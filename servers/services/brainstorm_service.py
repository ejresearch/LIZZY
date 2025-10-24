"""
Brainstorm business logic.
Handles interactive brainstorming, batch processing, and brainstorm management.
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional

# Add parent directory to path for lizzy imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from lizzy.database import Database
from lizzy.interactive_brainstorm import InteractiveBrainstorm
from lizzy.automated_brainstorm import AutomatedBrainstorm


class BrainstormService:
    """Service for brainstorming and scene brainstorm generation."""

    def __init__(self, projects_dir: str = "projects"):
        self.projects_dir = Path(projects_dir)

    def _get_db_path(self, project_name: str) -> Path:
        """Get database path for a project."""
        db_path = self.projects_dir / project_name / f"{project_name}.db"
        if not db_path.exists():
            raise ValueError(f"Project '{project_name}' not found")
        return db_path

    def get_chat_history(self, project_name: str) -> Dict:
        """Get chat history for a project."""
        # TODO: Implement chat history storage
        return {"messages": []}

    async def chat_query(self, project_name: str, query: str, focused_scene: Optional[int] = None) -> Dict:
        """Send a query to the expert knowledge graphs."""
        db_path = self._get_db_path(project_name)

        try:
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

            return {
                "success": True,
                "message_id": len(brainstorm.conversation_history),
                "experts": experts
            }
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": f"Failed to query: {str(e)}"
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
                await brainstorm.run_batch_processing()

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
                    bs.content,
                    bs.bucket_used,
                    bs.created_at
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
                        'experts': []
                    }

                if row['content']:
                    # If bucket_used is 'all' or 'synthesis', it's the main brainstorm
                    if row['bucket_used'] in ['all', 'synthesis']:
                        brainstorms[scene_num]['brainstorm'] = row['content']
                        brainstorms[scene_num]['created_at'] = row['created_at']
                    else:
                        # It's an expert consultation
                        brainstorms[scene_num]['experts'].append({
                            'bucket': row['bucket_used'],
                            'content': row['content']
                        })

            return {"brainstorms": list(brainstorms.values())}
