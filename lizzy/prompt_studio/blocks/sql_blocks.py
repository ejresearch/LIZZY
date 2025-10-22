"""
SQL-based blocks for Prompt Studio

These blocks fetch data from the SQLite database.
"""

import sqlite3
from typing import Optional, List
from .base import Block


class SceneBlock(Block):
    """
    Fetches data for a specific scene.

    Outputs: Scene number, title, description, act, characters
    """

    def __init__(self, scene_number: int, block_id: str = None):
        super().__init__(block_id)
        self.scene_number = scene_number

    def execute(self, project_name: str, **kwargs) -> str:
        db_path = f"projects/{project_name}/{project_name}.db"

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get scene data
        cursor.execute("""
            SELECT scene_number, title, description, tone, characters
            FROM scenes
            WHERE scene_number = ?
        """, (self.scene_number,))

        scene = cursor.fetchone()
        conn.close()

        if not scene:
            return f"[Scene {self.scene_number} not found]"

        output = []
        output.append(f"SCENE {scene['scene_number']}: {scene['title']}")
        if scene['tone']:
            output.append(f"Tone: {scene['tone']}")
        output.append(f"Description: {scene['description']}")
        output.append(f"Characters: {scene['characters']}")

        return "\n".join(output)

    def get_description(self) -> str:
        return f"Scene {self.scene_number} data (title, description, act, characters)"

    def validate(self) -> tuple[bool, Optional[str]]:
        if self.scene_number < 1 or self.scene_number > 30:
            return (False, f"Scene number must be 1-30, got {self.scene_number}")
        return (True, None)


class CharacterBiosBlock(Block):
    """
    Fetches all character bios from the database.

    Outputs: Formatted list of all characters with their bios
    """

    def __init__(self, block_id: str = None):
        super().__init__(block_id)

    def execute(self, project_name: str, **kwargs) -> str:
        db_path = f"projects/{project_name}/{project_name}.db"

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT name, description, role, arc FROM characters ORDER BY name")
        characters = cursor.fetchall()
        conn.close()

        if not characters:
            return "[No characters defined]"

        output = ["CHARACTER BIOS:"]
        for char in characters:
            output.append(f"\n{char['name']}:")
            if char['role']:
                output.append(f"  Role: {char['role']}")
            if char['description']:
                output.append(f"  {char['description']}")
            if char['arc']:
                output.append(f"  Arc: {char['arc']}")

        return "\n".join(output)

    def get_description(self) -> str:
        return "All character bios from the database"


class WriterNotesBlock(Block):
    """
    Fetches all writer notes from the database.

    Outputs: All notes organized by category
    """

    def __init__(self, category: Optional[str] = None, block_id: str = None):
        super().__init__(block_id)
        self.category = category

    def execute(self, project_name: str, **kwargs) -> str:
        db_path = f"projects/{project_name}/{project_name}.db"

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if self.category:
            cursor.execute("""
                SELECT category, note
                FROM writer_notes
                WHERE category = ?
                ORDER BY category
            """, (self.category,))
        else:
            cursor.execute("""
                SELECT category, note
                FROM writer_notes
                ORDER BY category
            """)

        notes = cursor.fetchall()
        conn.close()

        if not notes:
            return "[No writer notes found]"

        output = ["WRITER NOTES:"]
        current_category = None

        for note in notes:
            if note['category'] != current_category:
                current_category = note['category']
                output.append(f"\n{current_category}:")
            output.append(f"  - {note['note']}")

        return "\n".join(output)

    def get_description(self) -> str:
        if self.category:
            return f"Writer notes (category: {self.category})"
        return "All writer notes"


class ProjectMetadataBlock(Block):
    """
    Fetches project-level metadata.

    Outputs: Project name, genre, total scenes, story spine
    """

    def __init__(self, block_id: str = None):
        super().__init__(block_id)

    def execute(self, project_name: str, **kwargs) -> str:
        db_path = f"projects/{project_name}/{project_name}.db"

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get project info
        cursor.execute("SELECT project_name, genre, total_scenes FROM projects LIMIT 1")
        project = cursor.fetchone()

        # Get story spine
        cursor.execute("""
            SELECT scene_number, title
            FROM scenes
            ORDER BY scene_number
        """)
        scenes = cursor.fetchall()
        conn.close()

        output = ["PROJECT METADATA:"]
        output.append(f"Title: {project['project_name']}")
        output.append(f"Genre: {project['genre']}")
        output.append(f"Total Scenes: {project['total_scenes']}")
        output.append("\nSTORY SPINE:")

        for scene in scenes:
            output.append(f"  {scene['scene_number']}. {scene['title']}")

        return "\n".join(output)

    def get_description(self) -> str:
        return "Project metadata and story spine"


class AllScenesBlock(Block):
    """
    Fetches all scenes with their basic info.

    Outputs: List of all scenes with number, title, act
    """

    def __init__(self, block_id: str = None):
        super().__init__(block_id)

    def execute(self, project_name: str, **kwargs) -> str:
        db_path = f"projects/{project_name}/{project_name}.db"

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT scene_number, title, tone, characters
            FROM scenes
            ORDER BY scene_number
        """)
        scenes = cursor.fetchall()
        conn.close()

        output = ["ALL SCENES:"]
        for scene in scenes:
            tone_str = f" (Tone: {scene['tone']})" if scene['tone'] else ""
            output.append(
                f"{scene['scene_number']}. {scene['title']}{tone_str} - {scene['characters']}"
            )

        return "\n".join(output)

    def get_description(self) -> str:
        return "All scenes (number, title, act, characters)"


class PreviousSceneBlock(Block):
    """
    Fetches the scene immediately before a given scene number.

    Outputs: Previous scene's full data
    """

    def __init__(self, scene_number: int, block_id: str = None):
        super().__init__(block_id)
        self.scene_number = scene_number

    def execute(self, project_name: str, **kwargs) -> str:
        if self.scene_number <= 1:
            return "[No previous scene - this is Scene 1]"

        prev_scene_num = self.scene_number - 1

        # Reuse SceneBlock
        prev_block = SceneBlock(prev_scene_num)
        result = prev_block.execute(project_name, **kwargs)

        return f"PREVIOUS SCENE:\n{result}"

    def get_description(self) -> str:
        return f"Scene {self.scene_number - 1} (previous scene)"

    def validate(self) -> tuple[bool, Optional[str]]:
        if self.scene_number < 1 or self.scene_number > 30:
            return (False, f"Scene number must be 1-30, got {self.scene_number}")
        return (True, None)


class NextSceneBlock(Block):
    """
    Fetches the scene immediately after a given scene number.

    Outputs: Next scene's full data
    """

    def __init__(self, scene_number: int, block_id: str = None):
        super().__init__(block_id)
        self.scene_number = scene_number

    def execute(self, project_name: str, **kwargs) -> str:
        next_scene_num = self.scene_number + 1

        if next_scene_num > 30:
            return "[No next scene - this is the final scene]"

        # Reuse SceneBlock
        next_block = SceneBlock(next_scene_num)
        result = next_block.execute(project_name, **kwargs)

        return f"NEXT SCENE:\n{result}"

    def get_description(self) -> str:
        return f"Scene {self.scene_number + 1} (next scene)"

    def validate(self) -> tuple[bool, Optional[str]]:
        if self.scene_number < 1 or self.scene_number > 30:
            return (False, f"Scene number must be 1-30, got {self.scene_number}")
        return (True, None)
