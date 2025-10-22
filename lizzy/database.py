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
from typing import Optional
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
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indices for performance
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
        braindump: str = ""
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
                        tone = ?, comps = ?, braindump = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (logline, theme, inspiration, tone, comps, braindump, existing[0]))
                return existing[0]
            else:
                # Insert new
                cursor.execute("""
                    INSERT INTO writer_notes
                    (logline, theme, inspiration, tone, comps, braindump)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (logline, theme, inspiration, tone, comps, braindump))
                return cursor.lastrowid
