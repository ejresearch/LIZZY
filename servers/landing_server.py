"""
Lizzy 2.0 Landing Page Server

Clean, modular FastAPI server with separation of concerns.
Uses routers for endpoints and services for business logic.
"""

from fastapi import FastAPI
import uvicorn

# Import routers
from servers.routers import (
    pages_router,
    projects_router,
    brainstorm_router,
    generation_router,
    write_router
)

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
    print("\n" + "=" * 50)
    print("Lizzy 2.0 Landing Page Server")
    print("=" * 50)
    print("\nStarting server at: http://localhost:8002")
    print("\nAPI Documentation:")
    print("  - Interactive API docs: http://localhost:8002/docs")
    print("  - ReDoc documentation: http://localhost:8002/redoc")
    print("\nKey Endpoints:")
    print("  - GET  /                      Landing page")
    print("  - GET  /api/projects          List projects")
    print("  - GET  /api/status/{project}  Project status")
    print("  - POST /api/launch            Launch module")
    print("  - GET  /api/health            Health check")
    print("\n" + "=" * 50 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=8002)
