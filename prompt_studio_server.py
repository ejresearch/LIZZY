#!/usr/bin/env python3
"""
Prompt Studio Chat Server

Simple FastAPI server for the chat-based prompt composer.
"""

import os
import sys
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn

# Add lizzy to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lizzy.prompt_studio import AIBlockComposer, BlockRegistry
from lizzy.prompt_studio.executor import execute_prompt, ExecutionResult as ExecResult

app = FastAPI(title="Prompt Studio Chat", version="1.0")

# Enable CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session storage (simple for now)
sessions = {}


class ChatRequest(BaseModel):
    """Chat message from user"""
    project_name: str
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Response with parsed blocks and prompt"""
    session_id: str
    parsed_entities: dict
    blocks_used: list[str]
    prompt: str
    total_chars: int
    execution_time_ms: float


class BlockInfo(BaseModel):
    """Information about available blocks"""
    block_type: str
    class_name: str
    description: str


@app.get("/")
async def root():
    """Serve the chat UI"""
    html_path = os.path.join(os.path.dirname(__file__), "prompt_studio_ui.html")

    if os.path.exists(html_path):
        with open(html_path, 'r') as f:
            return HTMLResponse(content=f.read())
    else:
        return {
            "message": "Prompt Studio Chat Server",
            "endpoints": {
                "/chat": "POST - Send chat message",
                "/blocks": "GET - List available blocks",
                "/projects": "GET - List available projects",
            }
        }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Process a chat message and return blocks + prompt.
    """
    try:
        # Create composer for this project
        composer = AIBlockComposer(request.project_name)

        # Compose prompt from natural language
        result = await composer.compose(request.message)

        # Generate session ID
        import uuid
        session_id = request.session_id or str(uuid.uuid4())

        # Store in session
        sessions[session_id] = {
            'project_name': request.project_name,
            'last_message': request.message,
            'last_result': result,
        }

        # Return response
        return ChatResponse(
            session_id=session_id,
            parsed_entities=result.parsed_entities if hasattr(result, 'parsed_entities') else {},
            blocks_used=result.blocks_used if hasattr(result, 'blocks_used') else [],
            prompt=result.prompt,
            total_chars=result.total_chars,
            execution_time_ms=result.total_execution_time_ms,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/blocks", response_model=list[BlockInfo])
async def list_blocks():
    """
    List all available block types.
    """
    try:
        info = BlockRegistry.get_block_info()

        blocks = []
        for block_type, details in info.items():
            blocks.append(BlockInfo(
                block_type=block_type,
                class_name=details['class_name'],
                description=details['description']
            ))

        return blocks

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/projects")
async def list_projects():
    """
    List available projects.
    """
    try:
        projects_dir = "projects"

        if not os.path.exists(projects_dir):
            return {"projects": []}

        projects = []
        for item in os.listdir(projects_dir):
            project_path = os.path.join(projects_dir, item)
            if os.path.isdir(project_path):
                # Check if database exists
                db_path = os.path.join(project_path, f"{item}.db")
                if os.path.exists(db_path):
                    projects.append({
                        "name": item,
                        "display_name": item.replace("_", " ").title(),
                        "path": project_path
                    })

        return {"projects": projects}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ExecuteRequest(BaseModel):
    """Request to execute a prompt"""
    prompt: str
    execution_type: str = "general"  # general, ideas, analysis, feedback
    model: str = "gpt-4o"
    focus_area: Optional[str] = None


class ExecuteResponse(BaseModel):
    """Response from execution"""
    success: bool
    response: str
    model: str
    tokens_used: Optional[int] = None
    cost_estimate: Optional[float] = None
    error: Optional[str] = None


@app.post("/api/execute", response_model=ExecuteResponse)
async def execute(request: ExecuteRequest):
    """
    Execute a prompt with an LLM.
    """
    try:
        result = await execute_prompt(
            prompt=request.prompt,
            execution_type=request.execution_type,
            model=request.model,
            focus_area=request.focus_area
        )

        return ExecuteResponse(
            success=result.success,
            response=result.response,
            model=result.model,
            tokens_used=result.tokens_used,
            cost_estimate=result.cost_estimate,
            error=result.error
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Prompt Studio Chat"}


def main():
    """Start the server"""
    print("\n" + "="*60)
    print("🚀 Prompt Studio Chat Server")
    print("="*60)
    print("\nStarting server at: http://localhost:8001")
    print("\nEndpoints:")
    print("  • http://localhost:8001          - Chat UI")
    print("  • http://localhost:8001/api/chat - Chat API")
    print("  • http://localhost:8001/docs     - API docs")
    print("\nPress Ctrl+C to stop")
    print("="*60 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")


if __name__ == "__main__":
    main()
