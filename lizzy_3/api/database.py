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
        """Create all tables with multi-project support."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Projects table (can have multiple projects)
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

            # Writer notes (per project)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS writer_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    theme TEXT DEFAULT '',
                    tone TEXT DEFAULT '',
                    comps TEXT DEFAULT '',
                    braindump TEXT DEFAULT '',
                    outline TEXT DEFAULT '[]',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES project(id) ON DELETE CASCADE
                )
            """)

            # Characters (per project)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS characters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
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
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES project(id) ON DELETE CASCADE
                )
            """)

            # Acts (per project)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS acts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    title TEXT NOT NULL DEFAULT '',
                    description TEXT DEFAULT '',
                    sort_order INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES project(id) ON DELETE CASCADE
                )
            """)

            # Scenes (per project, within acts)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scenes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    act_id INTEGER,
                    scene_number INTEGER NOT NULL,
                    title TEXT DEFAULT '',
                    description TEXT DEFAULT '',
                    characters TEXT DEFAULT '',
                    tone TEXT DEFAULT '',
                    beats TEXT DEFAULT '[]',
                    canvas_content TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES project(id) ON DELETE CASCADE,
                    FOREIGN KEY (act_id) REFERENCES acts(id) ON DELETE SET NULL,
                    UNIQUE(project_id, scene_number)
                )
            """)

            # Conversations (per project)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    title TEXT DEFAULT 'New Chat',
                    messages TEXT DEFAULT '[]',
                    active_buckets TEXT DEFAULT '[]',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES project(id) ON DELETE CASCADE
                )
            """)

            # Create indices for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_writer_notes_project ON writer_notes(project_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_characters_project ON characters(project_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_acts_project ON acts(project_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_scenes_project ON scenes(project_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_scenes_act ON scenes(act_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversations_project ON conversations(project_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversations_updated ON conversations(updated_at DESC)")

    # =========================================================================
    # PROJECT METHODS (Multi-project support)
    # =========================================================================

    def list_projects(self) -> List[Dict]:
        """List all projects."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM project ORDER BY updated_at DESC")
            return [dict(row) for row in cursor.fetchall()]

    def get_project(self, project_id: int) -> Optional[Dict]:
        """Get a single project by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM project WHERE id = ?", (project_id,))
            row = cursor.fetchone()
            if row:
                project = dict(row)
                # Generate memory_bank_id if missing
                if not project.get('memory_bank_id'):
                    bank_id = f"lizzy-{uuid.uuid4().hex[:8]}"
                    cursor.execute("UPDATE project SET memory_bank_id = ? WHERE id = ?", (bank_id, project['id']))
                    project['memory_bank_id'] = bank_id
                return project
            return None

    def create_project(self, title: str = "", logline: str = "", genre: str = "Romantic Comedy", use_template: bool = False) -> Dict:
        """Create a new project and return it."""
        bank_id = f"lizzy-{uuid.uuid4().hex[:8]}"
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO project (title, logline, genre, memory_bank_id) VALUES (?, ?, ?, ?)",
                (title, logline, genre, bank_id)
            )
            project_id = cursor.lastrowid

        # Initialize writer notes for this project
        self._create_writer_notes(project_id)

        # Optionally create template (acts, scenes, characters)
        if use_template:
            self.initialize_scene_template(project_id)
            self.initialize_character_template(project_id)

        return self.get_project(project_id)

    def update_project(self, project_id: int, **kwargs) -> Optional[Dict]:
        """Update project metadata."""
        allowed = ['title', 'title_locked', 'logline', 'logline_locked', 'genre', 'description', 'phase']
        updates = {k: v for k, v in kwargs.items() if k in allowed}

        if not updates:
            return self.get_project(project_id)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
            set_clause += ", updated_at = CURRENT_TIMESTAMP"
            values = list(updates.values()) + [project_id]
            cursor.execute(f"UPDATE project SET {set_clause} WHERE id = ?", values)

        return self.get_project(project_id)

    def delete_project(self, project_id: int) -> Optional[str]:
        """Delete a project and all its data. Returns memory_bank_id for cleanup."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Get memory bank ID before deleting
            cursor.execute("SELECT memory_bank_id FROM project WHERE id = ?", (project_id,))
            row = cursor.fetchone()
            old_bank_id = row['memory_bank_id'] if row else None

            # Delete project (CASCADE will delete related data)
            cursor.execute("DELETE FROM project WHERE id = ?", (project_id,))
            return old_bank_id if cursor.rowcount > 0 else None

    # =========================================================================
    # WRITER NOTES METHODS
    # =========================================================================

    def _create_writer_notes(self, project_id: int) -> None:
        """Create default writer notes for a project (internal use)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO writer_notes (project_id, theme) VALUES (?, '')", (project_id,))

    def get_writer_notes(self, project_id: int) -> Optional[Dict]:
        """Get writer notes for a project."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM writer_notes WHERE project_id = ?", (project_id,))
            row = cursor.fetchone()
            if row:
                result = dict(row)
                try:
                    result['outline'] = json.loads(result.get('outline', '[]'))
                except:
                    result['outline'] = []
                return result
            return None

    def update_writer_notes(self, project_id: int, **kwargs) -> Optional[Dict]:
        """Update writer notes for a project."""
        allowed = ['theme', 'tone', 'comps', 'braindump', 'outline']
        updates = {}

        for k, v in kwargs.items():
            if k in allowed:
                if k == 'outline' and isinstance(v, list):
                    updates[k] = json.dumps(v)
                else:
                    updates[k] = v

        if not updates:
            return self.get_writer_notes(project_id)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
            set_clause += ", updated_at = CURRENT_TIMESTAMP"
            values = list(updates.values()) + [project_id]
            cursor.execute(f"UPDATE writer_notes SET {set_clause} WHERE project_id = ?", values)

        return self.get_writer_notes(project_id)

    # =========================================================================
    # CHARACTER METHODS
    # =========================================================================

    def get_characters(self, project_id: int) -> List[Dict]:
        """Get all characters for a project."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM characters WHERE project_id = ? ORDER BY sort_order, id", (project_id,))
            return [dict(row) for row in cursor.fetchall()]

    def get_character(self, character_id: int) -> Optional[Dict]:
        """Get a single character."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM characters WHERE id = ?", (character_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def create_character(self, project_id: int, **kwargs) -> Dict:
        """Create a new character in a project."""
        allowed = ['name', 'role', 'description', 'arc', 'age', 'personality', 'flaw', 'backstory', 'relationships', 'sort_order']
        data = {k: v for k, v in kwargs.items() if k in allowed}
        data['project_id'] = project_id

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Get next sort order if not specified
            if 'sort_order' not in data:
                cursor.execute("SELECT COALESCE(MAX(sort_order), -1) + 1 FROM characters WHERE project_id = ?", (project_id,))
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

    def get_scenes(self, project_id: int) -> List[Dict]:
        """Get all scenes for a project."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM scenes WHERE project_id = ? ORDER BY scene_number", (project_id,))
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

    def create_scene(self, project_id: int, scene_number: int, **kwargs) -> Dict:
        """Create a new scene in a project."""
        allowed = ['title', 'description', 'characters', 'tone', 'beats', 'canvas_content', 'act_id']
        data = {'project_id': project_id, 'scene_number': scene_number}

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

    def reorder_scene(self, project_id: int, scene_id: int, new_scene_number: int) -> Optional[Dict]:
        """Move a scene to a new position within a project."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Get the scene's current position
            cursor.execute("SELECT scene_number FROM scenes WHERE id = ? AND project_id = ?", (scene_id, project_id))
            row = cursor.fetchone()
            if not row:
                return None

            old_number = row['scene_number']
            if old_number == new_scene_number:
                return self.get_scene(scene_id)

            # Temporarily set to -1 to avoid unique constraint issues
            cursor.execute("UPDATE scenes SET scene_number = -1 WHERE id = ?", (scene_id,))

            # Shift scenes between old and new positions (within same project)
            if new_scene_number < old_number:
                cursor.execute("""
                    UPDATE scenes
                    SET scene_number = scene_number + 1
                    WHERE project_id = ? AND scene_number >= ? AND scene_number < ?
                """, (project_id, new_scene_number, old_number))
            else:
                cursor.execute("""
                    UPDATE scenes
                    SET scene_number = scene_number - 1
                    WHERE project_id = ? AND scene_number > ? AND scene_number <= ?
                """, (project_id, old_number, new_scene_number))

            cursor.execute("UPDATE scenes SET scene_number = ? WHERE id = ?", (new_scene_number, scene_id))

        return self.get_scene(scene_id)

    # =========================================================================
    # ACT METHODS
    # =========================================================================

    def get_acts(self, project_id: int) -> List[Dict]:
        """Get all acts for a project."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM acts WHERE project_id = ? ORDER BY sort_order, id", (project_id,))
            return [dict(row) for row in cursor.fetchall()]

    def get_act(self, act_id: int) -> Optional[Dict]:
        """Get a single act by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM acts WHERE id = ?", (act_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def create_act(self, project_id: int, title: str, description: str = '', sort_order: int = None) -> Dict:
        """Create a new act in a project."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Auto-assign sort_order if not provided
            if sort_order is None:
                cursor.execute("SELECT COALESCE(MAX(sort_order), -1) + 1 FROM acts WHERE project_id = ?", (project_id,))
                sort_order = cursor.fetchone()[0]

            cursor.execute(
                "INSERT INTO acts (project_id, title, description, sort_order) VALUES (?, ?, ?, ?)",
                (project_id, title, description, sort_order)
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

    def get_scenes_by_act(self, project_id: int, act_id: int = None) -> List[Dict]:
        """Get scenes for a specific act within a project."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if act_id is None:
                cursor.execute("SELECT * FROM scenes WHERE project_id = ? AND act_id IS NULL ORDER BY scene_number", (project_id,))
            else:
                cursor.execute("SELECT * FROM scenes WHERE project_id = ? AND act_id = ? ORDER BY scene_number", (project_id, act_id))
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

    def initialize_scene_template(self, project_id: int) -> List[Dict]:
        """Create 4 acts with 30 scenes for a project."""

        # Create the 4 acts first
        acts_data = [
            {"title": "Act 1 - Setup", "description": "Establish the world, introduce characters, catalyst/meet-cute, break into two"},
            {"title": "Act 2A - Fun & Games", "description": "B-story, falling in love, getting closer, building to midpoint"},
            {"title": "Act 2B - Complications", "description": "Doubts, external pressure, secrets, breakup, dark night of the soul"},
            {"title": "Act 3 - Resolution", "description": "Realization, grand gesture, confronting flaws, final image"},
        ]

        act_ids = []
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for i, act in enumerate(acts_data):
                cursor.execute(
                    "INSERT INTO acts (project_id, title, description, sort_order) VALUES (?, ?, ?, ?)",
                    (project_id, act["title"], act["description"], i)
                )
                act_ids.append(cursor.lastrowid)

        # Scene beats with act assignments
        beats = [
            # Act 1 - Setup (7 scenes)
            (1, "Opening Image", act_ids[0]),
            (2, "Theme Stated", act_ids[0]),
            (3, "Setup - Protagonist's World", act_ids[0]),
            (4, "Setup - The Flaw", act_ids[0]),
            (5, "Catalyst / Meet-Cute", act_ids[0]),
            (6, "Debate - Should They?", act_ids[0]),
            (7, "Break Into Two", act_ids[0]),
            # Act 2A - Fun & Games (5 scenes)
            (8, "B Story / Supporting Cast", act_ids[1]),
            (9, "Fun and Games - Falling", act_ids[1]),
            (10, "Fun and Games - The Date", act_ids[1]),
            (11, "Fun and Games - Getting Closer", act_ids[1]),
            (12, "Midpoint - The Kiss / Declaration", act_ids[1]),
            # Act 2B - Complications (6 scenes)
            (13, "Bad Guys Close In - Doubts", act_ids[2]),
            (14, "Bad Guys Close In - External Pressure", act_ids[2]),
            (15, "Bad Guys Close In - Secrets Surface", act_ids[2]),
            (16, "All Is Lost - The Breakup", act_ids[2]),
            (17, "Dark Night of the Soul", act_ids[2]),
            (18, "Break Into Three - Realization", act_ids[2]),
            # Act 3 - Resolution (12 scenes)
            (19, "Gathering the Team", act_ids[3]),
            (20, "Finale - Storming the Castle", act_ids[3]),
            (21, "Finale - The Grand Gesture", act_ids[3]),
            (22, "Finale - Confronting the Flaw", act_ids[3]),
            (23, "Finale - The Choice", act_ids[3]),
            (24, "Final Image - Together", act_ids[3]),
            (25, "Tag Scene 1", act_ids[3]),
            (26, "Tag Scene 2", act_ids[3]),
            (27, "Tag Scene 3", act_ids[3]),
            (28, "Tag Scene 4", act_ids[3]),
            (29, "Tag Scene 5", act_ids[3]),
            (30, "Tag Scene 6", act_ids[3]),
        ]

        with self.get_connection() as conn:
            cursor = conn.cursor()
            for scene_num, title, act_id in beats:
                cursor.execute(
                    "INSERT INTO scenes (project_id, scene_number, title, description, act_id) VALUES (?, ?, ?, ?, ?)",
                    (project_id, scene_num, title, "", act_id)
                )

        return self.get_scenes(project_id)

    def initialize_character_template(self, project_id: int) -> List[Dict]:
        """Create 5 default character role slots for a project."""
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
                    "INSERT INTO characters (project_id, name, role, description, sort_order) VALUES (?, ?, ?, ?, ?)",
                    (project_id, char["name"], char["role"], char["description"], i)
                )

        return self.get_characters(project_id)

    # =========================================================================
    # CONVERSATION METHODS
    # =========================================================================

    def get_conversations(self, project_id: int) -> List[Dict]:
        """Get all conversations for a project."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, title, created_at, updated_at FROM conversations WHERE project_id = ? ORDER BY updated_at DESC",
                (project_id,)
            )
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

    def create_conversation(self, project_id: int, title: str = "New Chat", messages: List[Dict] = None, active_buckets: List[str] = None) -> Dict:
        """Create a new conversation in a project."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO conversations (project_id, title, messages, active_buckets) VALUES (?, ?, ?, ?)",
                (project_id, title, json.dumps(messages or []), json.dumps(active_buckets or []))
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
