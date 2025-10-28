"""
Write business logic.
Handles scene draft generation, management, and export operations.
"""

from pathlib import Path
from typing import Dict, List, Optional

from ..config import config
from ..logging_config import get_logger
from lizzy.database import Database
from lizzy.write import WriteModule
from lizzy.exceptions import (
    ProjectNotFoundError,
    SceneNotFoundError,
    DraftNotFoundError,
    ExportError,
    create_error_response
)

logger = get_logger(__name__)


class WriteService:
    """Service for screenplay writing and scene draft management."""

    def __init__(self, projects_dir: Path = None):
        self.projects_dir = projects_dir or config.projects_dir

    def _get_db_path(self, project_name: str) -> Path:
        """Get database path for a project."""
        db_path = config.get_project_db_path(project_name)
        if not db_path.exists():
            raise ProjectNotFoundError(project_name)
        return db_path

    def get_all_drafts(self, project_name: str) -> Dict:
        """
        Get all scene drafts for a project.

        Args:
            project_name: Name of the project

        Returns:
            Dict with success status and list of drafts
        """
        try:
            db_path = self._get_db_path(project_name)
            db = Database(db_path)

            with db.get_connection() as conn:
                cursor = conn.cursor()

                # Get all drafts with their scene info
                cursor.execute("""
                    SELECT
                        sd.id,
                        sd.scene_id,
                        s.scene_number,
                        sd.content,
                        sd.version,
                        sd.word_count,
                        sd.tokens_used,
                        sd.cost_estimate,
                        sd.created_at
                    FROM scene_drafts sd
                    JOIN scenes s ON sd.scene_id = s.id
                    ORDER BY s.scene_number, sd.version DESC
                """)

                drafts = []
                for row in cursor.fetchall():
                    drafts.append({
                        "id": row["id"],
                        "scene_id": row["scene_id"],
                        "scene_number": row["scene_number"],
                        "content": row["content"],
                        "version": row["version"],
                        "word_count": row["word_count"],
                        "tokens_used": row["tokens_used"],
                        "cost_estimate": row["cost_estimate"],
                        "created_at": row["created_at"]
                    })

            return {
                "success": True,
                "drafts": drafts
            }

        except ProjectNotFoundError as e:
            logger.warning(f"Project not found: {e.project_name}")
            return create_error_response(e)
        except Exception as e:
            logger.error(f"Error getting drafts: {e}", exc_info=True)
            return create_error_response(e)

    async def generate_scene(
        self,
        project_name: str,
        scene_number: int,
        target_words: int = 800
    ) -> Dict:
        """
        Generate a screenplay draft for a scene.

        Args:
            project_name: Name of the project
            scene_number: Scene number to generate
            target_words: Target word count (default: 800)

        Returns:
            Dict with success status and draft details
        """
        try:
            writer = WriteModule(project_name)

            # Load scene context (includes blueprint from brainstorm)
            context = writer.load_scene_context(scene_number)

            if not context:
                return {
                    "success": False,
                    "error": f"Scene {scene_number} not found in project"
                }

            # Generate the draft
            draft = await writer.generate_draft(context, target_words=target_words)

            # Save to database
            draft_id = writer.save_draft(draft)

            # Get formatted preview
            preview = writer.get_formatted_preview(draft, max_lines=50)

            # Validate formatting
            validation_report = writer.validate_draft(draft)

            return {
                "success": True,
                "draft": {
                    "id": draft_id,
                    "scene_number": draft.scene_number,
                    "version": draft.version,
                    "content": draft.content,
                    "preview": preview,
                    "word_count": draft.word_count,
                    "tokens_used": draft.tokens_used,
                    "cost_estimate": draft.cost_estimate,
                    "created_at": draft.created_at,
                    "is_valid": validation_report.passed,
                    "formatting_errors": validation_report.errors if not validation_report.passed else []
                }
            }

        except Exception as e:
            logger.error(f"Error generating scene: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    def get_scene_drafts(
        self,
        project_name: str,
        scene_number: int
    ) -> Dict:
        """
        Get all draft versions for a specific scene.

        Args:
            project_name: Name of the project
            scene_number: Scene number

        Returns:
            Dict with success status and list of drafts
        """
        try:
            writer = WriteModule(project_name)
            drafts = writer.get_all_drafts(scene_number)

            return {
                "success": True,
                "drafts": [
                    {
                        "id": d.scene_id,
                        "scene_number": d.scene_number,
                        "version": d.version,
                        "content": d.content,
                        "word_count": d.word_count,
                        "tokens_used": d.tokens_used,
                        "cost_estimate": d.cost_estimate,
                        "created_at": d.created_at
                    }
                    for d in drafts
                ]
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def export_scene(
        self,
        project_name: str,
        scene_number: int,
        version: int = 1,
        output_format: str = "docx"
    ) -> Dict:
        """
        Export a scene draft as formatted screenplay.

        Args:
            project_name: Name of the project
            scene_number: Scene number to export
            version: Draft version (default: 1)
            output_format: Format (txt, docx, or pdf)

        Returns:
            Dict with success status and file details
        """
        try:
            writer = WriteModule(project_name)

            # Get the draft
            drafts = writer.get_all_drafts(scene_number)
            if not drafts:
                return {
                    "success": False,
                    "error": f"No drafts found for scene {scene_number}"
                }

            # Find the requested version
            draft = next((d for d in drafts if d.version == version), None)
            if not draft:
                return {
                    "success": False,
                    "error": f"Version {version} not found for scene {scene_number}"
                }

            # Export
            output_path, is_valid, errors = writer.export_draft(
                draft,
                output_format=output_format,
                validate=True
            )

            # Get filename from path
            filename = Path(output_path).name

            return {
                "success": True,
                "filename": filename,
                "path": output_path,
                "is_valid": is_valid,
                "errors": errors if not is_valid else [],
                "scene_number": scene_number,
                "version": version,
                "format": output_format
            }

        except Exception as e:
            logger.error(f"Error exporting scene: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    async def export_full_screenplay(
        self,
        project_name: str,
        scenes: List[Dict],
        output_format: str = "docx"
    ) -> Dict:
        """
        Export full screenplay combining all scenes.

        Args:
            project_name: Name of the project
            scenes: List of dicts with scene_number and version
            output_format: Format (txt, docx, or pdf)

        Returns:
            Dict with success status and file details
        """
        try:
            writer = WriteModule(project_name)

            # Collect all scene drafts
            all_content = []
            for scene_info in scenes:
                scene_number = scene_info['scene_number']
                version = scene_info['version']

                # Get the draft
                drafts = writer.get_all_drafts(scene_number)
                draft = next((d for d in drafts if d.version == version), None)

                if draft:
                    all_content.append(draft.content)

            if not all_content:
                return {
                    "success": False,
                    "error": "No drafts found to export"
                }

            # Combine all scenes with separators
            full_screenplay = '\n\n\n'.join(all_content)

            # Create a temporary draft-like object for export
            from dataclasses import dataclass
            from datetime import datetime

            @dataclass
            class FullScreenplayDraft:
                scene_id: int
                scene_number: int
                content: str
                version: int
                word_count: int
                tokens_used: int
                cost_estimate: float
                created_at: str

            combined_draft = FullScreenplayDraft(
                scene_id=0,
                scene_number=0,  # Special: 0 means full screenplay
                content=full_screenplay,
                version=1,
                word_count=len(full_screenplay.split()),
                tokens_used=0,
                cost_estimate=0.0,
                created_at=datetime.now().isoformat()
            )

            # Export using the writer's export method
            output_path, is_valid, errors = writer.export_draft(
                combined_draft,
                output_format=output_format,
                validate=True
            )

            # Rename file to indicate full screenplay
            old_path = Path(output_path)
            new_filename = f"{project_name}_FULL_SCREENPLAY.{output_format}"
            new_path = old_path.parent / new_filename

            # Rename the file
            old_path.rename(new_path)

            return {
                "success": True,
                "filename": new_filename,
                "path": str(new_path),
                "is_valid": is_valid,
                "errors": errors if not is_valid else [],
                "scene_count": len(scenes),
                "format": output_format
            }

        except Exception as e:
            logger.error(f"Error exporting full screenplay: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
