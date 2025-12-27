"""
Routes for AI content generation and screenplay export.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from typing import Dict

from ..config import config
from ..services import GenerationService, WriteService
from ..models import ExportSceneRequest, ExportFullScreenplayRequest

router = APIRouter(prefix="/api/generate", tags=["generation"])
generation_service = GenerationService()
write_service = WriteService()


@router.post("/random-romcom")
async def generate_random_romcom():
    """Generate a random romantic comedy project using AI."""
    try:
        return await generation_service.generate_random_romcom()
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {str(e)}"}


@router.post("/export-scene")
async def export_scene(request: ExportSceneRequest):
    """
    Export a scene draft as formatted screenplay.

    Request body:
    {
        "project": "project_name",
        "scene_number": 1,
        "version": 1,
        "format": "docx"  # txt, docx, or pdf
    }
    """
    try:
        result = await write_service.export_scene(
            request.project, request.scene_number, request.version, request.format
        )
        return result
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {str(e)}"}


@router.post("/export-full-screenplay")
async def export_full_screenplay(request: ExportFullScreenplayRequest):
    """
    Export full screenplay with all scenes.

    Request body:
    {
        "project": "project_name",
        "scenes": [{"scene_number": 1, "version": 1}, ...],
        "format": "docx"  # txt, docx, or pdf
    }
    """
    try:
        # Convert Pydantic models to dicts for the service
        scenes_data = [{"scene_number": s.scene_number, "version": s.version} for s in request.scenes]
        result = await write_service.export_full_screenplay(
            request.project, scenes_data, request.format
        )
        return result
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {str(e)}"}


@router.get("/download-screenplay/{project_name}/{filename}")
async def download_screenplay(project_name: str, filename: str):
    """Download an exported screenplay file."""
    try:
        screenplays_dir = config.get_project_screenplays_dir(project_name)
        file_path = screenplays_dir / filename

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")

        return FileResponse(
            path=str(file_path),
            filename=filename,
            media_type='application/octet-stream'
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
