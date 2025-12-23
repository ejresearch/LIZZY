"""
Brainstorm business logic.
Handles interactive brainstorming, batch processing, and brainstorm management.
"""

from pathlib import Path
from typing import Dict, List, Optional

from ..config import config
from ..logging_config import get_logger
from backend.database import Database
from backend.interactive_brainstorm import InteractiveBrainstorm
from backend.automated_brainstorm import AutomatedBrainstorm
from backend.project_creator import sanitize_name

logger = get_logger(__name__)


class BrainstormService:
    """Service for brainstorming and scene brainstorm generation."""

    def __init__(self, projects_dir: Path = None):
        self.projects_dir = projects_dir or config.projects_dir

    def _get_db_path(self, project_name: str) -> Path:
        """Get database path for a project."""
        # Sanitize project name for filesystem lookup
        sanitized_name = sanitize_name(project_name)
        db_path = self.projects_dir / sanitized_name / f"{sanitized_name}.db"
        if not db_path.exists():
            raise ValueError(f"Project '{project_name}' not found")
        return db_path

    def get_chat_history(self, project_name: str, limit: Optional[int] = None) -> Dict:
        """
        Get chat history for a project.

        Args:
            project_name: Name of the project
            limit: Optional limit on number of messages (most recent first)

        Returns:
            Dict with success status and list of messages
        """
        try:
            db_path = self._get_db_path(project_name)
            db = Database(db_path)

            messages = db.get_chat_history(limit=limit)

            # Parse experts JSON for assistant messages
            import json
            for msg in messages:
                if msg.get('experts'):
                    try:
                        msg['experts'] = json.loads(msg['experts'])
                    except json.JSONDecodeError:
                        msg['experts'] = []

            return {
                "success": True,
                "messages": messages
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "messages": []
            }

    async def chat_query(self, project_name: str, query: str, focused_scene: Optional[int] = None) -> Dict:
        """
        Send a query to the expert knowledge graphs and save to chat history.

        Args:
            project_name: Name of the project
            query: User's query text
            focused_scene: Optional scene number in focus

        Returns:
            Dict with success status, message_id, and expert responses
        """
        db_path = self._get_db_path(project_name)

        try:
            import json

            # Save user message to database
            db = Database(db_path)
            user_msg_id = db.insert_chat_message(
                role='user',
                content=query,
                focused_scene=focused_scene
            )

            # Query experts
            brainstorm = InteractiveBrainstorm(db_path)
            brainstorm.load_project_context()

            # Set focused scene if provided
            if focused_scene:
                brainstorm.focused_scene = focused_scene

            # Query all three buckets
            buckets = ['books', 'plays', 'scripts']
            results = await brainstorm.query_buckets(query, buckets, mode="hybrid")

            # Format results for frontend
            experts = []
            for result in results:
                experts.append({
                    'bucket': result['bucket'],
                    'content': result.get('response', '')  # 'response' is the key from query_buckets
                })

            # Save assistant response to database
            assistant_msg_id = db.insert_chat_message(
                role='assistant',
                content=f"Expert responses for: {query}",
                focused_scene=focused_scene,
                experts=json.dumps(experts)
            )

            return {
                "success": True,
                "message_id": assistant_msg_id,
                "user_message_id": user_msg_id,
                "experts": experts
            }
        except Exception as e:
            logger.error(f"Failed to query: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Failed to query: {str(e)}"
            }

    def clear_chat_history(self, project_name: str) -> Dict:
        """
        Clear all chat history for a project.

        Args:
            project_name: Name of the project

        Returns:
            Dict with success status and count of deleted messages
        """
        try:
            db_path = self._get_db_path(project_name)
            db = Database(db_path)

            deleted_count = db.clear_chat_history()

            return {
                "success": True,
                "deleted_count": deleted_count
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def get_batch_status(self, project_name: str) -> Dict:
        """Get status of all scenes for batch processing."""
        db_path = self._get_db_path(project_name)
        db = Database(db_path)

        with db.get_connection() as conn:
            cursor = conn.cursor()

            # Get all scenes
            cursor.execute("""
                SELECT s.scene_number, s.title, s.description,
                       COUNT(DISTINCT bs.id) as brainstorm_count
                FROM scenes s
                LEFT JOIN brainstorm_sessions bs ON s.id = bs.scene_id
                GROUP BY s.scene_number
                ORDER BY s.scene_number
            """)

            scenes = []
            for row in cursor.fetchall():
                scene = dict(row)
                scene['status'] = 'done' if scene['brainstorm_count'] > 0 else 'pending'
                scenes.append(scene)

        return {"scenes": scenes}

    async def start_batch_process(self, project_name: str) -> Dict:
        """Start batch processing all scenes."""
        import asyncio

        db_path = self._get_db_path(project_name)

        try:
            # Run automated brainstorm in background
            brainstorm = AutomatedBrainstorm(db_path)

            # Start async processing in background
            async def process_scenes():
                brainstorm.load_project_context()
                await brainstorm.run_batch_processing(skip_confirmation=True)

            # Start background task
            asyncio.create_task(process_scenes())

            return {
                "success": True,
                "message": "Batch processing started"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to start batch process: {str(e)}"
            }

    async def generate_scene_brainstorm(self, project_name: str, scene_number: int) -> Dict:
        """Generate brainstorm for a single scene."""
        db_path = self._get_db_path(project_name)

        try:
            brainstorm = AutomatedBrainstorm(db_path)
            brainstorm.load_project_context()

            # Find the scene
            scene = next((s for s in brainstorm.scenes if s['scene_number'] == scene_number), None)
            if not scene:
                return {"success": False, "error": f"Scene {scene_number} not found"}

            # Process single scene (using Rich progress for CLI compatibility)
            from rich.progress import Progress
            with Progress() as progress:
                task_id = progress.add_task(f"Processing Scene {scene_number}", total=1)
                await brainstorm.process_scene(scene, progress, task_id)

            return {
                "success": True,
                "message": f"Scene {scene_number} brainstorm generated"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to generate scene: {str(e)}"
            }

    def get_brainstorms(self, project_name: str) -> Dict:
        """Get all scene brainstorms for a project."""
        db_path = self._get_db_path(project_name)
        db = Database(db_path)

        with db.get_connection() as conn:
            cursor = conn.cursor()

            # Get all scenes with their brainstorms
            cursor.execute("""
                SELECT
                    s.scene_number,
                    s.title,
                    s.description,
                    s.characters,
                    bs.id as brainstorm_id,
                    bs.content,
                    bs.bucket_used,
                    bs.created_at,
                    bs.tone
                FROM scenes s
                LEFT JOIN brainstorm_sessions bs ON s.id = bs.scene_id
                ORDER BY s.scene_number, bs.created_at DESC
            """)

            results = cursor.fetchall()

            # Group by scene
            brainstorms = {}
            for row in results:
                scene_num = row['scene_number']
                if scene_num not in brainstorms:
                    brainstorms[scene_num] = {
                        'scene_number': scene_num,
                        'title': row['title'],
                        'description': row['description'],
                        'characters': row['characters'],
                        'brainstorm': None,
                        'created_at': None,
                        'versions': [],  # All synthesis/all brainstorms
                        'experts': []    # Expert consultations (books, plays, scripts)
                    }

                if row['content']:
                    # If bucket_used is 'all' or 'synthesis', it's a main brainstorm version
                    if row['bucket_used'] in ['all', 'synthesis']:
                        # Add to versions list
                        brainstorms[scene_num]['versions'].append({
                            'id': row['brainstorm_id'],
                            'content': row['content'],
                            'created_at': row['created_at'],
                            'tone': row['tone'],
                            'bucket_used': row['bucket_used']
                        })

                        # Set the latest one as the main brainstorm
                        if brainstorms[scene_num]['brainstorm'] is None:
                            brainstorms[scene_num]['brainstorm'] = row['content']
                            brainstorms[scene_num]['created_at'] = row['created_at']
                    else:
                        # It's an expert consultation
                        brainstorms[scene_num]['experts'].append({
                            'bucket': row['bucket_used'],
                            'content': row['content'],
                            'created_at': row['created_at']
                        })

            return {"brainstorms": list(brainstorms.values())}
