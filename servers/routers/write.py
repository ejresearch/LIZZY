"""
Routes for WRITE module - scene draft management.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict

from ..services import WriteService
from ..models import WriteSceneRequest

router = APIRouter(prefix="/api/write", tags=["write"])

# Initialize service
write_service = WriteService()


@router.get("/drafts/{project_name}")
async def get_all_drafts(project_name: str):
    """Get all scene drafts for a project."""
    try:
        result = write_service.get_all_drafts(project_name)
        return result

    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {str(e)}"}


@router.post("/generate-scene")
async def generate_scene(request: WriteSceneRequest):
    """
    Generate a screenplay draft for a scene.

    Request body:
    {
        "project": "project_name",
        "scene_number": 1,
        "target_words": 800  # optional, defaults to 800
    }
    """
    try:
        result = await write_service.generate_scene(
            project_name=request.project,
            scene_number=request.scene_number,
            target_words=request.target_words
        )
        return result

    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {str(e)}"}
