"""
Centralized Configuration for LIZZY

Manages all path configuration, environment variables, and project settings.
This eliminates hardcoded paths and provides a single source of truth.
"""

import os
from pathlib import Path
from typing import Optional


class LizzyConfig:
    """Central configuration for LIZZY paths and settings."""

    def __init__(self, root_dir: Optional[Path] = None):
        """
        Initialize configuration.

        Args:
            root_dir: Root directory of LIZZY project.
                     If None, auto-detects based on this file's location.
        """
        if root_dir is None:
            # Auto-detect: lizzy/config.py -> parent is root
            self._root_dir = Path(__file__).parent.parent.resolve()
        else:
            self._root_dir = Path(root_dir).resolve()

    @property
    def root_dir(self) -> Path:
        """Root directory of LIZZY project."""
        return self._root_dir

    @property
    def projects_dir(self) -> Path:
        """Directory containing all user projects."""
        # Allow override via environment variable
        custom_path = os.getenv('LIZZY_PROJECTS_DIR')
        if custom_path:
            return Path(custom_path).resolve()
        return self._root_dir / "projects"

    @property
    def rag_buckets_dir(self) -> Path:
        """Directory containing RAG knowledge graph buckets."""
        custom_path = os.getenv('LIZZY_RAG_BUCKETS_DIR')
        if custom_path:
            return Path(custom_path).resolve()
        return self._root_dir / "rag_buckets"

    @property
    def frontend_dir(self) -> Path:
        """Directory containing frontend HTML/CSS/JS files."""
        return self._root_dir / "frontend"

    @property
    def scripts_dir(self) -> Path:
        """Directory containing utility scripts."""
        return self._root_dir / "scripts"

    @property
    def docs_dir(self) -> Path:
        """Directory containing documentation."""
        return self._root_dir / "docs"

    @property
    def examples_dir(self) -> Path:
        """Directory containing examples."""
        return self._root_dir / "examples"

    @property
    def lib_dir(self) -> Path:
        """Directory containing third-party libraries."""
        return self._root_dir / "lib"

    def get_project_dir(self, project_name: str) -> Path:
        """
        Get the directory path for a specific project.

        Args:
            project_name: Name of the project

        Returns:
            Path to project directory
        """
        return self.projects_dir / project_name

    def get_project_db_path(self, project_name: str) -> Path:
        """
        Get the database path for a specific project.

        Args:
            project_name: Name of the project

        Returns:
            Path to project's SQLite database
        """
        return self.get_project_dir(project_name) / f"{project_name}.db"

    def get_project_exports_dir(self, project_name: str) -> Path:
        """
        Get the exports directory for a specific project.

        Args:
            project_name: Name of the project

        Returns:
            Path to project's exports directory
        """
        return self.get_project_dir(project_name) / "exports"

    def get_project_screenplays_dir(self, project_name: str) -> Path:
        """
        Get the screenplays directory for a specific project.

        Args:
            project_name: Name of the project

        Returns:
            Path to project's screenplays directory
        """
        return self.get_project_dir(project_name) / "screenplays"

    def get_bucket_path(self, bucket_name: str) -> Path:
        """
        Get the path for a specific RAG bucket.

        Args:
            bucket_name: Name of the bucket

        Returns:
            Path to bucket directory
        """
        return self.rag_buckets_dir / bucket_name

    def ensure_directories(self):
        """Create essential directories if they don't exist."""
        self.projects_dir.mkdir(exist_ok=True, parents=True)
        self.rag_buckets_dir.mkdir(exist_ok=True, parents=True)

    def __repr__(self) -> str:
        return (
            f"LizzyConfig(\n"
            f"  root_dir={self.root_dir},\n"
            f"  projects_dir={self.projects_dir},\n"
            f"  rag_buckets_dir={self.rag_buckets_dir}\n"
            f")"
        )


# Global config instance
# Import this in other modules: from backend.config import config
config = LizzyConfig()


# Convenience function for backward compatibility
def get_projects_dir() -> Path:
    """Get the projects directory path."""
    return config.projects_dir


def get_rag_buckets_dir() -> Path:
    """Get the RAG buckets directory path."""
    return config.rag_buckets_dir
