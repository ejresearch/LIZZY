"""
Lizzy 2.0 Landing Page Server

Clean, modular FastAPI server with separation of concerns.
Uses routers for endpoints and services for business logic.
"""

from fastapi import FastAPI
import uvicorn

from servers.logging_config import get_logger

# Import routers
from servers.routers import (
    pages_router,
    projects_router,
    brainstorm_router,
    generation_router,
    write_router
)

logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Lizzy 2.0 - AI Screenplay Writer",
    description="Backend API for Lizzy, an AI-assisted romantic comedy screenplay writing framework",
    version="2.0.0"
)

# Include routers
app.include_router(pages_router)
app.include_router(projects_router)
app.include_router(brainstorm_router)
app.include_router(generation_router)
app.include_router(write_router)


if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("Lizzy 2.0 Landing Page Server")
    logger.info("=" * 50)
    logger.info("Starting server at: http://localhost:8002")
    logger.info("API Documentation:")
    logger.info("  - Interactive API docs: http://localhost:8002/docs")
    logger.info("  - ReDoc documentation: http://localhost:8002/redoc")
    logger.info("Key Endpoints:")
    logger.info("  - GET  /                      Landing page")
    logger.info("  - GET  /api/projects          List projects")
    logger.info("  - GET  /api/status/{project}  Project status")
    logger.info("  - POST /api/launch            Launch module")
    logger.info("  - GET  /api/health            Health check")
    logger.info("=" * 50)

    uvicorn.run(app, host="0.0.0.0", port=8002)
