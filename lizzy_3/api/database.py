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
import uuid
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
                    phase TEXT DEFAULT 'intake',
                    memory_bank_id TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Migration: add memory_bank_id if missing
            cursor.execute("PRAGMA table_info(project)")
            project_columns = [row[1] for row in cursor.fetchall()]
            if 'memory_bank_id' not in project_columns:
                cursor.execute("ALTER TABLE project ADD COLUMN memory_bank_id TEXT DEFAULT ''")
            if 'phase' not in project_columns:
                cursor.execute("ALTER TABLE project ADD COLUMN phase TEXT DEFAULT 'intake'")

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

            # Acts (story structure)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS acts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL DEFAULT '',
                    description TEXT DEFAULT '',
                    sort_order INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Scenes (within acts)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scenes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    act_id INTEGER,
                    scene_number INTEGER NOT NULL UNIQUE,
                    title TEXT DEFAULT '',
                    description TEXT DEFAULT '',
                    characters TEXT DEFAULT '',
                    tone TEXT DEFAULT '',
                    beats TEXT DEFAULT '[]',
                    canvas_content TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (act_id) REFERENCES acts(id) ON DELETE SET NULL
                )
            """)

            # Migration: add canvas_content if missing
            cursor.execute("PRAGMA table_info(scenes)")
            columns = [row[1] for row in cursor.fetchall()]
            if 'canvas_content' not in columns:
                cursor.execute("ALTER TABLE scenes ADD COLUMN canvas_content TEXT DEFAULT ''")
            if 'act_id' not in columns:
                cursor.execute("ALTER TABLE scenes ADD COLUMN act_id INTEGER")

            # Conversations (chat history with Syd)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT DEFAULT 'New Chat',
                    messages TEXT DEFAULT '[]',
                    active_buckets TEXT DEFAULT '[]',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Migration: add active_buckets if missing
            cursor.execute("PRAGMA table_info(conversations)")
            conv_columns = [row[1] for row in cursor.fetchall()]
            if 'active_buckets' not in conv_columns:
                cursor.execute("ALTER TABLE conversations ADD COLUMN active_buckets TEXT DEFAULT '[]'")

            # Create indices
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_scenes_number ON scenes(scene_number)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_scenes_act ON scenes(act_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_acts_order ON acts(sort_order)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_characters_order ON characters(sort_order)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversations_updated ON conversations(updated_at DESC)")

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
                project = dict(row)
                # Generate memory_bank_id if missing
                if not project.get('memory_bank_id'):
                    bank_id = f"lizzy-{uuid.uuid4().hex[:8]}"
                    cursor.execute("UPDATE project SET memory_bank_id = ? WHERE id = ?", (bank_id, project['id']))
                    conn.commit()
                    project['memory_bank_id'] = bank_id
                return project
            # Create default project if none exists
            bank_id = f"lizzy-{uuid.uuid4().hex[:8]}"
            cursor.execute("INSERT INTO project (title, memory_bank_id) VALUES ('', ?)", (bank_id,))
            cursor.execute("SELECT * FROM project LIMIT 1")
            row = cursor.fetchone()
            return dict(row) if row else None

    def reset_project(self) -> Optional[str]:
        """Delete all project data (project, notes, characters, scenes).

        Returns the old memory_bank_id so it can be cleared from Hindsight.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Get the old memory bank ID before deleting
            cursor.execute("SELECT memory_bank_id FROM project LIMIT 1")
            row = cursor.fetchone()
            old_bank_id = row['memory_bank_id'] if row else None

            cursor.execute("DELETE FROM project")
            cursor.execute("DELETE FROM writer_notes")
            cursor.execute("DELETE FROM characters")
            cursor.execute("DELETE FROM scenes")
            return old_bank_id

    def update_project(self, **kwargs) -> Dict:
        """Update project metadata."""
        allowed = ['title', 'title_locked', 'logline', 'logline_locked', 'genre', 'description', 'phase']
        updates = {k: v for k, v in kwargs.items() if k in allowed}

        if not updates:
            return self.get_project()

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Ensure project exists with a bank ID
            cursor.execute("SELECT id FROM project LIMIT 1")
            row = cursor.fetchone()
            if not row:
                bank_id = f"lizzy-{uuid.uuid4().hex[:8]}"
                cursor.execute("INSERT INTO project (title, memory_bank_id) VALUES ('', ?)", (bank_id,))
                cursor.execute("SELECT id FROM project LIMIT 1")
                row = cursor.fetchone()

            project_id = row[0]
            set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
            set_clause += ", updated_at = CURRENT_TIMESTAMP"
            values = list(updates.values()) + [project_id]

            cursor.execute(f"UPDATE project SET {set_clause} WHERE id = ?", values)

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
            char_id = cursor.lastrowid
        return self.get_character(char_id)

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
        allowed = ['title', 'description', 'characters', 'tone', 'beats', 'canvas_content', 'act_id']
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
            scene_id = cursor.lastrowid
        return self.get_scene(scene_id)

    def update_scene(self, scene_id: int, **kwargs) -> Optional[Dict]:
        """Update a scene."""
        allowed = ['scene_number', 'title', 'description', 'characters', 'tone', 'beats', 'canvas_content', 'act_id']
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

    def reorder_scene(self, scene_id: int, new_scene_number: int) -> Optional[Dict]:
        """Move a scene to a new position, shifting other scenes as needed."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Get the scene's current position
            cursor.execute("SELECT scene_number FROM scenes WHERE id = ?", (scene_id,))
            row = cursor.fetchone()
            if not row:
                return None

            old_number = row['scene_number']
            if old_number == new_scene_number:
                return self.get_scene(scene_id)

            # Temporarily set to -1 to avoid unique constraint issues
            cursor.execute("UPDATE scenes SET scene_number = -1 WHERE id = ?", (scene_id,))

            # Shift scenes between old and new positions
            if new_scene_number < old_number:
                # Moving up: shift scenes in range [new, old) down by 1
                cursor.execute("""
                    UPDATE scenes
                    SET scene_number = scene_number + 1
                    WHERE scene_number >= ? AND scene_number < ?
                """, (new_scene_number, old_number))
            else:
                # Moving down: shift scenes in range (old, new] up by 1
                cursor.execute("""
                    UPDATE scenes
                    SET scene_number = scene_number - 1
                    WHERE scene_number > ? AND scene_number <= ?
                """, (old_number, new_scene_number))

            # Set the scene to its new position
            cursor.execute(
                "UPDATE scenes SET scene_number = ? WHERE id = ?",
                (new_scene_number, scene_id)
            )

        return self.get_scene(scene_id)

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

    # =========================================================================
    # ACT METHODS
    # =========================================================================

    def get_acts(self) -> List[Dict]:
        """Get all acts ordered by sort_order."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM acts ORDER BY sort_order, id")
            return [dict(row) for row in cursor.fetchall()]

    def get_act(self, act_id: int) -> Optional[Dict]:
        """Get a single act by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM acts WHERE id = ?", (act_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def create_act(self, title: str, description: str = '', sort_order: int = None) -> Dict:
        """Create a new act."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Auto-assign sort_order if not provided
            if sort_order is None:
                cursor.execute("SELECT COALESCE(MAX(sort_order), -1) + 1 FROM acts")
                sort_order = cursor.fetchone()[0]

            cursor.execute(
                "INSERT INTO acts (title, description, sort_order) VALUES (?, ?, ?)",
                (title, description, sort_order)
            )
            act_id = cursor.lastrowid

        return self.get_act(act_id)

    def update_act(self, act_id: int, **kwargs) -> Optional[Dict]:
        """Update an act's properties."""
        allowed = ['title', 'description', 'sort_order']
        updates = {k: v for k, v in kwargs.items() if k in allowed}

        if not updates:
            return self.get_act(act_id)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
            set_clause += ", updated_at = CURRENT_TIMESTAMP"
            values = list(updates.values()) + [act_id]
            cursor.execute(f"UPDATE acts SET {set_clause} WHERE id = ?", values)

        return self.get_act(act_id)

    def delete_act(self, act_id: int) -> bool:
        """Delete an act. Scenes in this act will have act_id set to NULL."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM acts WHERE id = ?", (act_id,))
            return cursor.rowcount > 0

    def get_scenes_by_act(self, act_id: int = None) -> List[Dict]:
        """Get scenes for a specific act, or unassigned scenes if act_id is None."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if act_id is None:
                cursor.execute("SELECT * FROM scenes WHERE act_id IS NULL ORDER BY scene_number")
            else:
                cursor.execute("SELECT * FROM scenes WHERE act_id = ? ORDER BY scene_number", (act_id,))
            return [dict(row) for row in cursor.fetchall()]

    def assign_scene_to_act(self, scene_id: int, act_id: int = None) -> Optional[Dict]:
        """Assign a scene to an act (or remove from act if act_id is None)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE scenes SET act_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (act_id, scene_id)
            )
        return self.get_scene(scene_id)

    # =========================================================================
    # TEMPLATE INITIALIZATION
    # =========================================================================

    def initialize_scene_template(self) -> List[Dict]:
        """Create 30 empty scenes for the beat sheet template."""
        # Standard 30-beat romcom structure
        beat_titles = [
            "Opening Image",
            "Theme Stated",
            "Setup - Protagonist's World",
            "Setup - The Flaw",
            "Catalyst / Meet-Cute",
            "Debate - Should They?",
            "Break Into Two",
            "B Story / Supporting Cast",
            "Fun and Games - Falling",
            "Fun and Games - The Date",
            "Fun and Games - Getting Closer",
            "Midpoint - The Kiss / Declaration",
            "Bad Guys Close In - Doubts",
            "Bad Guys Close In - External Pressure",
            "Bad Guys Close In - Secrets Surface",
            "All Is Lost - The Breakup",
            "Dark Night of the Soul",
            "Break Into Three - Realization",
            "Gathering the Team",
            "Finale - Storming the Castle",
            "Finale - The Grand Gesture",
            "Finale - Confronting the Flaw",
            "Finale - The Choice",
            "Final Image - Together",
            "Tag Scene 1",
            "Tag Scene 2",
            "Tag Scene 3",
            "Tag Scene 4",
            "Tag Scene 5",
            "Tag Scene 6"
        ]

        with self.get_connection() as conn:
            cursor = conn.cursor()
            for i, title in enumerate(beat_titles, 1):
                cursor.execute(
                    "INSERT OR IGNORE INTO scenes (scene_number, title, description) VALUES (?, ?, ?)",
                    (i, title, "")
                )

        return self.get_scenes()

    def initialize_character_template(self) -> List[Dict]:
        """Create 5 default character role slots."""
        character_roles = [
            {"name": "", "role": "Protagonist", "description": "The main character whose journey we follow."},
            {"name": "", "role": "Love Interest", "description": "The romantic counterpart to the protagonist."},
            {"name": "", "role": "Best Friend", "description": "The protagonist's confidante and supporter."},
            {"name": "", "role": "Obstacle", "description": "A character who creates conflict or complications."},
            {"name": "", "role": "Mentor", "description": "A wise figure who guides the protagonist."},
        ]

        with self.get_connection() as conn:
            cursor = conn.cursor()
            for i, char in enumerate(character_roles):
                cursor.execute(
                    "INSERT INTO characters (name, role, description, sort_order) VALUES (?, ?, ?, ?)",
                    (char["name"], char["role"], char["description"], i)
                )

        return self.get_characters()

    def initialize_project_with_template(self, title: str = "", logline: str = "", genre: str = "Romantic Comedy") -> Dict:
        """Create a new project with the full 30-scene + 5-character template."""
        # Create project
        self.update_project(title=title, logline=logline, genre=genre)

        # Initialize writer notes
        self.get_writer_notes()  # Creates default row

        # Create scene template
        self.initialize_scene_template()

        # Create character template
        self.initialize_character_template()

        return {
            "project": self.get_project(),
            "scenes": self.get_scenes(),
            "characters": self.get_characters()
        }

    # =========================================================================
    # CONVERSATION METHODS
    # =========================================================================

    def get_conversations(self) -> List[Dict]:
        """Get all conversations, most recent first."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, title, created_at, updated_at FROM conversations ORDER BY updated_at DESC")
            return [dict(row) for row in cursor.fetchall()]

    def get_conversation(self, conversation_id: int) -> Optional[Dict]:
        """Get a single conversation with messages."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,))
            row = cursor.fetchone()
            if row:
                conv = dict(row)
                conv['messages'] = json.loads(conv['messages'] or '[]')
                conv['active_buckets'] = json.loads(conv.get('active_buckets') or '[]')
                return conv
            return None

    def create_conversation(self, title: str = "New Chat", messages: List[Dict] = None, active_buckets: List[str] = None) -> Dict:
        """Create a new conversation."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO conversations (title, messages, active_buckets) VALUES (?, ?, ?)",
                (title, json.dumps(messages or []), json.dumps(active_buckets or []))
            )
            conv_id = cursor.lastrowid
        return self.get_conversation(conv_id)

    def update_conversation(self, conversation_id: int, title: str = None, messages: List[Dict] = None, active_buckets: List[str] = None) -> Optional[Dict]:
        """Update a conversation."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            updates = []
            values = []

            if title is not None:
                updates.append("title = ?")
                values.append(title)

            if messages is not None:
                updates.append("messages = ?")
                values.append(json.dumps(messages))

            if active_buckets is not None:
                updates.append("active_buckets = ?")
                values.append(json.dumps(active_buckets))

            if updates:
                updates.append("updated_at = CURRENT_TIMESTAMP")
                values.append(conversation_id)
                cursor.execute(
                    f"UPDATE conversations SET {', '.join(updates)} WHERE id = ?",
                    values
                )

        return self.get_conversation(conversation_id)

    def delete_conversation(self, conversation_id: int) -> bool:
        """Delete a conversation."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
            return cursor.rowcount > 0


# Global database instance
db = Database()
db.initialize_schema()
