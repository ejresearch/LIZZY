"""
Routes for brainstorming and scene brainstorm generation.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict

from ..services import BrainstormService
from ..models import ChatQueryRequest, BatchProcessRequest, SceneBlueprintRequest

router = APIRouter(prefix="/api/brainstorm", tags=["brainstorm"])
brainstorm_service = BrainstormService()


@router.get("/chat/history")
async def get_chat_history(project: str):
    """Get chat history for a project."""
    return brainstorm_service.get_chat_history(project)


@router.post("/chat/query")
async def chat_query(request: ChatQueryRequest):
    """Send a query to the expert knowledge graphs."""
    try:
        return await brainstorm_service.chat_query(request.project, request.query, request.focused_scene)
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {str(e)}"}


@router.get("/batch/status")
async def get_batch_status(project: str):
    """Get status of all scenes for batch processing."""
    try:
        return brainstorm_service.get_batch_status(project)
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {str(e)}"}


@router.post("/batch/start")
async def start_batch_process(request: BatchProcessRequest):
    """Start batch processing all scenes."""
    try:
        return await brainstorm_service.start_batch_process(request.project)
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {str(e)}"}


@router.post("/batch/generate-scene")
async def generate_scene_brainstorm(request: SceneBlueprintRequest):
    """Generate brainstorm for a single scene."""
    try:
        return await brainstorm_service.generate_scene_brainstorm(request.project, request.scene_number)
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {str(e)}"}


@router.get("/brainstorms/{project_name}")
async def get_brainstorms(project_name: str):
    """Get all scene brainstorms for a project."""
    try:
        return brainstorm_service.get_brainstorms(project_name)
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {str(e)}"}
