"""
Custom Exception Types for LIZZY

Provides specific exception classes for better error handling and debugging.
"""


class LizzyError(Exception):
    """Base exception for all LIZZY-specific errors."""

    def __init__(self, message: str, error_code: str = "LIZZY_ERROR"):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class ProjectNotFoundError(LizzyError):
    """Raised when a project cannot be found."""

    def __init__(self, project_name: str):
        message = f"Project '{project_name}' not found"
        super().__init__(message, error_code="PROJECT_NOT_FOUND")
        self.project_name = project_name


class ProjectAlreadyExistsError(LizzyError):
    """Raised when attempting to create a project that already exists."""

    def __init__(self, project_name: str):
        message = f"Project '{project_name}' already exists"
        super().__init__(message, error_code="PROJECT_EXISTS")
        self.project_name = project_name


class SceneNotFoundError(LizzyError):
    """Raised when a scene cannot be found."""

    def __init__(self, scene_number: int, project_name: str = None):
        if project_name:
            message = f"Scene {scene_number} not found in project '{project_name}'"
        else:
            message = f"Scene {scene_number} not found"
        super().__init__(message, error_code="SCENE_NOT_FOUND")
        self.scene_number = scene_number
        self.project_name = project_name


class DraftNotFoundError(LizzyError):
    """Raised when a draft cannot be found."""

    def __init__(self, scene_number: int, version: int = None):
        if version:
            message = f"Draft version {version} not found for scene {scene_number}"
        else:
            message = f"No drafts found for scene {scene_number}"
        super().__init__(message, error_code="DRAFT_NOT_FOUND")
        self.scene_number = scene_number
        self.version = version


class DatabaseError(LizzyError):
    """Raised when a database operation fails."""

    def __init__(self, message: str, original_error: Exception = None):
        super().__init__(message, error_code="DATABASE_ERROR")
        self.original_error = original_error


class BrainstormError(LizzyError):
    """Raised when brainstorm operations fail."""

    def __init__(self, message: str, bucket: str = None):
        super().__init__(message, error_code="BRAINSTORM_ERROR")
        self.bucket = bucket


class RAGQueryError(LizzyError):
    """Raised when RAG knowledge graph queries fail."""

    def __init__(self, message: str, bucket: str = None):
        super().__init__(message, error_code="RAG_QUERY_ERROR")
        self.bucket = bucket


class ExportError(LizzyError):
    """Raised when export operations fail."""

    def __init__(self, message: str, output_format: str = None):
        super().__init__(message, error_code="EXPORT_ERROR")
        self.output_format = output_format


class ValidationError(LizzyError):
    """Raised when data validation fails."""

    def __init__(self, message: str, field: str = None):
        super().__init__(message, error_code="VALIDATION_ERROR")
        self.field = field


class ConfigurationError(LizzyError):
    """Raised when configuration is invalid or missing."""

    def __init__(self, message: str, config_key: str = None):
        super().__init__(message, error_code="CONFIGURATION_ERROR")
        self.config_key = config_key


class AIGenerationError(LizzyError):
    """Raised when AI generation fails."""

    def __init__(self, message: str, model: str = None):
        super().__init__(message, error_code="AI_GENERATION_ERROR")
        self.model = model


# Error response helper
def create_error_response(error: Exception, include_traceback: bool = False) -> dict:
    """
    Create a consistent error response dict from an exception.

    Args:
        error: The exception to convert
        include_traceback: Whether to include traceback info (for debugging)

    Returns:
        Dict with error details
    """
    if isinstance(error, LizzyError):
        response = {
            "success": False,
            "error": error.message,
            "error_code": error.error_code
        }
    else:
        response = {
            "success": False,
            "error": str(error),
            "error_code": "UNKNOWN_ERROR"
        }

    if include_traceback:
        import traceback
        response["traceback"] = traceback.format_exc()

    return response
