"""API routers for Lizzy 2.0 backend."""

from .pages import router as pages_router
from .projects import router as projects_router
from .brainstorm import router as brainstorm_router
from .generation import router as generation_router
from .write import router as write_router

__all__ = [
    "pages_router",
    "projects_router",
    "brainstorm_router",
    "generation_router",
    "write_router"
]
