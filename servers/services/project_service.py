"""
Project management business logic.
Handles project CRUD operations, status tracking, and data management.
"""

import sys
from pathlib import Path

# Add parent directory to path for lizzy imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from lizzy.database import Database
from lizzy.start import StartModule
from typing import Dict, List, Optional


class ProjectService:
    """Service for managing screenplay projects."""

    def __init__(self, projects_dir: str = "projects"):
        self.projects_dir = Path(projects_dir)

    def list_projects(self) -> List[Dict]:
        """Get list of all projects."""
        if not self.projects_dir.exists():
            return []

        projects = []
        for project_dir in self.projects_dir.iterdir():
            if project_dir.is_dir():
                db_path = project_dir / f"{project_dir.name}.db"
                if db_path.exists():
                    projects.append({
                        "name": project_dir.name,
                        "path": str(project_dir),
                        "has_database": True
                    })

        return projects

    def get_project_status(self, project_name: str) -> Dict:
        """Get completion status for a project."""
        db_path = self.projects_dir / project_name / f"{project_name}.db"

        if not db_path.exists():
            raise ValueError(f"Project '{project_name}' not found")

        db = Database(db_path)

        # Check each step
        status = {
            "current_project": project_name,
            "steps": {
                "start": True,  # If DB exists, start is complete
                "intake": False,
                "brainstorm": False,
                "write": False,
                "export": False
            }
        }

        with db.get_connection() as conn:
            cursor = conn.cursor()

            # Check intake (has characters or scenes)
            cursor.execute("SELECT COUNT(*) FROM characters")
            char_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM scenes WHERE description IS NOT NULL AND description != ''")
            scene_count = cursor.fetchone()[0]

            status["steps"]["intake"] = char_count > 0 or scene_count > 0

            # Check brainstorm (has brainstorm_sessions)
            cursor.execute("SELECT COUNT(*) FROM brainstorm_sessions")
            brainstorm_count = cursor.fetchone()[0]
            status["steps"]["brainstorm"] = brainstorm_count > 0

            # Check write (has scene_drafts)
            cursor.execute("SELECT COUNT(*) FROM scene_drafts")
            draft_count = cursor.fetchone()[0]
            status["steps"]["write"] = draft_count > 0

            # Check export (has files in exports/)
            exports_dir = self.projects_dir / project_name / "exports"
            if exports_dir.exists():
                export_files = list(exports_dir.glob("*"))
                status["steps"]["export"] = len(export_files) > 0

        return status

    def get_project(self, project_name: str) -> Dict:
        """Get full project details including characters, scenes, notes."""
        db_path = self.projects_dir / project_name / f"{project_name}.db"

        if not db_path.exists():
            raise ValueError(f"Project '{project_name}' not found")

        db = Database(db_path)
        project_data = db.get_project()

        # Get characters
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name, description, role FROM characters")
            characters = [dict(row) for row in cursor.fetchall()]

            # Get scenes
            cursor.execute("SELECT scene_number, title, description, characters FROM scenes ORDER BY scene_number")
            scenes = []
            for row in cursor.fetchall():
                scene = dict(row)
                # Calculate act based on scene number
                scene_num = scene['scene_number']
                if scene_num <= 6:
                    scene['act'] = 1
                elif scene_num <= 24:
                    scene['act'] = 2
                else:
                    scene['act'] = 3
                scenes.append(scene)

            # Get notes from writer_notes table
            cursor.execute("SELECT theme, tone, comps, inspiration FROM writer_notes LIMIT 1")
            notes_row = cursor.fetchone()
            if notes_row:
                notes = {
                    'theme': notes_row['theme'] or '',
                    'tone': notes_row['tone'] or '',
                    'comparable_films': notes_row['comps'] or '',
                    'inspiration': notes_row['inspiration'] or ''
                }
            else:
                notes = {}

        return {
            "name": project_data.get('name'),
            "genre": project_data.get('genre'),
            "logline": project_data.get('description'),
            "characters": characters,
            "scenes": scenes,
            "notes": notes
        }

    def save_project(self, project_data: Dict) -> Dict:
        """Save or create a project."""
        name = project_data['name']
        genre = project_data.get('genre', 'Romantic Comedy')
        logline = project_data.get('logline', '')
        template = project_data.get('template', 'beatsheet')
        is_new = project_data.get('is_new', False)
        characters = project_data.get('characters', [])
        scenes = project_data.get('scenes', [])
        notes = project_data.get('notes', {})

        start = StartModule()

        if is_new:
            # Create new project
            if template == 'beatsheet':
                db_path = start.create_from_beat_sheet(name=name, genre=genre)
            else:
                db_path = start.create_project(name=name, genre=genre, description=logline)
        else:
            # Update existing project
            db_path = start.get_project_path(name)
            if not db_path:
                raise ValueError(f"Project '{name}' not found")

        # Update all project data
        db = Database(db_path)
        with db.get_connection() as conn:
            cursor = conn.cursor()

            # Update project metadata
            cursor.execute(
                "UPDATE projects SET genre = ?, description = ? WHERE id = 1",
                (genre, logline)
            )

            # Update characters
            if characters:
                # Clear existing characters
                cursor.execute("DELETE FROM characters")
                # Insert new characters
                for char in characters:
                    cursor.execute(
                        "INSERT INTO characters (name, role, description) VALUES (?, ?, ?)",
                        (char.get('name', ''), char.get('role', ''), char.get('description', ''))
                    )

            # Update scenes
            if scenes:
                for scene in scenes:
                    scene_num = scene.get('scene_number')
                    if scene_num:
                        cursor.execute(
                            """UPDATE scenes
                               SET title = ?, description = ?, characters = ?
                               WHERE scene_number = ?""",
                            (
                                scene.get('title', ''),
                                scene.get('description', ''),
                                scene.get('characters', ''),
                                scene_num
                            )
                        )

            # Update notes
            if notes:
                # Check if writer_notes row exists
                cursor.execute("SELECT COUNT(*) FROM writer_notes")
                count = cursor.fetchone()[0]

                if count > 0:
                    # Update existing row
                    cursor.execute(
                        """UPDATE writer_notes
                           SET theme = ?, tone = ?, comps = ?, inspiration = ?
                           WHERE id = (SELECT id FROM writer_notes LIMIT 1)""",
                        (
                            notes.get('theme', ''),
                            notes.get('tone', ''),
                            notes.get('comparable_films', ''),
                            notes.get('inspiration', '')
                        )
                    )
                else:
                    # Insert new row
                    cursor.execute(
                        "INSERT INTO writer_notes (theme, tone, comps, inspiration) VALUES (?, ?, ?, ?)",
                        (
                            notes.get('theme', ''),
                            notes.get('tone', ''),
                            notes.get('comparable_films', ''),
                            notes.get('inspiration', '')
                        )
                    )

            conn.commit()

        return {"success": True, "project_name": name}

    def delete_project(self, project_name: str) -> Dict:
        """Delete a project."""
        start = StartModule()
        start.delete_project(project_name)
        return {"success": True}

    def get_launch_command(self, module: str, project_name: Optional[str] = None) -> Dict:
        """Get CLI command to launch a module."""
        commands = {
            "start": "python3 -m lizzy.start",
            "intake": "python3 -m lizzy.intake",
            "brainstorm": "python3 -m lizzy.automated_brainstorm",
            "write": "python3 -m lizzy.automated_write",
            "export": "python3 -m lizzy.export",
            "prompt_studio": "./scripts/start_prompt_studio.sh"
        }

        if module not in commands:
            raise ValueError(f"Invalid module: {module}")

        command = commands[module]

        # Add project name if provided
        if project_name and module in ["intake"]:
            command += f' "{project_name}"'

        return {
            "module": module,
            "command": command,
            "message": f"Run this command in your terminal:\n\n{command}"
        }
