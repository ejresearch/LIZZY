"""
Database Module - SQL-Based Structured Memory

Provides isolated SQLite databases for each project with proper
schema for characters, scenes, brainstorm sessions, and drafts.

From Lizzy White Paper:
"SQL-Based Structured Memory acts as the backbone for project data
management, ensuring well organized data encapsulation and facilitating
seamless integration across the various modules."
"""

import sqlite3
from pathlib import Path
from typing import Optional, List
from contextlib import contextmanager


class Database:
    """
    SQLite database manager for Lizzy projects.

    Each project gets its own isolated database with:
    - projects: Project metadata
    - characters: Character profiles
    - scenes: Scene outlines
    - brainstorm_sessions: AI-generated ideas
    - drafts: Versioned screenplay drafts
    """

    def __init__(self, db_path: Path):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path

    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections.

        Ensures proper transaction handling and connection cleanup.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Access columns by name
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def initialize_schema(self) -> None:
        """
        Create all necessary tables for a new project.

        Schema design supports:
        - Project metadata tracking
        - Character profiles with roles
        - Scene outlines with character associations
        - Brainstorming sessions with tone/bucket tracking
        - Versioned draft storage
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Projects table - metadata about the screenplay
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    genre TEXT DEFAULT 'Romantic Comedy',
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Characters table - protagonist, love interest, supporting cast
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS characters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    role TEXT,  -- protagonist, love_interest, antagonist, supporting
                    arc TEXT,   -- character arc/transformation
                    age TEXT,   -- character age
                    personality TEXT,  -- personality traits
                    flaw TEXT,  -- character flaw/weakness
                    backstory TEXT,  -- character backstory
                    relationships TEXT,  -- relationships to other characters
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Scenes table - screenplay structure
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scenes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scene_number INTEGER NOT NULL,
                    title TEXT,
                    description TEXT,
                    characters TEXT,  -- Comma-separated character names
                    tone TEXT,        -- Desired tone for this scene
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(scene_number)
                )
            """)

            # Brainstorm sessions - RAG-powered creative ideas
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS brainstorm_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scene_id INTEGER NOT NULL,
                    tone TEXT,            -- Tone preset used
                    bucket_used TEXT,     -- Which RAG bucket was queried
                    content TEXT NOT NULL,  -- Generated brainstorm ideas
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (scene_id) REFERENCES scenes(id)
                )
            """)

            # Drafts table - versioned screenplay outputs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS drafts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version INTEGER NOT NULL DEFAULT 1,
                    content TEXT NOT NULL,
                    scene_id INTEGER,  -- NULL if full draft, or specific scene
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (scene_id) REFERENCES scenes(id)
                )
            """)

            # Scene drafts table - individual scene versions with metadata
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scene_drafts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scene_id INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    version INTEGER DEFAULT 1,
                    word_count INTEGER,
                    tokens_used INTEGER,
                    cost_estimate REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (scene_id) REFERENCES scenes(id)
                )
            """)

            # Writer notes table - creative project notes
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS writer_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    logline TEXT,
                    theme TEXT,
                    inspiration TEXT,
                    tone TEXT,
                    comps TEXT,  -- Comparable titles
                    braindump TEXT,
                    outline TEXT,  -- JSON array of outline beats
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Chat messages table - conversation history with expert buckets
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role TEXT NOT NULL,  -- 'user' or 'assistant'
                    content TEXT NOT NULL,  -- User query or assistant response
                    focused_scene INTEGER,  -- Scene context if any
                    experts TEXT,  -- JSON array of expert responses (for assistant messages)
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Ideate sessions table - IDEATE phase conversation state
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ideate_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,  -- Project/session name
                    stage TEXT DEFAULT 'explore',  -- explore, build_out, complete
                    title TEXT,  -- Locked title
                    logline TEXT,  -- Locked logline
                    title_locked INTEGER DEFAULT 0,
                    logline_locked INTEGER DEFAULT 0,
                    characters TEXT,  -- JSON array of character objects
                    outline TEXT,  -- JSON array of outline beats
                    beats TEXT,  -- JSON array of scene beats
                    notebook TEXT,  -- JSON array of notebook ideas
                    theme TEXT,
                    tone TEXT,
                    comps TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Ideate messages table - conversation history for ideate sessions
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ideate_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    role TEXT NOT NULL,  -- 'user' or 'assistant'
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES ideate_sessions(id)
                )
            """)

            # Create indices for performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_ideate_messages_session
                ON ideate_messages(session_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_scenes_number
                ON scenes(scene_number)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_brainstorm_scene
                ON brainstorm_sessions(scene_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_drafts_version
                ON drafts(version DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_scene_drafts_scene
                ON scene_drafts(scene_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_scene_drafts_version
                ON scene_drafts(version DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_chat_messages_created
                ON chat_messages(created_at DESC)
            """)

    def insert_project(self, name: str, genre: str = "Romantic Comedy", description: str = "") -> int:
        """Insert project metadata."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO projects (name, genre, description) VALUES (?, ?, ?)",
                (name, genre, description)
            )
            return cursor.lastrowid

    def get_project(self) -> Optional[dict]:
        """Get project metadata (assumes single project per database)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM projects LIMIT 1")
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_writer_notes(self) -> Optional[dict]:
        """Get writer notes (assumes single notes row per database)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM writer_notes LIMIT 1")
            row = cursor.fetchone()
            return dict(row) if row else None

    def upsert_writer_notes(
        self,
        logline: str = "",
        theme: str = "",
        inspiration: str = "",
        tone: str = "",
        comps: str = "",
        braindump: str = "",
        outline: str = ""
    ) -> int:
        """Insert or update writer notes."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Check if notes already exist
            cursor.execute("SELECT id FROM writer_notes LIMIT 1")
            existing = cursor.fetchone()

            if existing:
                # Update existing
                cursor.execute("""
                    UPDATE writer_notes
                    SET logline = ?, theme = ?, inspiration = ?,
                        tone = ?, comps = ?, braindump = ?, outline = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (logline, theme, inspiration, tone, comps, braindump, outline, existing[0]))
                return existing[0]
            else:
                # Insert new
                cursor.execute("""
                    INSERT INTO writer_notes
                    (logline, theme, inspiration, tone, comps, braindump, outline)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (logline, theme, inspiration, tone, comps, braindump, outline))
                return cursor.lastrowid

    def insert_character(
        self,
        name: str,
        role: str = "",
        description: str = "",
        arc: str = "",
        age: str = "",
        personality: str = "",
        flaw: str = "",
        backstory: str = "",
        relationships: str = ""
    ) -> int:
        """Insert a character into the characters table."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO characters
                (name, role, description, arc, age, personality, flaw, backstory, relationships)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (name, role, description, arc, age, personality, flaw, backstory, relationships))
            return cursor.lastrowid

    def get_characters(self) -> List[dict]:
        """Get all characters for the project."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM characters ORDER BY created_at")
            return [dict(row) for row in cursor.fetchall()]

    def insert_scene(
        self,
        scene_number: int,
        title: str = "",
        description: str = "",
        characters: str = "",
        tone: str = ""
    ) -> int:
        """Insert or update a scene in the scenes table."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO scenes (scene_number, title, description, characters, tone)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(scene_number) DO UPDATE SET
                    title = excluded.title,
                    description = excluded.description,
                    characters = excluded.characters,
                    tone = excluded.tone
            """, (scene_number, title, description, characters, tone))
            return cursor.lastrowid

    def insert_chat_message(
        self,
        role: str,
        content: str,
        focused_scene: Optional[int] = None,
        experts: Optional[str] = None
    ) -> int:
        """
        Insert a chat message into conversation history.

        Args:
            role: Either 'user' or 'assistant'
            content: The message content (user query or assistant response)
            focused_scene: Optional scene number that was in focus
            experts: Optional JSON string of expert responses (for assistant messages)

        Returns:
            Message ID
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO chat_messages (role, content, focused_scene, experts)
                VALUES (?, ?, ?, ?)
            """, (role, content, focused_scene, experts))
            return cursor.lastrowid

    def get_chat_history(self, limit: Optional[int] = None) -> List[dict]:
        """
        Retrieve chat message history.

        Args:
            limit: Optional limit on number of messages to retrieve (most recent first)

        Returns:
            List of message dicts with id, role, content, focused_scene, experts, created_at
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            if limit:
                cursor.execute("""
                    SELECT id, role, content, focused_scene, experts, created_at
                    FROM chat_messages
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (limit,))
            else:
                cursor.execute("""
                    SELECT id, role, content, focused_scene, experts, created_at
                    FROM chat_messages
                    ORDER BY created_at ASC
                """)

            messages = []
            for row in cursor.fetchall():
                messages.append(dict(row))

            return messages

    def clear_chat_history(self) -> int:
        """
        Clear all chat history for the project.

        Returns:
            Number of messages deleted
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM chat_messages")
            return cursor.rowcount

    # =========================================================================
    # IDEATE SESSION METHODS
    # =========================================================================

    def create_ideate_session(self, name: str) -> int:
        """
        Create a new ideate session.

        Args:
            name: Project/session name

        Returns:
            Session ID
        """
        import json
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO ideate_sessions
                (name, characters, outline, beats, notebook)
                VALUES (?, ?, ?, ?, ?)
            """, (name, '[]', '[]', '[]', '[]'))
            return cursor.lastrowid

    def get_ideate_sessions(self) -> List[dict]:
        """
        Get all ideate sessions.

        Returns:
            List of session dicts with id, name, stage, title, logline, created_at, updated_at
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, name, stage, title, logline, created_at, updated_at
                FROM ideate_sessions
                ORDER BY updated_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]

    def get_ideate_session(self, session_id: int) -> Optional[dict]:
        """
        Get a specific ideate session with all fields.

        Args:
            session_id: Session ID

        Returns:
            Session dict or None
        """
        import json
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM ideate_sessions WHERE id = ?
            """, (session_id,))
            row = cursor.fetchone()
            if not row:
                return None

            session = dict(row)
            # Parse JSON fields
            for field in ['characters', 'outline', 'beats', 'notebook']:
                if session.get(field):
                    try:
                        session[field] = json.loads(session[field])
                    except json.JSONDecodeError:
                        session[field] = []
                else:
                    session[field] = []
            return session

    def update_ideate_session(
        self,
        session_id: int,
        stage: str = None,
        title: str = None,
        logline: str = None,
        title_locked: bool = None,
        logline_locked: bool = None,
        characters: list = None,
        outline: list = None,
        beats: list = None,
        notebook: list = None,
        theme: str = None,
        tone: str = None,
        comps: str = None
    ) -> None:
        """
        Update an ideate session. Only updates fields that are provided.

        Args:
            session_id: Session ID
            Other args: Fields to update
        """
        import json

        updates = []
        params = []

        if stage is not None:
            updates.append("stage = ?")
            params.append(stage)
        if title is not None:
            updates.append("title = ?")
            params.append(title)
        if logline is not None:
            updates.append("logline = ?")
            params.append(logline)
        if title_locked is not None:
            updates.append("title_locked = ?")
            params.append(1 if title_locked else 0)
        if logline_locked is not None:
            updates.append("logline_locked = ?")
            params.append(1 if logline_locked else 0)
        if characters is not None:
            updates.append("characters = ?")
            params.append(json.dumps(characters))
        if outline is not None:
            updates.append("outline = ?")
            params.append(json.dumps(outline))
        if beats is not None:
            updates.append("beats = ?")
            params.append(json.dumps(beats))
        if notebook is not None:
            updates.append("notebook = ?")
            params.append(json.dumps(notebook))
        if theme is not None:
            updates.append("theme = ?")
            params.append(theme)
        if tone is not None:
            updates.append("tone = ?")
            params.append(tone)
        if comps is not None:
            updates.append("comps = ?")
            params.append(comps)

        if not updates:
            return

        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(session_id)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                UPDATE ideate_sessions
                SET {', '.join(updates)}
                WHERE id = ?
            """, params)

    def delete_ideate_session(self, session_id: int) -> None:
        """
        Delete an ideate session and its messages.

        Args:
            session_id: Session ID
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM ideate_messages WHERE session_id = ?", (session_id,))
            cursor.execute("DELETE FROM ideate_sessions WHERE id = ?", (session_id,))

    def add_ideate_message(self, session_id: int, role: str, content: str) -> int:
        """
        Add a message to an ideate session.

        Args:
            session_id: Session ID
            role: 'user' or 'assistant'
            content: Message content

        Returns:
            Message ID
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO ideate_messages (session_id, role, content)
                VALUES (?, ?, ?)
            """, (session_id, role, content))
            return cursor.lastrowid

    def get_ideate_messages(self, session_id: int) -> List[dict]:
        """
        Get all messages for an ideate session.

        Args:
            session_id: Session ID

        Returns:
            List of message dicts
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, role, content, created_at
                FROM ideate_messages
                WHERE session_id = ?
                ORDER BY created_at ASC
            """, (session_id,))
            return [dict(row) for row in cursor.fetchall()]
