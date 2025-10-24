"""
Routes for brainstorming and scene brainstorm generation.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict

from ..services import BrainstormService

router = APIRouter(prefix="/api/brainstorm", tags=["brainstorm"])
brainstorm_service = BrainstormService()


@router.get("/chat/history")
async def get_chat_history(project: str):
    """Get chat history for a project."""
    return brainstorm_service.get_chat_history(project)


@router.post("/chat/query")
async def chat_query(request_data: Dict):
    """Send a query to the expert knowledge graphs."""
    project_name = request_data.get('project')
    query = request_data.get('query')
    focused_scene = request_data.get('focused_scene')

    if not project_name or not query:
        return {"success": False, "error": "Project name and query required"}

    try:
        return await brainstorm_service.chat_query(project_name, query, focused_scene)
    except ValueError as e:
        return {"success": False, "error": str(e)}


@router.get("/batch/status")
async def get_batch_status(project: str):
    """Get status of all scenes for batch processing."""
    try:
        return brainstorm_service.get_batch_status(project)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/batch/start")
async def start_batch_process(request_data: Dict):
    """Start batch processing all scenes."""
    project_name = request_data.get('project')
    if not project_name:
        return {"success": False, "error": "Project name required"}

    return await brainstorm_service.start_batch_process(project_name)


@router.post("/batch/generate-scene")
async def generate_scene_brainstorm(request_data: Dict):
    """Generate brainstorm for a single scene."""
    project_name = request_data.get('project')
    scene_number = request_data.get('scene_number')

    if not project_name or not scene_number:
        return {"success": False, "error": "Project name and scene number required"}

    return await brainstorm_service.generate_scene_brainstorm(project_name, scene_number)


@router.get("/brainstorms/{project_name}")
async def get_brainstorms(project_name: str):
    """Get all scene brainstorms for a project."""
    try:
        return brainstorm_service.get_brainstorms(project_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
