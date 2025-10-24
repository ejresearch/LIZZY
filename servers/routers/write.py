"""
Routes for WRITE module - scene draft management.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict
import sys
from pathlib import Path
import asyncio

# Add parent directory to path for lizzy imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from lizzy.write import WriteModule

router = APIRouter(prefix="/api/write", tags=["write"])


@router.get("/drafts/{project_name}")
async def get_all_drafts(project_name: str):
    """Get all scene drafts for a project."""
    try:
        writer = WriteModule(project_name)

        # Get all scenes from the project
        import sqlite3
        db_path = Path("projects") / project_name / f"{project_name}.db"

        if not db_path.exists():
            return {"success": True, "drafts": []}

        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
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

        conn.close()

        return {
            "success": True,
            "drafts": drafts
        }

    except Exception as e:
        print(f"Error fetching drafts: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-scene")
async def generate_scene(request_data: Dict):
    """
    Generate a screenplay draft for a scene.

    Request body:
    {
        "project": "project_name",
        "scene_number": 1,
        "target_words": 800  # optional, defaults to 800
    }
    """
    project_name = request_data.get('project')
    scene_number = request_data.get('scene_number')
    target_words = request_data.get('target_words', 800)

    if not project_name or not scene_number:
        raise HTTPException(status_code=400, detail="Project and scene_number required")

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
        print(f"Error generating scene: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }
