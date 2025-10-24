"""
Routes for WRITE module - scene draft management.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict

from ..services import WriteService

router = APIRouter(prefix="/api/write", tags=["write"])

# Initialize service
write_service = WriteService()


@router.get("/drafts/{project_name}")
async def get_all_drafts(project_name: str):
    """Get all scene drafts for a project."""
    try:
        result = write_service.get_all_drafts(project_name)
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))
        return result

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
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
        result = await write_service.generate_scene(
            project_name=project_name,
            scene_number=scene_number,
            target_words=target_words
        )

        if not result["success"]:
            return result

        return result

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
