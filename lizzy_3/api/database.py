"""
Database Module - SQLite storage for project outlines.

Stores structured project data:
- Project metadata (title, logline, genre)
- Writer notes (theme, tone, comps, braindump)
- Characters (name, role, arc, flaw, etc.)
- Scenes (30 beats with descriptions)
"""

import sqlite3
import json
from pathlib import Path
from typing import Optional, List, Dict
from contextlib import contextmanager

# Database location
DB_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DB_DIR / "lizzy.db"


class Database:
    """SQLite database manager for lizzy_3 projects."""

    def __init__(self, db_path: Path = None):
        self.db_path = db_path or DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def initialize_schema(self) -> None:
        """Create all tables."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Project metadata
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS project (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL DEFAULT '',
                    title_locked INTEGER DEFAULT 0,
                    logline TEXT DEFAULT '',
                    logline_locked INTEGER DEFAULT 0,
                    genre TEXT DEFAULT 'Romantic Comedy',
                    description TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Writer notes
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS writer_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    theme TEXT DEFAULT '',
                    tone TEXT DEFAULT '',
                    comps TEXT DEFAULT '',
                    braindump TEXT DEFAULT '',
                    outline TEXT DEFAULT '[]',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Characters
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS characters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL DEFAULT '',
                    role TEXT DEFAULT '',
                    description TEXT DEFAULT '',
                    arc TEXT DEFAULT '',
                    age TEXT DEFAULT '',
                    personality TEXT DEFAULT '',
                    flaw TEXT DEFAULT '',
                    backstory TEXT DEFAULT '',
                    relationships TEXT DEFAULT '',
                    sort_order INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Scenes (30 beats)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scenes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scene_number INTEGER NOT NULL UNIQUE,
                    title TEXT DEFAULT '',
                    description TEXT DEFAULT '',
                    characters TEXT DEFAULT '',
                    tone TEXT DEFAULT '',
                    beats TEXT DEFAULT '[]',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indices
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_scenes_number ON scenes(scene_number)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_characters_order ON characters(sort_order)")

    # =========================================================================
    # PROJECT METHODS
    # =========================================================================

    def get_project(self) -> Optional[Dict]:
        """Get project metadata (single project per database)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM project LIMIT 1")
            row = cursor.fetchone()
            if row:
                return dict(row)
            # Create default project if none exists
            cursor.execute("INSERT INTO project (title) VALUES ('')")
            cursor.execute("SELECT * FROM project LIMIT 1")
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_project(self, **kwargs) -> Dict:
        """Update project metadata."""
        allowed = ['title', 'title_locked', 'logline', 'logline_locked', 'genre', 'description']
        updates = {k: v for k, v in kwargs.items() if k in allowed}

        if not updates:
            return self.get_project()

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Ensure project exists
            cursor.execute("SELECT id FROM project LIMIT 1")
            if not cursor.fetchone():
                cursor.execute("INSERT INTO project (title) VALUES ('')")

            set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
            set_clause += ", updated_at = CURRENT_TIMESTAMP"
            values = list(updates.values())

            cursor.execute(f"UPDATE project SET {set_clause} WHERE id = 1", values)

        return self.get_project()

    # =========================================================================
    # WRITER NOTES METHODS
    # =========================================================================

    def get_writer_notes(self) -> Optional[Dict]:
        """Get writer notes."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM writer_notes LIMIT 1")
            row = cursor.fetchone()
            if not row:
                # Create default if none exists
                cursor.execute("INSERT INTO writer_notes (theme) VALUES ('')")
                cursor.execute("SELECT * FROM writer_notes LIMIT 1")
                row = cursor.fetchone()
            if row:
                result = dict(row)
                # Parse outline JSON
                try:
                    result['outline'] = json.loads(result.get('outline', '[]'))
                except:
                    result['outline'] = []
                return result
            return None

    def update_writer_notes(self, **kwargs) -> Dict:
        """Update writer notes."""
        allowed = ['theme', 'tone', 'comps', 'braindump', 'outline']
        updates = {}

        for k, v in kwargs.items():
            if k in allowed:
                if k == 'outline' and isinstance(v, list):
                    updates[k] = json.dumps(v)
                else:
                    updates[k] = v

        if not updates:
            return self.get_writer_notes()

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Ensure notes exist
            cursor.execute("SELECT id FROM writer_notes LIMIT 1")
            if not cursor.fetchone():
                cursor.execute("INSERT INTO writer_notes (theme) VALUES ('')")

            set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
            set_clause += ", updated_at = CURRENT_TIMESTAMP"
            values = list(updates.values())

            cursor.execute(f"UPDATE writer_notes SET {set_clause} WHERE id = 1", values)

        return self.get_writer_notes()

    # =========================================================================
    # CHARACTER METHODS
    # =========================================================================

    def get_characters(self) -> List[Dict]:
        """Get all characters sorted by order."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM characters ORDER BY sort_order, id")
            return [dict(row) for row in cursor.fetchall()]

    def get_character(self, character_id: int) -> Optional[Dict]:
        """Get a single character."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM characters WHERE id = ?", (character_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def create_character(self, **kwargs) -> Dict:
        """Create a new character."""
        allowed = ['name', 'role', 'description', 'arc', 'age', 'personality', 'flaw', 'backstory', 'relationships', 'sort_order']
        data = {k: v for k, v in kwargs.items() if k in allowed}

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Get next sort order if not specified
            if 'sort_order' not in data:
                cursor.execute("SELECT COALESCE(MAX(sort_order), -1) + 1 FROM characters")
                data['sort_order'] = cursor.fetchone()[0]

            columns = ", ".join(data.keys())
            placeholders = ", ".join("?" * len(data))
            values = list(data.values())

            cursor.execute(f"INSERT INTO characters ({columns}) VALUES ({placeholders})", values)
            return self.get_character(cursor.lastrowid)

    def update_character(self, character_id: int, **kwargs) -> Optional[Dict]:
        """Update a character."""
        allowed = ['name', 'role', 'description', 'arc', 'age', 'personality', 'flaw', 'backstory', 'relationships', 'sort_order']
        updates = {k: v for k, v in kwargs.items() if k in allowed}

        if not updates:
            return self.get_character(character_id)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
            set_clause += ", updated_at = CURRENT_TIMESTAMP"
            values = list(updates.values()) + [character_id]

            cursor.execute(f"UPDATE characters SET {set_clause} WHERE id = ?", values)

        return self.get_character(character_id)

    def delete_character(self, character_id: int) -> bool:
        """Delete a character."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM characters WHERE id = ?", (character_id,))
            return cursor.rowcount > 0

    # =========================================================================
    # SCENE METHODS
    # =========================================================================

    def get_scenes(self) -> List[Dict]:
        """Get all scenes sorted by number."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM scenes ORDER BY scene_number")
            scenes = []
            for row in cursor.fetchall():
                scene = dict(row)
                try:
                    scene['beats'] = json.loads(scene.get('beats', '[]'))
                except:
                    scene['beats'] = []
                scenes.append(scene)
            return scenes

    def get_scene(self, scene_id: int) -> Optional[Dict]:
        """Get a single scene."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM scenes WHERE id = ?", (scene_id,))
            row = cursor.fetchone()
            if row:
                scene = dict(row)
                try:
                    scene['beats'] = json.loads(scene.get('beats', '[]'))
                except:
                    scene['beats'] = []
                return scene
            return None

    def create_scene(self, scene_number: int, **kwargs) -> Dict:
        """Create a new scene."""
        allowed = ['title', 'description', 'characters', 'tone', 'beats']
        data = {'scene_number': scene_number}

        for k, v in kwargs.items():
            if k in allowed:
                if k == 'beats' and isinstance(v, list):
                    data[k] = json.dumps(v)
                else:
                    data[k] = v

        with self.get_connection() as conn:
            cursor = conn.cursor()
            columns = ", ".join(data.keys())
            placeholders = ", ".join("?" * len(data))
            values = list(data.values())

            cursor.execute(f"INSERT INTO scenes ({columns}) VALUES ({placeholders})", values)
            return self.get_scene(cursor.lastrowid)

    def update_scene(self, scene_id: int, **kwargs) -> Optional[Dict]:
        """Update a scene."""
        allowed = ['scene_number', 'title', 'description', 'characters', 'tone', 'beats']
        updates = {}

        for k, v in kwargs.items():
            if k in allowed:
                if k == 'beats' and isinstance(v, list):
                    updates[k] = json.dumps(v)
                else:
                    updates[k] = v

        if not updates:
            return self.get_scene(scene_id)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
            set_clause += ", updated_at = CURRENT_TIMESTAMP"
            values = list(updates.values()) + [scene_id]

            cursor.execute(f"UPDATE scenes SET {set_clause} WHERE id = ?", values)

        return self.get_scene(scene_id)

    def delete_scene(self, scene_id: int) -> bool:
        """Delete a scene."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM scenes WHERE id = ?", (scene_id,))
            return cursor.rowcount > 0

    def upsert_scene(self, scene_number: int, **kwargs) -> Dict:
        """Insert or update a scene by scene_number."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM scenes WHERE scene_number = ?", (scene_number,))
            row = cursor.fetchone()

            if row:
                return self.update_scene(row['id'], **kwargs)
            else:
                return self.create_scene(scene_number, **kwargs)


# Global database instance
db = Database()
db.initialize_schema()
