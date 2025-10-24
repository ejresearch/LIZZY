"""
Pydantic models for API requests and responses.
"""

from pydantic import BaseModel
from typing import Dict, List, Optional


class ProjectStatus(BaseModel):
    """Project completion status."""
    current_project: Optional[str] = None
    steps: Dict[str, bool]


class ModuleLaunch(BaseModel):
    """Request to launch a Lizzy module."""
    module: str
    project_name: Optional[str] = None


class CharacterData(BaseModel):
    """Character information."""
    name: str
    role: str
    description: str


class SceneData(BaseModel):
    """Scene information."""
    scene_number: int
    act: Optional[int] = None
    title: str
    description: str
    characters: str


class WriterNotes(BaseModel):
    """Writer's creative notes."""
    theme: str = ""
    tone: str = ""
    comparable_films: str = ""
    inspiration: str = ""


class ProjectData(BaseModel):
    """Complete project data."""
    name: str
    genre: str = "Romantic Comedy"
    logline: str = ""
    template: str = "beatsheet"
    is_new: bool = False
    characters: List[CharacterData] = []
    scenes: List[SceneData] = []
    notes: WriterNotes = WriterNotes()


class ChatQueryRequest(BaseModel):
    """Request to query expert knowledge graphs."""
    project: str
    query: str
    focused_scene: Optional[int] = None


class BatchProcessRequest(BaseModel):
    """Request to start batch scene processing."""
    project: str


class SceneBlueprintRequest(BaseModel):
    """Request to generate a single scene blueprint."""
    project: str
    scene_number: int
