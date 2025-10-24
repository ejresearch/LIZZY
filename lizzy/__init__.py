"""
Lizzy - AI-Assisted Romantic Comedy Writing Framework
YT Research
"""

__version__ = "3.0.0"

# Export central configuration
from .config import config, LizzyConfig

# Export logging utilities
from .logging_config import get_logger, LizzyLogger

# Export exceptions
from .exceptions import (
    LizzyError,
    ProjectNotFoundError,
    SceneNotFoundError,
    DraftNotFoundError,
    DatabaseError,
    BrainstormError,
    RAGQueryError,
    ExportError,
    ValidationError,
    ConfigurationError,
    AIGenerationError,
    create_error_response
)

__all__ = [
    'config', 'LizzyConfig',
    'get_logger', 'LizzyLogger',
    'LizzyError', 'ProjectNotFoundError', 'SceneNotFoundError',
    'DraftNotFoundError', 'DatabaseError', 'BrainstormError',
    'RAGQueryError', 'ExportError', 'ValidationError',
    'ConfigurationError', 'AIGenerationError', 'create_error_response',
    '__version__'
]
