"""
Routes for project management.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict

from ..services import ProjectService
from ..models import ModuleLaunch, ProjectData

router = APIRouter(prefix="/api", tags=["projects"])
project_service = ProjectService()


@router.get("/projects")
async def get_projects():
    """Get list of all projects."""
    projects = project_service.list_projects()
    return {"projects": projects}


@router.get("/status/{project_name}")
async def get_project_status(project_name: str):
    """Get completion status for a project."""
    try:
        return project_service.get_project_status(project_name)
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {str(e)}"}


@router.get("/project/{project_name}")
async def get_project(project_name: str):
    """Get full project details including characters, scenes, notes."""
    try:
        return project_service.get_project(project_name)
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {str(e)}"}


@router.post("/project/save")
async def save_project(project: ProjectData):
    """Save or create a project."""
    try:
        # Convert Pydantic model to dict for the service
        project_dict = project.model_dump()
        return project_service.save_project(project_dict)
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {str(e)}"}


@router.delete("/projects/{project_name}")
async def delete_project(project_name: str):
    """Delete a project."""
    try:
        return project_service.delete_project(project_name)
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {str(e)}"}


@router.post("/launch")
async def launch_module(launch: ModuleLaunch):
    """Get CLI command to launch a module."""
    try:
        return project_service.get_launch_command(launch.module, launch.project_name)
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {str(e)}"}


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "Lizzy 2.0 Landing Page"}
