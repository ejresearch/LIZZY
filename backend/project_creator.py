"""
Project Creator Module - Unified Project Creation from IDEATE Sessions

This module consolidates the functionality of START and INTAKE into a single
function that creates a complete project from an IDEATE session.

Replaces:
- START: Project directory and database creation
- INTAKE: Initial data population (characters, scenes, notes)

Usage:
    from backend.project_creator import create_project_from_ideate

    project_db_path = create_project_from_ideate(
        session_id=123,
        ideate_db_path=Path("ideate_sessions.db")
    )
"""

import json
from pathlib import Path
from typing import Optional, Dict, List

from .config import config
from .database import Database


def sanitize_name(name: str) -> str:
    """
    Sanitize project name for filesystem use.

    Args:
        name: Raw project name

    Returns:
        Safe filesystem name

    Example:
        "The Proposal 2.0!" -> "the_proposal_2_0"
    """
    # Convert to lowercase
    safe = name.lower()

    # Replace spaces and special chars with underscores
    safe = "".join(c if c.isalnum() else "_" for c in safe)

    # Remove consecutive underscores
    while "__" in safe:
        safe = safe.replace("__", "_")

    # Remove leading/trailing underscores
    safe = safe.strip("_")

    return safe


def load_ideate_session(session_id: int, ideate_db_path: Path) -> Optional[Dict]:
    """
    Load an IDEATE session from the ideate_sessions database.

    Args:
        session_id: Session ID to load
        ideate_db_path: Path to ideate_sessions.db

    Returns:
        Session dict with all fields, or None if not found
    """
    db = Database(ideate_db_path)
    return db.get_ideate_session(session_id)


def create_project_from_ideate(
    session_id: int,
    ideate_db_path: Path,
    overwrite: bool = False
) -> Path:
    """
    Create a complete project from an IDEATE session.

    This single function replaces the START + INTAKE workflow for IDEATE users.
    It creates the project directory, initializes the database, and populates
    all tables with the data collected during the IDEATE conversation.

    Args:
        session_id: ID of the IDEATE session to export
        ideate_db_path: Path to ideate_sessions.db
        overwrite: If True, overwrite existing project (default False)

    Returns:
        Path to the created project database

    Raises:
        ValueError: If session not found or project already exists

    Example:
        project_path = create_project_from_ideate(
            session_id=42,
            ideate_db_path=Path("ideate_sessions.db")
        )
        # Returns: Path("projects/my_romcom/my_romcom.db")
    """
    # 1. Load the IDEATE session
    session = load_ideate_session(session_id, ideate_db_path)
    if not session:
        raise ValueError(f"IDEATE session {session_id} not found")

    # 2. Get project name from session
    title = session.get("title") or session.get("name") or "Untitled Project"
    safe_name = sanitize_name(title)

    # 3. Create project directory
    project_dir = config.projects_dir / safe_name
    if project_dir.exists() and not overwrite:
        raise ValueError(f"Project '{title}' already exists at {project_dir}")

    project_dir.mkdir(parents=True, exist_ok=True)

    # Also create exports directory
    exports_dir = project_dir / "exports"
    exports_dir.mkdir(exist_ok=True)

    # 4. Create and initialize project database
    db_path = project_dir / f"{safe_name}.db"
    db = Database(db_path)
    db.initialize_schema()

    # 5. Insert project metadata
    db.insert_project(
        name=title,
        genre="Romantic Comedy",
        description=session.get("logline") or ""
    )

    # 6. Insert writer notes
    # Parse notebook from JSON if it's a string
    notebook = session.get("notebook", [])
    if isinstance(notebook, str):
        try:
            notebook = json.loads(notebook)
        except json.JSONDecodeError:
            notebook = [notebook] if notebook else []

    braindump = "\n\n".join(notebook) if notebook else ""

    # Parse outline from JSON if it's a string
    outline = session.get("outline", [])
    if isinstance(outline, str):
        try:
            outline = json.loads(outline)
        except json.JSONDecodeError:
            outline = []

    db.upsert_writer_notes(
        logline=session.get("logline") or "",
        theme=session.get("theme") or "",
        inspiration="",  # Not tracked in IDEATE
        tone=session.get("tone") or "",
        comps=session.get("comps") or "",
        braindump=braindump,
        outline=json.dumps(outline)
    )

    # 7. Insert characters
    characters = session.get("characters", [])
    if isinstance(characters, str):
        try:
            characters = json.loads(characters)
        except json.JSONDecodeError:
            characters = []

    for char in characters:
        if isinstance(char, dict):
            db.insert_character(
                name=char.get("name") or "",
                role=char.get("role") or "",
                description=char.get("description") or "",
                arc=char.get("arc") or "",
                age=char.get("age") or "",
                personality=char.get("personality") or "",
                flaw=char.get("flaw") or "",
                backstory=char.get("backstory") or "",
                relationships=char.get("relationships") or ""
            )

    # 8. Insert scenes
    # IDEATE stores scenes in the 'beats' column (confusing naming)
    scenes = session.get("beats", [])
    if isinstance(scenes, str):
        try:
            scenes = json.loads(scenes)
        except json.JSONDecodeError:
            scenes = []

    for scene in scenes:
        if isinstance(scene, dict):
            # Combine beats into description
            beats_list = scene.get("beats", [])
            beats_text = "\n".join(f"- {b}" for b in beats_list) if beats_list else ""

            description = scene.get("description") or ""
            if beats_text:
                description = f"{description}\n\nBeats:\n{beats_text}" if description else f"Beats:\n{beats_text}"

            # Get characters for this scene
            scene_characters = scene.get("characters", "")
            if isinstance(scene_characters, list):
                scene_characters = ", ".join(scene_characters)

            db.insert_scene(
                scene_number=scene.get("number") or 0,
                title=scene.get("title") or "",
                description=description,
                characters=scene_characters,
                tone=scene.get("tone") or ""
            )

    return db_path


def list_projects() -> List[str]:
    """
    List all existing projects.

    Returns:
        List of project names
    """
    if not config.projects_dir.exists():
        return []

    projects = []
    for project_dir in config.projects_dir.iterdir():
        if project_dir.is_dir():
            # Look for .db file
            db_files = list(project_dir.glob("*.db"))
            if db_files:
                projects.append(project_dir.name)

    return sorted(projects)


def get_project_path(name: str) -> Optional[Path]:
    """
    Get database path for an existing project.

    Args:
        name: Project name (can be display name or sanitized name)

    Returns:
        Path to database file, or None if not found
    """
    # Try exact match first
    db_path = config.projects_dir / name / f"{name}.db"
    if db_path.exists():
        return db_path

    # Try sanitized name
    safe_name = sanitize_name(name)
    db_path = config.projects_dir / safe_name / f"{safe_name}.db"
    if db_path.exists():
        return db_path

    return None


def list_exportable_sessions(ideate_db_path: Path) -> List[Dict]:
    """
    List IDEATE sessions that are ready for export.

    Args:
        ideate_db_path: Path to ideate_sessions.db

    Returns:
        List of session summaries with id, title, character count, scene count
    """
    db = Database(ideate_db_path)
    sessions = db.get_ideate_sessions()

    exportable = []
    for session in sessions:
        # Skip already exported sessions
        if session.get("stage") == "exported":
            continue

        # Get full session to count items
        full = db.get_ideate_session(session["id"])
        if not full:
            continue

        # Parse characters and scenes
        characters = full.get("characters", [])
        if isinstance(characters, str):
            try:
                characters = json.loads(characters)
            except json.JSONDecodeError:
                characters = []

        scenes = full.get("beats", [])
        if isinstance(scenes, str):
            try:
                scenes = json.loads(scenes)
            except json.JSONDecodeError:
                scenes = []

        exportable.append({
            "id": session["id"],
            "title": full.get("title") or session.get("name") or "Untitled",
            "logline": full.get("logline") or "",
            "characters": len(characters) if isinstance(characters, list) else 0,
            "scenes": len(scenes) if isinstance(scenes, list) else 0,
            "stage": session.get("stage", "explore"),
            "title_locked": full.get("title_locked", False),
            "logline_locked": full.get("logline_locked", False),
        })

    return exportable
