"""
Routes for AI content generation and screenplay export.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from typing import Dict

from ..config import config
from ..services import GenerationService, WriteService

router = APIRouter(prefix="/api/generate", tags=["generation"])
generation_service = GenerationService()
write_service = WriteService()


@router.post("/random-romcom")
async def generate_random_romcom():
    """Generate a random romantic comedy project using AI."""
    return await generation_service.generate_random_romcom()


@router.post("/export-scene")
async def export_scene(request_data: Dict):
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
    project_name = request_data.get('project')
    scene_number = request_data.get('scene_number')
    version = request_data.get('version', 1)
    output_format = request_data.get('format', 'docx')

    if not project_name or not scene_number:
        raise HTTPException(status_code=400, detail="Project and scene_number required")

    try:
        result = await write_service.export_scene(
            project_name, scene_number, version, output_format
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export-full-screenplay")
async def export_full_screenplay(request_data: Dict):
    """
    Export full screenplay with all scenes.

    Request body:
    {
        "project": "project_name",
        "scenes": [{"scene_number": 1, "version": 1}, ...],
        "format": "docx"  # txt, docx, or pdf
    }
    """
    project_name = request_data.get('project')
    scenes = request_data.get('scenes', [])
    output_format = request_data.get('format', 'docx')

    if not project_name or not scenes:
        raise HTTPException(status_code=400, detail="Project and scenes required")

    try:
        result = await write_service.export_full_screenplay(
            project_name, scenes, output_format
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
