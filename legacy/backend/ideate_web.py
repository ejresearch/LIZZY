"""
Web interface for IDEATE - Conversational Pre-Planning

Run with: python -m backend.ideate_web
Then open: http://localhost:8888
"""

import os
import json
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from .ideate import IdeateSession
from .database import Database

# Database path for session persistence
DB_PATH = Path(__file__).parent.parent / "ideate_sessions.db"

# Global session and current session ID
session = None
current_session_id = None
db = None

# Brainstorm progress tracking
brainstorm_progress = {
    "active": False,
    "project_id": None,
    "total_scenes": 0,
    "completed_scenes": 0,
    "current_scene": None,
    "current_scene_title": None,
    "status": "idle",  # idle, running, awaiting_vote, checkpoint, completed, error
    "error": None,
    "started_at": None,

    # Expert voting
    "current_expert_perspectives": None,  # {books: str, plays: str, scripts: str}
    "awaiting_vote_for_scene": None,      # Scene number waiting for vote

    # Checkpoints
    "checkpoint_act": None,               # 1, 2, or None
    "completed_scenes_data": [],          # List of {scene_num, title, blueprint_preview}

    # User votes
    "scene_votes": {}                     # {scene_num: {books: 1-3, plays: 1-3, scripts: 1-3}}
}

# Async events for interactive brainstorm signaling
vote_received_event = None  # Will be initialized as asyncio.Event()
checkpoint_continue_event = None  # Will be initialized as asyncio.Event()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global db, vote_received_event, checkpoint_continue_event
    db = Database(DB_PATH)
    db.initialize_schema()
    print(f"Database initialized at {DB_PATH}")

    # Initialize async events for interactive brainstorm
    vote_received_event = asyncio.Event()
    checkpoint_continue_event = asyncio.Event()

    yield
    # Shutdown (nothing to clean up)

app = FastAPI(lifespan=lifespan)

# Serve static files
STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# =============================================================================
# SESSION MANAGEMENT ENDPOINTS
# =============================================================================

@app.get("/", response_class=HTMLResponse)
async def get_landing():
    """Landing page - project selector."""
    return LANDING_TEMPLATE

@app.get("/chat/{session_id}", response_class=HTMLResponse)
async def get_chat(session_id: int):
    """Chat interface for a specific session."""
    global session, current_session_id

    # Load session from database
    session_data = db.get_ideate_session(session_id)
    if not session_data:
        return HTMLResponse("<h1>Session not found</h1>", status_code=404)

    # Create IdeateSession and restore state
    session = IdeateSession(project_name=session_data['name'], debug=False)
    current_session_id = session_id

    # Restore fields
    session.fields['title'] = session_data.get('title')
    session.fields['logline'] = session_data.get('logline')
    session.fields['characters'] = session_data.get('characters', [])
    session.fields['scenes'] = session_data.get('beats', [])  # scenes stored in beats column
    session.fields['notebook'] = session_data.get('notebook', [])
    session.fields['theme'] = session_data.get('theme')
    session.fields['tone'] = session_data.get('tone')
    session.fields['comps'] = session_data.get('comps')

    # Restore locked status
    session.locked['title'] = bool(session_data.get('title_locked'))
    session.locked['logline'] = bool(session_data.get('logline_locked'))

    # Restore stage
    session.stage = session_data.get('stage', 'explore')

    # Restore conversation history
    messages = db.get_ideate_messages(session_id)
    for msg in messages:
        session.messages.append({
            "role": msg['role'],
            "content": msg['content']
        })

    print(f"Loaded session {session_id}: {session_data['name']} ({len(messages)} messages)")

    return HTML_TEMPLATE.replace('{{SESSION_ID}}', str(session_id)).replace('{{SESSION_NAME}}', session_data['name'])

@app.get("/api/sessions")
async def list_sessions():
    """List all sessions."""
    sessions = db.get_ideate_sessions()
    return {"sessions": sessions}

@app.post("/api/sessions")
async def create_session(request: Request):
    """Create a new session."""
    data = await request.json()
    name = data.get("name", "Untitled Project")

    session_id = db.create_ideate_session(name)
    return {"id": session_id, "name": name}

@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: int):
    """Delete a session."""
    db.delete_ideate_session(session_id)
    return {"success": True}

@app.get("/api/sessions/{session_id}/messages")
async def get_messages(session_id: int):
    """Get all messages for a session."""
    messages = db.get_ideate_messages(session_id)
    return {"messages": messages}

# =============================================================================
# CHAT ENDPOINTS
# =============================================================================

@app.post("/chat")
async def chat(request: Request):
    """Process a message and return streamed response."""
    global session, current_session_id

    data = await request.json()
    message = data.get("message", "")

    if not message:
        return {"error": "No message provided"}

    if not session or not current_session_id:
        return {"error": "No active session"}

    # Save user message to database
    db.add_ideate_message(current_session_id, "user", message)

    async def generate():
        try:
            print(f"Processing message: {message[:50]}...")
            full_response = ""
            async for chunk in session.process_message_stream(message):
                full_response += chunk
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"

            print(f"Response complete: {len(full_response)} chars")

            # Strip directives from response before saving
            import re
            clean_response = re.sub(r'\[DIRECTIVE:[^\]]+\]\s*', '', full_response).strip()

            # Save assistant response to database
            db.add_ideate_message(current_session_id, "assistant", clean_response)

            # Save updated session state to database
            save_session_state()

            # Send final state
            state = session.get_state()
            yield f"data: {json.dumps({'type': 'state', 'state': state})}\n\n"
        except Exception as e:
            print(f"Error in chat: {e}")
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

def save_session_state():
    """Save current session state to database."""
    if not session or not current_session_id:
        return

    db.update_ideate_session(
        current_session_id,
        stage=session.stage,
        title=session.fields.get('title'),
        logline=session.fields.get('logline'),
        title_locked=session.locked.get('title', False),
        logline_locked=session.locked.get('logline', False),
        characters=session.fields.get('characters', []),
        beats=session.fields.get('scenes', []),  # scenes stored in beats column
        notebook=session.fields.get('notebook', []),
        theme=session.fields.get('theme'),
        tone=session.fields.get('tone'),
        comps=session.fields.get('comps')
    )

@app.get("/state")
async def get_state():
    """Get current session state."""
    if session:
        return session.get_state()
    return {"error": "No session"}

@app.post("/save")
async def save_to_database(request: Request):
    """Export session to production database."""
    from pathlib import Path

    if not session:
        return {"error": "No session to save"}

    data = await request.json()
    db_path = data.get("db_path")
    if not db_path:
        return {"error": "db_path required"}

    try:
        project_id = session.save_to_database(Path(db_path))
        return {
            "success": True,
            "project_id": project_id,
            "message": "Project exported successfully"
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/export")
async def export_project(format: str = "markdown"):
    """Export project to markdown or other formats."""
    if not session:
        return {"error": "No active session"}

    if format == "markdown" or format == "md":
        content = session.export_to_markdown()
        return {
            "success": True,
            "format": "markdown",
            "content": content,
            "filename": f"{session.fields.get('title', 'project')}.md"
        }
    else:
        return {"error": f"Unsupported format: {format}"}


@app.get("/api/undo")
async def undo_action():
    """Undo the last action."""
    if not session:
        return {"error": "No active session"}

    result = session._undo_last_action()
    if result:
        # Save state after undo
        save_session_state()
        return {
            "success": True,
            "undone": {
                "action": result.get("action"),
                "type": result.get("type")
            }
        }
    return {"success": False, "error": "Nothing to undo"}


@app.get("/api/history")
async def get_history():
    """Get undo history."""
    if not session:
        return {"error": "No active session"}

    history = getattr(session, '_undo_history', [])
    return {
        "success": True,
        "count": len(history),
        "history": history[-10:]  # Last 10 items
    }


@app.post("/api/field")
async def update_field(request: Request):
    """
    Update a field directly via inline editing.

    Supports: title, logline, scene_title, character_description, beat
    """
    global session, current_session_id

    if not session:
        return {"error": "No active session"}

    data = await request.json()
    field_type = data.get("type")
    value = data.get("value", "").strip()

    if not field_type:
        return {"error": "Field type required"}

    try:
        if field_type == "title":
            session.fields['title'] = value
            session.locked['title'] = True

        elif field_type == "logline":
            session.fields['logline'] = value
            session.locked['logline'] = True

        elif field_type == "scene_title":
            scene_num = data.get("scene_num")
            if not scene_num:
                return {"error": "scene_num required"}
            for scene in session.fields.get('scenes', []):
                if scene.get('number') == scene_num:
                    scene['title'] = value
                    break

        elif field_type == "character_name":
            old_name = data.get("old_name")
            if not old_name:
                return {"error": "old_name required"}
            for char in session.fields.get('characters', []):
                if char.get('name') == old_name:
                    char['name'] = value
                    break

        elif field_type == "character_description":
            char_name = data.get("name")
            if not char_name:
                return {"error": "name required"}
            for char in session.fields.get('characters', []):
                if char.get('name') == char_name:
                    char['description'] = value
                    break

        elif field_type == "beat":
            scene_num = data.get("scene_num")
            beat_idx = data.get("beat_idx")
            if scene_num is None or beat_idx is None:
                return {"error": "scene_num and beat_idx required"}
            for scene in session.fields.get('scenes', []):
                if scene.get('number') == scene_num:
                    beats = scene.get('beats', [])
                    if 0 <= beat_idx < len(beats):
                        beats[beat_idx] = value
                    break
        else:
            return {"error": f"Unknown field type: {field_type}"}

        # Save to database
        save_session_state()

        return {
            "success": True,
            "state": session.get_state()
        }

    except Exception as e:
        return {"error": str(e)}


# =============================================================================
# BRAINSTORM INTEGRATION
# =============================================================================

async def run_brainstorm_with_progress(db_path: Path, project_id: int):
    """
    Run automated brainstorm with progress tracking.
    Updates global brainstorm_progress as scenes complete.
    """
    global brainstorm_progress
    from datetime import datetime

    try:
        from .automated_brainstorm import AutomatedBrainstorm

        brainstorm = AutomatedBrainstorm(db_path)
        brainstorm.load_project_context()

        if not brainstorm.scenes:
            brainstorm_progress["status"] = "error"
            brainstorm_progress["error"] = "No scenes found in database"
            brainstorm_progress["active"] = False
            return

        brainstorm_progress.update({
            "active": True,
            "project_id": project_id,
            "total_scenes": len(brainstorm.scenes),
            "completed_scenes": 0,
            "status": "running",
            "started_at": datetime.now().isoformat(),
            "error": None
        })

        # Process each scene
        for scene in brainstorm.scenes:
            scene_num = scene['scene_number']
            scene_title = scene['title']

            brainstorm_progress["current_scene"] = scene_num
            brainstorm_progress["current_scene_title"] = scene_title

            # Process the scene
            result = await brainstorm.process_scene_for_web(scene)

            brainstorm_progress["completed_scenes"] = scene_num

        brainstorm_progress["status"] = "completed"
        brainstorm_progress["current_scene"] = None
        brainstorm_progress["current_scene_title"] = None
        brainstorm_progress["active"] = False

    except Exception as e:
        import traceback
        traceback.print_exc()
        brainstorm_progress["status"] = "error"
        brainstorm_progress["error"] = str(e)
        brainstorm_progress["active"] = False


# Global reference to brainstorm instance for interactive mode
_brainstorm_instance = None
_current_scene_index = 0
_current_perspectives = None


async def run_brainstorm_interactive(db_path: Path, project_id: int):
    """
    Run interactive brainstorm with expert voting and checkpoints.
    Pauses for user votes and at act checkpoints.
    """
    global brainstorm_progress, _brainstorm_instance, _current_scene_index, _current_perspectives
    from datetime import datetime

    try:
        from .automated_brainstorm import AutomatedBrainstorm

        _brainstorm_instance = AutomatedBrainstorm(db_path)
        _brainstorm_instance.load_project_context()

        if not _brainstorm_instance.scenes:
            brainstorm_progress["status"] = "error"
            brainstorm_progress["error"] = "No scenes found in database"
            brainstorm_progress["active"] = False
            return

        # Reset progress state
        brainstorm_progress.update({
            "active": True,
            "project_id": project_id,
            "total_scenes": len(_brainstorm_instance.scenes),
            "completed_scenes": 0,
            "status": "running",
            "started_at": datetime.now().isoformat(),
            "error": None,
            "current_expert_perspectives": None,
            "awaiting_vote_for_scene": None,
            "checkpoint_act": None,
            "completed_scenes_data": [],
            "scene_votes": {}
        })

        # Process each scene
        for idx, scene in enumerate(_brainstorm_instance.scenes):
            _current_scene_index = idx
            scene_num = scene['scene_number']
            scene_title = scene['title']

            brainstorm_progress["current_scene"] = scene_num
            brainstorm_progress["current_scene_title"] = scene_title
            brainstorm_progress["status"] = "running"

            # Query experts (no synthesis yet)
            perspectives = await _brainstorm_instance.query_experts_for_scene(scene)
            _current_perspectives = perspectives

            # Pause for user vote
            brainstorm_progress.update({
                "status": "awaiting_vote",
                "awaiting_vote_for_scene": scene_num,
                "current_expert_perspectives": perspectives
            })

            # Wait for vote
            await vote_received_event.wait()
            vote_received_event.clear()

            # Get votes and synthesize
            votes = brainstorm_progress["scene_votes"].get(scene_num, {"books": 2, "plays": 2, "scripts": 2})
            brainstorm_progress["status"] = "running"

            result = await _brainstorm_instance.synthesize_with_votes(scene, perspectives, votes)

            # Store completed scene data
            brainstorm_progress["completed_scenes"] = scene_num
            brainstorm_progress["completed_scenes_data"].append({
                "scene_num": scene_num,
                "title": scene_title,
                "blueprint_preview": result.get("synthesized", "")[:500] + "..." if result.get("synthesized") else ""
            })

            # Check for checkpoint (after Act 1: scene 6, after Act 2: scene 24)
            if scene_num == 6:
                brainstorm_progress["status"] = "checkpoint"
                brainstorm_progress["checkpoint_act"] = 1
                await checkpoint_continue_event.wait()
                checkpoint_continue_event.clear()
            elif scene_num == 24:
                brainstorm_progress["status"] = "checkpoint"
                brainstorm_progress["checkpoint_act"] = 2
                await checkpoint_continue_event.wait()
                checkpoint_continue_event.clear()

        # Complete
        brainstorm_progress["status"] = "completed"
        brainstorm_progress["current_scene"] = None
        brainstorm_progress["current_scene_title"] = None
        brainstorm_progress["active"] = False

    except Exception as e:
        import traceback
        traceback.print_exc()
        brainstorm_progress["status"] = "error"
        brainstorm_progress["error"] = str(e)
        brainstorm_progress["active"] = False


@app.post("/api/brainstorm/vote")
async def submit_vote(request: Request):
    """Submit votes for current scene's experts, trigger synthesis."""
    global brainstorm_progress

    data = await request.json()
    scene_num = data.get("scene_num")
    votes = data.get("votes", {})

    if not scene_num or not votes:
        return {"success": False, "error": "Missing scene_num or votes"}

    if brainstorm_progress["status"] != "awaiting_vote":
        return {"success": False, "error": "Not awaiting vote"}

    if brainstorm_progress["awaiting_vote_for_scene"] != scene_num:
        return {"success": False, "error": f"Expected vote for scene {brainstorm_progress['awaiting_vote_for_scene']}"}

    # Store votes and signal to continue
    brainstorm_progress["scene_votes"][scene_num] = votes
    vote_received_event.set()

    return {"success": True, "message": f"Votes recorded for scene {scene_num}"}


@app.post("/api/brainstorm/checkpoint/continue")
async def continue_from_checkpoint(request: Request):
    """Resume processing after checkpoint review."""
    global brainstorm_progress

    if brainstorm_progress["status"] != "checkpoint":
        return {"success": False, "error": "Not at checkpoint"}

    # Signal to continue
    checkpoint_continue_event.set()

    return {"success": True, "message": f"Continuing from Act {brainstorm_progress['checkpoint_act']} checkpoint"}


@app.get("/api/brainstorm/scene/{scene_num}")
async def get_scene_result(scene_num: int):
    """Get completed scene blueprint for checkpoint review."""
    # Find scene in completed_scenes_data
    for scene_data in brainstorm_progress.get("completed_scenes_data", []):
        if scene_data["scene_num"] == scene_num:
            return {"success": True, "scene": scene_data}

    return {"success": False, "error": f"Scene {scene_num} not found"}


@app.post("/api/handoff")
async def handoff_to_brainstorm(request: Request):
    """
    Hand off the ideation session to BRAINSTORM phase.

    Creates a complete project from the IDEATE session:
    1. Creates project directory (projects/{name}/)
    2. Initializes project database ({name}.db)
    3. Populates all tables from session data
    4. Marks session as exported
    """
    if not session:
        return {"error": "No active session"}

    if not current_session_id:
        return {"error": "No session ID - please save session first"}

    # Validate readiness
    state = session.get_state()
    validation = state.get("handoff_validation", {})

    if not validation.get("ready"):
        # Find what's missing
        missing = []
        for key, check in validation.get("checks", {}).items():
            if not check.get("passed"):
                missing.append(check.get("label", key))
        return {
            "success": False,
            "error": f"Not ready for handoff. Missing: {', '.join(missing)}"
        }

    try:
        # Save current session state to ideate_sessions.db first
        save_session_state()

        # Create project using unified project creator
        from .project_creator import create_project_from_ideate

        project_db_path = create_project_from_ideate(
            session_id=current_session_id,
            ideate_db_path=DB_PATH,
            overwrite=False
        )

        # Mark session as exported in ideate database
        db.update_ideate_session(
            current_session_id,
            stage="exported"
        )

        # Get project name for response
        project_name = project_db_path.parent.name

        return {
            "success": True,
            "project_name": project_name,
            "project_path": str(project_db_path),
            "message": f"Project '{project_name}' created successfully!",
            "next_step": "brainstorm",
            "next_command": f"python -m backend.automated_brainstorm"
        }
    except ValueError as e:
        # Project already exists or other validation error
        return {
            "success": False,
            "error": str(e)
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": f"Failed to create project: {str(e)}"
        }


@app.get("/api/brainstorm/progress")
async def brainstorm_progress_stream():
    """
    SSE endpoint for streaming brainstorm progress.
    Client connects and receives updates as scenes complete.
    """
    async def generate():
        while True:
            # Send current state
            yield f"data: {json.dumps(brainstorm_progress)}\n\n"

            # Check if done
            if brainstorm_progress["status"] in ["completed", "error"]:
                yield f"data: {json.dumps({'type': 'done', 'status': brainstorm_progress['status']})}\n\n"
                break

            # If not active and idle, send done
            if not brainstorm_progress["active"] and brainstorm_progress["status"] == "idle":
                yield f"data: {json.dumps({'type': 'idle'})}\n\n"
                break

            # Wait before next update (every 2 seconds)
            await asyncio.sleep(2)

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/api/brainstorm/status")
async def get_brainstorm_status():
    """Get current brainstorm status (non-streaming)."""
    return brainstorm_progress


# =============================================================================
# LANDING PAGE TEMPLATE
# =============================================================================

LANDING_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lizzy IDEATE - Projects</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #F8F6F1 0%, #F0EDE5 100%);
            min-height: 100vh;
            padding: 40px;
            -webkit-font-smoothing: antialiased;
        }

        .container {
            max-width: 800px;
            margin: 0 auto;
        }

        .header {
            text-align: center;
            margin-bottom: 40px;
        }

        .header h1 {
            font-size: 32px;
            color: #1a1a1a;
            margin-bottom: 8px;
        }

        .header p {
            color: #888;
            font-size: 16px;
        }

        .new-project {
            background: white;
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 24px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04), 0 8px 24px rgba(0, 0, 0, 0.06);
        }

        .new-project h2 {
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #888;
            margin-bottom: 16px;
        }

        .new-project-form {
            display: flex;
            gap: 12px;
        }

        .new-project-form input {
            flex: 1;
            padding: 14px 18px;
            border: 2px solid rgba(0, 0, 0, 0.06);
            border-radius: 12px;
            font-size: 15px;
            background: #FDFCFA;
        }

        .new-project-form input:focus {
            outline: none;
            border-color: #DC3545;
        }

        .new-project-form button {
            padding: 14px 28px;
            background: linear-gradient(135deg, #DC3545 0%, #c82333 100%);
            color: white;
            border: none;
            border-radius: 12px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            box-shadow: 0 4px 12px rgba(220, 53, 69, 0.25);
        }

        .new-project-form button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(220, 53, 69, 0.35);
        }

        .projects-list {
            background: white;
            border-radius: 16px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04), 0 8px 24px rgba(0, 0, 0, 0.06);
            overflow: hidden;
        }

        .projects-list h2 {
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #888;
            padding: 20px 24px;
            border-bottom: 1px solid rgba(0, 0, 0, 0.06);
        }

        .project-item {
            display: flex;
            align-items: center;
            padding: 20px 24px;
            border-bottom: 1px solid rgba(0, 0, 0, 0.04);
            cursor: pointer;
            transition: background 0.2s ease;
        }

        .project-item:hover {
            background: rgba(220, 53, 69, 0.03);
        }

        .project-item:last-child {
            border-bottom: none;
        }

        .project-info {
            flex: 1;
        }

        .project-name {
            font-size: 16px;
            font-weight: 600;
            color: #1a1a1a;
            margin-bottom: 4px;
        }

        .project-meta {
            font-size: 13px;
            color: #888;
        }

        .project-meta .stage {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-right: 8px;
        }

        .project-meta .stage.explore {
            background: rgba(220, 53, 69, 0.1);
            color: #DC3545;
        }

        .project-meta .stage.build_out {
            background: rgba(255, 193, 7, 0.1);
            color: #FFC107;
        }

        .project-meta .stage.complete {
            background: rgba(32, 201, 151, 0.1);
            color: #20C997;
        }

        .project-actions {
            display: flex;
            gap: 8px;
        }

        .project-actions button {
            padding: 8px 12px;
            border: none;
            border-radius: 8px;
            font-size: 13px;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .btn-open {
            background: linear-gradient(135deg, #DC3545 0%, #c82333 100%);
            color: white;
        }

        .btn-delete {
            background: rgba(0, 0, 0, 0.04);
            color: #888;
        }

        .btn-delete:hover {
            background: rgba(220, 53, 69, 0.1);
            color: #DC3545;
        }

        .empty-state {
            text-align: center;
            padding: 60px 24px;
            color: #888;
        }

        .empty-state p {
            margin-bottom: 8px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Lizzy IDEATE</h1>
            <p>Brainstorm your romantic comedy with Syd</p>
        </div>

        <div class="new-project">
            <h2>Start New Project</h2>
            <form class="new-project-form" onsubmit="createProject(event)">
                <input type="text" id="projectName" placeholder="Enter project name..." required>
                <button type="submit">Create</button>
            </form>
        </div>

        <div class="projects-list">
            <h2>Your Projects</h2>
            <div id="projectsList">
                <div class="empty-state">
                    <p>No projects yet</p>
                    <p>Create one above to get started!</p>
                </div>
            </div>
        </div>
    </div>

    <script>
        async function loadProjects() {
            const response = await fetch('/api/sessions');
            const data = await response.json();
            const container = document.getElementById('projectsList');

            if (data.sessions.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <p>No projects yet</p>
                        <p>Create one above to get started!</p>
                    </div>
                `;
                return;
            }

            container.innerHTML = data.sessions.map(s => `
                <div class="project-item" onclick="openProject(${s.id})">
                    <div class="project-info">
                        <div class="project-name">${s.title || s.name}</div>
                        <div class="project-meta">
                            <span class="stage ${s.stage}">${s.stage.replace('_', ' ')}</span>
                            ${s.logline ? s.logline.substring(0, 60) + '...' : 'No logline yet'}
                        </div>
                    </div>
                    <div class="project-actions">
                        <button class="btn-open">Open</button>
                        <button class="btn-delete" onclick="deleteProject(event, ${s.id})">Delete</button>
                    </div>
                </div>
            `).join('');
        }

        async function createProject(e) {
            e.preventDefault();
            const name = document.getElementById('projectName').value.trim();
            if (!name) return;

            const response = await fetch('/api/sessions', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name })
            });
            const data = await response.json();

            // Open the new project
            window.location.href = '/chat/' + data.id;
        }

        function openProject(id) {
            window.location.href = '/chat/' + id;
        }

        async function deleteProject(e, id) {
            e.stopPropagation();
            if (!confirm('Delete this project?')) return;

            await fetch('/api/sessions/' + id, { method: 'DELETE' });
            loadProjects();
        }

        // Load on page load
        loadProjects();
    </script>
</body>
</html>
"""

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{SESSION_NAME}} - Lizzy IDEATE</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #F8F6F1 0%, #F0EDE5 100%);
            height: 100vh;
            display: flex;
            font-size: 14px;
            color: #1a1a1a;
            -webkit-font-smoothing: antialiased;
        }

        .main-container {
            display: flex;
            width: 100%;
            height: 100vh;
            position: relative;
        }

        .chat-container {
            flex: 1;
            background: #FDFCFA;
            display: flex;
            flex-direction: column;
        }

        /* Glassmorphism Sidebar */
        .sidebar {
            width: 340px;
            background: rgba(255, 255, 255, 0.7);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            color: #1a1a1a;
            padding: 24px;
            overflow-y: auto;
            border-left: 1px solid rgba(0, 0, 0, 0.06);
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            display: flex;
            flex-direction: column;
            gap: 20px;
        }

        .sidebar.collapsed {
            width: 0;
            padding: 0;
            overflow: hidden;
        }

        .sidebar-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .sidebar h2 {
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 2px;
            color: #888;
            margin: 0;
            font-weight: 600;
        }

        .collapse-btn {
            background: rgba(0, 0, 0, 0.04);
            border: none;
            cursor: pointer;
            padding: 8px;
            color: #888;
            font-size: 12px;
            border-radius: 8px;
            transition: all 0.2s ease;
        }

        .collapse-btn:hover {
            background: rgba(220, 53, 69, 0.1);
            color: #DC3545;
        }

        .expand-btn {
            position: absolute;
            right: 0;
            top: 50%;
            transform: translateY(-50%);
            background: rgba(255, 255, 255, 0.9);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(0, 0, 0, 0.06);
            border-right: none;
            border-radius: 12px 0 0 12px;
            padding: 16px 10px;
            cursor: pointer;
            color: #888;
            font-size: 12px;
            display: none;
            transition: all 0.2s ease;
        }

        .expand-btn:hover {
            color: #DC3545;
            background: white;
        }

        .sidebar.collapsed + .expand-btn {
            display: block;
        }

        /* Phase Indicator */
        .phase-indicator {
            display: flex;
            gap: 10px;
            padding: 6px;
            background: rgba(0, 0, 0, 0.03);
            border-radius: 14px;
        }

        .phase {
            flex: 1;
            text-align: center;
            padding: 10px 8px;
            border-radius: 10px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: #999;
            background: transparent;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }

        .phase.active {
            background: linear-gradient(135deg, #DC3545 0%, #c82333 100%);
            color: white;
            box-shadow: 0 4px 12px rgba(220, 53, 69, 0.3);
        }

        .phase.complete {
            background: linear-gradient(135deg, #20C997 0%, #1aa37a 100%);
            color: white;
            box-shadow: 0 4px 12px rgba(32, 201, 151, 0.3);
        }

        /* Foundation Content */
        .foundation-content {
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 24px;
        }

        .field-block {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .field-label {
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #999;
        }

        .field-count {
            font-weight: 500;
            color: #bbb;
        }

        .field-block .field-value {
            font-size: 15px;
            color: #333;
            line-height: 1.5;
        }

        .field-block .field-value.pending {
            color: #bbb;
            font-style: italic;
        }

        .field-block .field-value.locked {
            color: #1a1a1a;
            font-weight: 500;
            font-style: normal;
        }

        #titleValue.locked {
            font-size: 20px;
            font-weight: 600;
        }

        .empty-hint {
            font-size: 13px;
            color: #ccc;
            font-style: italic;
        }

        .notebook-list {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .notebook-item {
            font-size: 13px;
            color: #555;
            padding: 10px 12px;
            background: rgba(0, 0, 0, 0.02);
            border-radius: 8px;
            border-left: 3px solid #DC3545;
        }

        /* Legacy - keeping for JS compatibility */
        .progress-item {
            display: none;
        }

        .progress-tracker {
            display: none;
        }

        .status-badge {
            display: none;
        }

        .progress-item.hidden {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 10px 0;
            font-size: 13px;
            color: #888;
            transition: all 0.2s ease;
        }

        .progress-item:not(:last-child) {
            border-bottom: 1px solid rgba(0, 0, 0, 0.04);
        }

        .progress-item .icon {
            width: 22px;
            height: 22px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 11px;
            flex-shrink: 0;
            transition: all 0.3s ease;
        }

        .progress-item.pending .icon {
            border: 2px solid #e0e0e0;
            color: transparent;
        }

        .progress-item.complete .icon {
            background: linear-gradient(135deg, #20C997 0%, #1aa37a 100%);
            color: white;
            border: none;
            box-shadow: 0 2px 8px rgba(32, 201, 151, 0.3);
        }

        .progress-item.complete {
            color: #1a1a1a;
        }

        .progress-item .count {
            margin-left: auto;
            font-size: 12px;
            color: #aaa;
            font-weight: 500;
        }

        .sidebar h3 {
            font-size: 11px;
            color: #888;
            margin: 0;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .field-value {
            background: white;
            padding: 14px 16px;
            border-radius: 14px;
            font-size: 13px;
            line-height: 1.6;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04), 0 8px 24px rgba(0, 0, 0, 0.03);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }

        .field-value.empty {
            color: #bbb;
            font-style: normal;
            background: rgba(255, 255, 255, 0.6);
        }

        .field-value.just-updated {
            animation: pulse 0.6s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: 0 0 0 3px rgba(32, 201, 151, 0.2), 0 2px 8px rgba(0, 0, 0, 0.04);
        }

        @keyframes pulse {
            0%, 100% { background: white; }
            50% { background: #e8f8f3; }
        }

        /* Character Cards */
        .character-cards {
            display: flex;
            flex-direction: column;
            gap: 10px;
        }

        .character-card {
            background: white;
            border-radius: 14px;
            padding: 14px 16px;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04), 0 8px 24px rgba(0, 0, 0, 0.03);
        }

        .character-card:hover {
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08), 0 12px 32px rgba(0, 0, 0, 0.06);
        }

        .character-card-header {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .character-card-header .name {
            font-weight: 600;
            font-size: 14px;
            color: #1a1a1a;
        }

        .character-card-header .role {
            margin-left: auto;
            font-size: 10px;
            text-transform: uppercase;
        }

        .lock-indicator {
            font-size: 12px;
            color: #10b981;
            margin-left: 6px;
            title: "Locked - finalized";
        }

        .character-card.locked {
            border-left: 3px solid #10b981;
        }

        .scene-card.locked .scene-header {
            border-left: 3px solid #10b981;
            letter-spacing: 1px;
            color: #aaa;
        }

        .character-description {
            font-size: 12px;
            color: #666;
            margin-top: 8px;
            line-height: 1.4;
            background: rgba(0, 0, 0, 0.04);
            padding: 4px 8px;
            border-radius: 6px;
        }

        /* Gradient Header */
        .chat-header {
            padding: 20px 28px;
            background: linear-gradient(135deg, #DC3545 0%, #c82333 100%);
            color: white;
            font-size: 18px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 16px;
            box-shadow: 0 4px 20px rgba(220, 53, 69, 0.3);
        }

        .back-link {
            color: white;
            text-decoration: none;
            font-size: 24px;
            opacity: 0.8;
            transition: opacity 0.2s ease;
            margin-right: 8px;
        }

        .back-link:hover {
            opacity: 1;
        }

        .chat-header .logo {
            width: 48px;
            height: 48px;
            background: white;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            color: #DC3545;
            font-size: 18px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            overflow: hidden;
            padding: 4px;
        }

        .chat-header .logo img {
            width: 100%;
            height: 100%;
            object-fit: contain;
        }

        .chat-header-text {
            flex: 1;
        }

        .chat-header-text span {
            display: block;
            font-size: 13px;
            color: rgba(255, 255, 255, 0.8);
            font-weight: 400;
            margin-top: 2px;
        }

        .messages {
            flex: 1;
            overflow-y: auto;
            padding: 28px;
            display: flex;
            flex-direction: column;
            gap: 24px;
        }

        .message {
            display: flex;
            gap: 14px;
            max-width: 80%;
            animation: slideIn 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        }

        @keyframes slideIn {
            from { opacity: 0; transform: translateY(16px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .message.user {
            align-self: flex-end;
            flex-direction: row-reverse;
        }

        .message-avatar {
            width: 36px;
            height: 36px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 600;
            flex-shrink: 0;
            font-size: 12px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }

        .user .message-avatar {
            background: linear-gradient(135deg, #DC3545 0%, #c82333 100%);
            color: white;
        }

        .assistant .message-avatar {
            background: transparent;
            padding: 0;
            box-shadow: none;
            border-radius: 0;
        }

        .assistant .message-avatar img {
            width: 100%;
            height: 100%;
            object-fit: contain;
        }

        .message-content {
            padding: 16px 20px;
            border-radius: 18px;
            line-height: 1.7;
            white-space: pre-wrap;
            font-size: 15px;
        }

        .user .message-content {
            background: linear-gradient(135deg, #DC3545 0%, #c82333 100%);
            color: white;
            border-radius: 18px 18px 4px 18px;
            box-shadow: 0 4px 12px rgba(220, 53, 69, 0.25);
        }

        .assistant .message-content {
            background: white;
            color: #1a1a1a;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04), 0 8px 24px rgba(0, 0, 0, 0.06);
            border-radius: 18px 18px 18px 4px;
        }

        .input-container {
            padding: 20px 28px;
            display: flex;
            gap: 14px;
            background: white;
            border-top: 1px solid rgba(0, 0, 0, 0.04);
        }

        #messageInput {
            flex: 1;
            padding: 16px 20px;
            border: 2px solid rgba(0, 0, 0, 0.06);
            border-radius: 16px;
            font-size: 15px;
            resize: none;
            max-height: 140px;
            background: #FDFCFA;
            color: #1a1a1a;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }

        #messageInput::placeholder {
            color: #bbb;
        }

        #messageInput:focus {
            outline: none;
            border-color: #DC3545;
            background: white;
            box-shadow: 0 0 0 4px rgba(220, 53, 69, 0.1);
        }

        #sendButton {
            padding: 16px 28px;
            background: linear-gradient(135deg, #DC3545 0%, #c82333 100%);
            color: white;
            border: none;
            border-radius: 16px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: 0 4px 12px rgba(220, 53, 69, 0.25);
        }

        #sendButton:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(220, 53, 69, 0.35);
        }

        #sendButton:active {
            transform: translateY(0);
        }

        #sendButton:disabled {
            background: #e0e0e0;
            color: #999;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }

        #sendButton.loading {
            position: relative;
            color: transparent;
        }

        #sendButton.loading::after {
            content: '';
            position: absolute;
            width: 18px;
            height: 18px;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            border: 2px solid rgba(255, 255, 255, 0.3);
            border-top-color: white;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }

        @keyframes spin {
            to { transform: translate(-50%, -50%) rotate(360deg); }
        }

        /* Autosave indicator */
        .autosave-indicator {
            font-size: 11px;
            color: #999;
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 4px 0;
        }

        .autosave-indicator.saving {
            color: #DC3545;
        }

        .autosave-indicator.saved {
            color: #20C997;
        }

        /* Celebration animation */
        @keyframes confetti-fall {
            0% { transform: translateY(-100%) rotate(0deg); opacity: 1; }
            100% { transform: translateY(100vh) rotate(720deg); opacity: 0; }
        }

        .confetti {
            position: fixed;
            width: 10px;
            height: 10px;
            top: 0;
            z-index: 10001;
            animation: confetti-fall 3s ease-out forwards;
        }

        /* Error retry button */
        .error-message {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .retry-btn {
            background: #DC3545;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 12px;
            width: fit-content;
        }

        .retry-btn:hover {
            background: #c82333;
        }

        /* Onboarding empty state */
        .onboarding-tip {
            background: linear-gradient(135deg, rgba(220, 53, 69, 0.05) 0%, rgba(220, 53, 69, 0.1) 100%);
            border: 1px dashed rgba(220, 53, 69, 0.3);
            border-radius: 12px;
            padding: 16px;
            margin: 8px 0;
        }

        .onboarding-tip h4 {
            color: #DC3545;
            margin: 0 0 8px 0;
            font-size: 13px;
        }

        .onboarding-tip p {
            color: #666;
            font-size: 12px;
            margin: 0;
            line-height: 1.5;
        }

        .typing-dots-container {
            display: flex !important;
            flex-direction: row !important;
            gap: 8px !important;
            padding: 16px 20px !important;
            align-items: center !important;
            background: white !important;
            border-radius: 18px 18px 18px 4px !important;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04), 0 8px 24px rgba(0, 0, 0, 0.06) !important;
        }

        .typing-dot {
            width: 10px !important;
            height: 10px !important;
            background-color: #DC3545 !important;
            border-radius: 50% !important;
            display: block !important;
            animation: pulse-bounce 1.4s infinite ease-in-out !important;
        }

        .typing-dot:nth-child(2) { animation-delay: 0.2s !important; }
        .typing-dot:nth-child(3) { animation-delay: 0.4s !important; }

        @keyframes pulse-bounce {
            0%, 80%, 100% {
                transform: scale(0.6);
                opacity: 0.4;
            }
            40% {
                transform: scale(1);
                opacity: 1;
            }
        }

        /* Sidebar Tabs */
        .sidebar-tabs {
            display: flex;
            gap: 10px;
            padding: 16px 20px;
            background: rgba(0, 0, 0, 0.02);
            border-bottom: 1px solid rgba(0, 0, 0, 0.06);
        }

        .sidebar-tab {
            flex: 1;
            padding: 12px 16px;
            border: none;
            border-radius: 10px;
            background: transparent;
            color: #888;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .sidebar-tab:hover {
            background: rgba(0, 0, 0, 0.04);
            color: #555;
        }

        .sidebar-tab.active {
            background: linear-gradient(135deg, #DC3545 0%, #c82333 100%);
            color: white;
            box-shadow: 0 2px 8px rgba(220, 53, 69, 0.25);
        }

        .tab-content {
            display: none;
            overflow-y: auto;
            flex: 1;
            padding: 8px 0;
        }

        .tab-content.active {
            display: block;
        }

        /* Building Tab - Act/Scene Structure */
        .structure-container {
            padding: 20px;
        }

        .act-section {
            margin-bottom: 20px;
        }

        .act-header {
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #bbb;
            padding: 0 4px 8px 4px;
            border-bottom: 1px solid rgba(0, 0, 0, 0.06);
            margin-bottom: 10px;
        }

        .scenes-list {
            display: flex;
            flex-direction: column;
            gap: 6px;
            padding-left: 8px;
        }

        .empty-scenes {
            font-size: 12px;
            color: #aaa;
            font-style: italic;
            padding: 8px 12px;
        }

        .scene-card {
            background: white;
            border: 1px solid rgba(0, 0, 0, 0.06);
            border-radius: 10px;
            overflow: hidden;
            transition: all 0.2s ease;
        }

        .scene-card:hover {
            border-color: rgba(220, 53, 69, 0.3);
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
        }

        .scene-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 10px 12px;
            cursor: pointer;
            user-select: none;
        }

        .scene-header:hover {
            background: rgba(0, 0, 0, 0.02);
        }

        .scene-number {
            font-size: 11px;
            font-weight: 700;
            color: #DC3545;
            background: rgba(220, 53, 69, 0.1);
            padding: 2px 8px;
            border-radius: 4px;
            margin-right: 8px;
        }

        .scene-title {
            flex: 1;
            font-size: 13px;
            font-weight: 500;
            color: #333;
        }

        .scene-toggle {
            font-size: 10px;
            color: #aaa;
            transition: transform 0.2s ease;
        }

        .scene-card.expanded .scene-toggle {
            transform: rotate(180deg);
        }

        .scene-beats {
            display: none;
            padding: 0 12px 12px 12px;
            border-top: 1px solid rgba(0, 0, 0, 0.04);
        }

        .scene-card.expanded .scene-beats {
            display: block;
        }

        .beat-item {
            display: flex;
            align-items: flex-start;
            gap: 8px;
            padding: 8px 0;
            border-bottom: 1px solid rgba(0, 0, 0, 0.03);
        }

        .beat-item:last-child {
            border-bottom: none;
        }

        .beat-bullet {
            width: 6px;
            height: 6px;
            background: #DC3545;
            border-radius: 50%;
            margin-top: 5px;
            flex-shrink: 0;
        }

        .beat-text {
            font-size: 12px;
            color: #555;
            line-height: 1.4;
        }

        .no-beats {
            font-size: 11px;
            color: #aaa;
            font-style: italic;
            padding: 8px 0;
        }

        .scene-description {
            font-size: 12px;
            color: #666;
            font-style: italic;
            padding: 8px 0;
            border-bottom: 1px solid rgba(0, 0, 0, 0.04);
            margin-bottom: 8px;
        }

        /* Action buttons for edit/delete */
        .item-actions {
            display: flex;
            gap: 4px;
            opacity: 0;
            transition: opacity 0.2s ease;
            margin-left: auto;
        }

        .scene-card:hover .item-actions,
        .character-card:hover .item-actions,
        .beat-item:hover .item-actions {
            opacity: 1;
        }

        .action-btn {
            width: 22px;
            height: 22px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.15s ease;
        }

        .edit-btn {
            background: rgba(32, 201, 151, 0.1);
            color: #20C997;
        }

        .edit-btn:hover {
            background: rgba(32, 201, 151, 0.2);
        }

        .delete-btn {
            background: rgba(220, 53, 69, 0.1);
            color: #DC3545;
        }

        .delete-btn:hover {
            background: rgba(220, 53, 69, 0.2);
        }

        .beat-delete {
            width: 18px;
            height: 18px;
            font-size: 10px;
            flex-shrink: 0;
        }

        .beat-item {
            position: relative;
        }

        .beat-item .beat-delete {
            opacity: 0;
            position: absolute;
            right: 0;
            top: 50%;
            transform: translateY(-50%);
        }

        .beat-item:hover .beat-delete {
            opacity: 1;
        }

        /* Command hint chips */
        .command-hints {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            padding: 8px 16px;
            background: rgba(0, 0, 0, 0.02);
            border-top: 1px solid rgba(0, 0, 0, 0.05);
        }

        .hint-chip {
            padding: 4px 10px;
            background: white;
            border: 1px solid rgba(220, 53, 69, 0.2);
            border-radius: 12px;
            font-size: 11px;
            color: #666;
            cursor: pointer;
            transition: all 0.15s ease;
            white-space: nowrap;
        }

        .hint-chip:hover {
            background: rgba(220, 53, 69, 0.1);
            border-color: #DC3545;
            color: #DC3545;
        }

        .hint-chip .cmd {
            color: #DC3545;
            font-weight: 600;
        }

        /* Outline Beats List */
        .outline-list {
            display: flex;
            flex-direction: column;
            gap: 6px;
        }

        .outline-item {
            display: flex;
            align-items: flex-start;
            gap: 10px;
            padding: 10px 12px;
            background: white;
            border: 1px solid rgba(0, 0, 0, 0.06);
            border-radius: 8px;
        }

        .outline-number {
            font-size: 11px;
            font-weight: 700;
            color: white;
            background: #DC3545;
            width: 20px;
            height: 20px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }

        .outline-text {
            font-size: 13px;
            color: #333;
            line-height: 1.4;
        }

        .status-badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 6px;
            font-size: 9px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-weight: 600;
        }

        .status-locked {
            background: linear-gradient(135deg, #20C997 0%, #1aa37a 100%);
            color: white;
        }

        .status-pending {
            background: rgba(0, 0, 0, 0.06);
            color: #999;
        }

        /* Section styling */
        .sidebar-section {
            display: flex;
            flex-direction: column;
            gap: 10px;
            padding: 0 16px;
            margin-bottom: 20px;
        }

        /* Handoff section */
        .handoff-section {
            margin-top: auto;
            padding: 16px;
            background: rgba(0, 0, 0, 0.02);
            border-radius: 12px;
        }

        .handoff-header h3 {
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #888;
            margin: 0 0 12px 0;
        }

        .handoff-checklist {
            display: flex;
            flex-direction: column;
            gap: 8px;
            margin-bottom: 16px;
        }

        .check-item {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 12px;
            color: #666;
        }

        .check-icon {
            width: 18px;
            height: 18px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 10px;
            flex-shrink: 0;
        }

        .check-icon.passed {
            background: linear-gradient(135deg, #20C997 0%, #1aa37a 100%);
            color: white;
        }

        .check-icon.pending {
            background: rgba(0, 0, 0, 0.08);
            color: #999;
        }

        .check-label {
            flex: 1;
        }

        .check-value {
            font-size: 10px;
            color: #999;
        }

        #handoffButton {
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, #20C997 0%, #1aa37a 100%);
            color: white;
            border: none;
            border-radius: 12px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: 0 4px 12px rgba(32, 201, 151, 0.25);
        }

        #handoffButton:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(32, 201, 151, 0.35);
        }

        #handoffButton:disabled {
            background: #e0e0e0;
            color: #999;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }

        .handoff-status {
            margin-top: 10px;
            font-size: 12px;
            text-align: center;
            color: #20C997;
            font-weight: 500;
        }

        .handoff-status.error {
            color: #DC3545;
        }

        /* Scrollbar styling */
        ::-webkit-scrollbar {
            width: 8px;
        }

        ::-webkit-scrollbar-track {
            background: transparent;
        }

        ::-webkit-scrollbar-thumb {
            background: rgba(0, 0, 0, 0.1);
            border-radius: 4px;
        }

        ::-webkit-scrollbar-thumb:hover {
            background: rgba(0, 0, 0, 0.2);
        }

        /* Inline editing styles */
        .editable {
            cursor: pointer;
            border-radius: 4px;
            transition: all 0.15s ease;
            position: relative;
            padding: 2px 4px;
            margin: -2px -4px;
        }

        .editable:hover {
            background-color: rgba(220, 53, 69, 0.08);
            outline: 1px dashed rgba(220, 53, 69, 0.3);
        }

        .editable:hover::after {
            content: 'click to edit';
            position: absolute;
            right: 4px;
            top: 50%;
            transform: translateY(-50%);
            font-size: 9px;
            color: #DC3545;
            background: white;
            padding: 2px 6px;
            border-radius: 3px;
            opacity: 0.9;
            pointer-events: none;
            white-space: nowrap;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }

        .editable.editing {
            background-color: white;
            cursor: text;
            outline: none;
        }

        .editable.editing::after {
            display: none;
        }

        .inline-edit-input {
            width: 100%;
            padding: 4px 8px;
            font-size: inherit;
            font-family: inherit;
            border: 2px solid #DC3545;
            border-radius: 4px;
            outline: none;
            box-sizing: border-box;
        }

        .inline-edit-input:focus {
            box-shadow: 0 0 0 3px rgba(220, 53, 69, 0.2);
        }

        .edit-hint {
            font-size: 10px;
            color: #888;
            font-style: italic;
            margin-top: 2px;
        }

        /* Beat text needs special handling for the edit hint */
        .beat-text.editable:hover::after {
            right: 30px; /* Account for delete button */
        }

        /* Scene title in header needs adjustment */
        .scene-title.editable:hover::after {
            right: 80px; /* Account for action buttons */
        }

        /* Brainstorm Progress Overlay */
        .brainstorm-overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.7);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            z-index: 1000;
            justify-content: center;
            align-items: center;
        }

        .brainstorm-overlay.active {
            display: flex;
        }

        .brainstorm-progress-card {
            background: white;
            border-radius: 20px;
            padding: 40px;
            max-width: 500px;
            width: 90%;
            text-align: center;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        }

        .brainstorm-progress-card h2 {
            margin: 0 0 10px 0;
            color: #1a1a1a;
            font-size: 24px;
        }

        .brainstorm-progress-card .subtitle {
            color: #666;
            font-size: 14px;
            margin-bottom: 30px;
        }

        .brainstorm-progress-bar {
            height: 8px;
            background: #e0e0e0;
            border-radius: 4px;
            overflow: hidden;
            margin: 20px 0;
        }

        .brainstorm-progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #20C997, #1aa37a);
            border-radius: 4px;
            transition: width 0.5s ease;
            width: 0%;
        }

        .brainstorm-scene-info {
            color: #666;
            font-size: 14px;
            margin: 10px 0;
        }

        .brainstorm-current-scene {
            color: #1a1a1a;
            font-size: 16px;
            font-weight: 500;
            margin: 15px 0;
            min-height: 24px;
        }

        .brainstorm-estimate {
            color: #999;
            font-size: 12px;
            margin-top: 20px;
        }

        .brainstorm-complete-btn {
            padding: 14px 36px;
            background: linear-gradient(135deg, #20C997, #1aa37a);
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            margin-top: 20px;
            transition: all 0.2s ease;
        }

        .brainstorm-complete-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(32, 201, 151, 0.4);
        }

        /* Expert Voting Panel */
        .expert-voting-container {
            display: none;
            max-width: 900px;
            width: 95%;
            max-height: 90vh;
            overflow-y: auto;
            background: white;
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        }

        .expert-voting-container.active {
            display: block;
        }

        .voting-header {
            text-align: center;
            margin-bottom: 25px;
        }

        .voting-header h2 {
            color: #1a1a1a;
            font-size: 22px;
            margin: 0 0 8px 0;
        }

        .voting-header p {
            color: #666;
            font-size: 14px;
            margin: 0;
        }

        .expert-cards {
            display: flex;
            flex-direction: column;
            gap: 20px;
        }

        .expert-card {
            background: #f8f8f8;
            border-radius: 12px;
            padding: 20px;
            border: 2px solid transparent;
            transition: all 0.2s ease;
        }

        .expert-card:hover {
            border-color: #DC3545;
        }

        .expert-card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }

        .expert-name {
            font-size: 16px;
            font-weight: 600;
            color: #1a1a1a;
        }

        .expert-name .emoji {
            margin-right: 8px;
        }

        .star-rating {
            display: flex;
            gap: 4px;
        }

        .star-rating .star {
            font-size: 24px;
            cursor: pointer;
            color: #ddd;
            transition: color 0.15s ease;
        }

        .star-rating .star.active {
            color: #FFD700;
        }

        .star-rating .star:hover {
            color: #FFC107;
        }

        .expert-content {
            font-size: 13px;
            color: #444;
            line-height: 1.6;
            max-height: 200px;
            overflow-y: auto;
            white-space: pre-wrap;
            background: white;
            padding: 12px;
            border-radius: 8px;
            border: 1px solid #e0e0e0;
        }

        .synthesize-btn {
            display: block;
            width: 100%;
            padding: 16px;
            margin-top: 25px;
            background: linear-gradient(135deg, #DC3545, #c82333);
            color: white;
            border: none;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .synthesize-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(220, 53, 69, 0.4);
        }

        .synthesize-btn:disabled {
            background: #ccc;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }

        /* Checkpoint Panel */
        .checkpoint-container {
            display: none;
            max-width: 700px;
            width: 95%;
            max-height: 85vh;
            overflow-y: auto;
            background: white;
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        }

        .checkpoint-container.active {
            display: block;
        }

        .checkpoint-header {
            text-align: center;
            margin-bottom: 25px;
            padding-bottom: 20px;
            border-bottom: 1px solid #eee;
        }

        .checkpoint-header h2 {
            color: #20C997;
            font-size: 24px;
            margin: 0 0 8px 0;
        }

        .checkpoint-header p {
            color: #666;
            font-size: 14px;
            margin: 0;
        }

        .checkpoint-scenes {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .checkpoint-scene {
            background: #f8f8f8;
            border-radius: 10px;
            padding: 15px;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .checkpoint-scene:hover {
            background: #f0f0f0;
        }

        .checkpoint-scene-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .checkpoint-scene-title {
            font-weight: 600;
            color: #1a1a1a;
        }

        .checkpoint-scene-preview {
            display: none;
            margin-top: 12px;
            padding-top: 12px;
            border-top: 1px solid #ddd;
            font-size: 13px;
            color: #555;
            line-height: 1.5;
            white-space: pre-wrap;
        }

        .checkpoint-scene.expanded .checkpoint-scene-preview {
            display: block;
        }

        .continue-btn {
            display: block;
            width: 100%;
            padding: 16px;
            margin-top: 25px;
            background: linear-gradient(135deg, #20C997, #1aa37a);
            color: white;
            border: none;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .continue-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(32, 201, 151, 0.4);
        }
    </style>
</head>
<body>
    <div class="main-container">
        <div class="chat-container">
            <div class="chat-header">
                <a href="/" class="back-link" title="Back to projects">&larr;</a>
                <div class="logo">
                    <img src="/static/syd_logo.png" alt="Syd" onerror="this.style.display='none'; this.parentElement.textContent='S';">
                </div>
                <div class="chat-header-text">
                    {{SESSION_NAME}}
                    <span>Brainstorming with Syd</span>
                </div>
            </div>

            <div class="messages" id="messages">
                <!-- Messages loaded dynamically -->
            </div>

            <div class="command-hints" id="commandHints">
                <span class="hint-chip" onclick="insertCommand('/title ')"><span class="cmd">/title</span> lock title</span>
                <span class="hint-chip" onclick="insertCommand('/logline ')"><span class="cmd">/logline</span> lock logline</span>
                <span class="hint-chip" onclick="insertCommand('/character ')"><span class="cmd">/character</span> add character</span>
                <span class="hint-chip" onclick="insertCommand('/scene ')"><span class="cmd">/scene</span> add scene</span>
                <span class="hint-chip" onclick="insertCommand('/beat ')"><span class="cmd">/beat</span> add beat</span>
                <span class="hint-chip" onclick="insertCommand('/note ')"><span class="cmd">/note</span> add note</span>
                <span class="hint-chip" onclick="insertCommand('/help')"><span class="cmd">/help</span> all commands</span>
            </div>

            <div class="input-container">
                <textarea
                    id="messageInput"
                    placeholder="Type your message..."
                    rows="1"
                ></textarea>
                <button id="sendButton">Send</button>
            </div>
        </div>

        <div class="sidebar" id="sidebar">
            <div class="sidebar-header">
                <h2>Project State</h2>
                <button class="collapse-btn" onclick="toggleSidebar()" title="Collapse">&#9664;</button>
            </div>

            <!-- Tab Switcher -->
            <div class="sidebar-tabs">
                <button class="sidebar-tab active" id="tabFoundation" onclick="switchTab('foundation')">1. Foundation</button>
                <button class="sidebar-tab" id="tabBuilding" onclick="switchTab('building')">2. Building</button>
            </div>

            <!-- Foundation Tab Content -->
            <div class="tab-content active" id="foundationTab">
                <div class="foundation-content">
                    <div class="field-block" id="titleBlock">
                        <div class="field-label">Title</div>
                        <div class="field-value pending editable" id="titleValue" data-field="title">Untitled</div>
                    </div>

                    <div class="field-block" id="loglineBlock">
                        <div class="field-label">Logline</div>
                        <div class="field-value pending editable" id="loglineValue" data-field="logline">What's the one-sentence pitch?</div>
                    </div>

                    <div class="field-block">
                        <div class="field-label">Characters <span class="field-count" id="characterCount">0</span></div>
                        <div class="character-cards" id="charactersContainer">
                            <div class="empty-hint" id="noCharacters">Use /character to add</div>
                        </div>
                    </div>

                    <div class="field-block">
                        <div class="field-label">Notebook <span class="field-count" id="notebookCount">0</span></div>
                        <div class="notebook-list" id="notebookValue">
                            <div class="empty-hint">Ideas saved during chat</div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Building Tab Content -->
            <div class="tab-content" id="buildingTab">
                <div class="structure-container" id="structureContainer">
                    <div class="act-section" id="act1Section">
                        <div class="act-header">Act 1</div>
                        <div class="scenes-list" id="act1Scenes">
                            <div class="empty-scenes">No scenes yet. Use /scene to add.</div>
                        </div>
                    </div>
                    <div class="act-section" id="act2Section">
                        <div class="act-header">Act 2</div>
                        <div class="scenes-list" id="act2Scenes">
                            <div class="empty-scenes">No scenes yet.</div>
                        </div>
                    </div>
                    <div class="act-section" id="act3Section">
                        <div class="act-header">Act 3</div>
                        <div class="scenes-list" id="act3Scenes">
                            <div class="empty-scenes">No scenes yet.</div>
                        </div>
                    </div>
                </div>

            </div>

            <!-- Handoff Section -->
            <div class="handoff-section">
                <div class="handoff-header">
                    <h3>Ready for Handoff?</h3>
                </div>
                <div class="handoff-checklist" id="handoffChecklist">
                    <!-- Populated by JS -->
                </div>
                <button id="handoffButton" disabled>Hand Off to BRAINSTORM</button>
                <div class="handoff-status" id="handoffStatus"></div>
            </div>
        </div>
        <button class="expand-btn" id="expandBtn" onclick="toggleSidebar()" title="Expand">&#9654;</button>
    </div>

    <script>
        const messagesDiv = document.getElementById('messages');
        const messageInput = document.getElementById('messageInput');
        const sendButton = document.getElementById('sendButton');
        const sidebar = document.getElementById('sidebar');
        const expandBtn = document.getElementById('expandBtn');
        const handoffButton = document.getElementById('handoffButton');

        // Track previous state for detecting changes
        let previousState = null;

        function toggleSidebar() {
            sidebar.classList.toggle('collapsed');
            expandBtn.style.display = sidebar.classList.contains('collapsed') ? 'block' : 'none';
        }

        function switchTab(tab) {
            // Update tab buttons
            document.getElementById('tabFoundation').classList.toggle('active', tab === 'foundation');
            document.getElementById('tabBuilding').classList.toggle('active', tab === 'building');

            // Update tab content
            document.getElementById('foundationTab').classList.toggle('active', tab === 'foundation');
            document.getElementById('buildingTab').classList.toggle('active', tab === 'building');
        }

        function toggleScene(sceneId) {
            const card = document.getElementById('scene-' + sceneId);
            if (card) {
                card.classList.toggle('expanded');
            }
        }

        // Edit/Delete handler functions
        function editScene(sceneNum, currentTitle) {
            const newTitle = prompt('Edit scene title:', currentTitle);
            if (newTitle && newTitle !== currentTitle) {
                sendMessage('/edit scene ' + sceneNum + ' ' + newTitle);
            }
        }

        function deleteScene(sceneNum) {
            if (confirm('Delete Scene ' + sceneNum + '? This cannot be undone.')) {
                sendMessage('/delete scene ' + sceneNum);
            }
        }

        function editCharacter(name) {
            const newDesc = prompt('Edit description for ' + name + ':');
            if (newDesc) {
                sendMessage('/edit character ' + name + ' - ' + newDesc);
            }
        }

        function deleteCharacter(name) {
            if (confirm('Delete character "' + name + '"? This cannot be undone.')) {
                sendMessage('/delete character ' + name);
            }
        }

        function deleteBeat(sceneNum, beatNum) {
            if (confirm('Delete this beat? This cannot be undone.')) {
                sendMessage('/delete beat ' + sceneNum + ' ' + beatNum);
            }
        }

        // ============================================
        // Inline editing functions (double-click to edit)
        // ============================================

        async function saveInlineEdit(fieldType, value, extraData = {}) {
            try {
                const payload = { type: fieldType, value: value, ...extraData };
                const response = await fetch('/api/field', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const result = await response.json();
                if (result.success) {
                    showToast('Saved!');
                    updateSidebar(result.state);
                    updateBuildingTab(result.state);
                } else {
                    showToast(result.error || 'Failed to save', 'error');
                }
                return result.success;
            } catch (e) {
                showToast('Failed to save', 'error');
                return false;
            }
        }

        function makeEditable(element, fieldType, extraData = {}) {
            if (element.classList.contains('editing')) return;

            const originalText = element.textContent;
            element.classList.add('editing');

            // Create input
            const input = document.createElement('input');
            input.type = 'text';
            input.className = 'inline-edit-input';
            input.value = originalText;

            // Replace content with input
            element.textContent = '';
            element.appendChild(input);
            input.focus();
            input.select();

            // Handle save on Enter, cancel on Escape
            input.addEventListener('keydown', async function(e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    const newValue = input.value.trim();
                    if (newValue && newValue !== originalText) {
                        const success = await saveInlineEdit(fieldType, newValue, extraData);
                        if (!success) {
                            element.textContent = originalText;
                        }
                    } else {
                        element.textContent = originalText;
                    }
                    element.classList.remove('editing');
                } else if (e.key === 'Escape') {
                    element.textContent = originalText;
                    element.classList.remove('editing');
                }
            });

            // Also save on blur
            input.addEventListener('blur', async function() {
                if (!element.classList.contains('editing')) return;
                const newValue = input.value.trim();
                if (newValue && newValue !== originalText) {
                    const success = await saveInlineEdit(fieldType, newValue, extraData);
                    if (!success) {
                        element.textContent = originalText;
                    }
                } else {
                    element.textContent = originalText;
                }
                element.classList.remove('editing');
            });
        }

        // Global event delegation for all editable elements (including dynamically rendered ones)
        // Use single click for more responsive editing
        document.addEventListener('click', function(e) {
            const el = e.target.closest('.editable');
            if (!el || el.classList.contains('editing')) return;

            // Don't trigger edit when clicking on action buttons within the same container
            if (e.target.closest('.action-btn') || e.target.closest('.item-actions')) return;

            const fieldType = el.dataset.field || el.id?.replace('Value', '') || null;
            if (!fieldType) return;

            // Build extraData from data attributes - map to API expected names
            const extraData = {};
            if (el.dataset.scene) extraData.scene_num = parseInt(el.dataset.scene);
            if (el.dataset.beatIdx !== undefined) extraData.beat_idx = parseInt(el.dataset.beatIdx);
            if (el.dataset.name) extraData.name = el.dataset.name;
            if (el.dataset.oldName) extraData.old_name = el.dataset.oldName;

            makeEditable(el, fieldType, extraData);
        });

        function updateBuildingTab(state) {
            const fields = state.fields;

            // Update scenes by act
            const scenes = fields.scenes || [];
            const act1Scenes = document.getElementById('act1Scenes');
            const act2Scenes = document.getElementById('act2Scenes');
            const act3Scenes = document.getElementById('act3Scenes');

            // Clear existing
            act1Scenes.innerHTML = '';
            act2Scenes.innerHTML = '';
            act3Scenes.innerHTML = '';

            if (scenes.length === 0) {
                act1Scenes.innerHTML = '<div class="empty-scenes">No scenes yet. Use /scene to add.</div>';
                act2Scenes.innerHTML = '<div class="empty-scenes">No scenes yet.</div>';
                act3Scenes.innerHTML = '<div class="empty-scenes">No scenes yet.</div>';
            } else {
                // Group scenes by act (1-10 = Act 1, 11-20 = Act 2, 21-30 = Act 3)
                scenes.forEach(scene => {
                    const num = scene.number || 0;
                    let container;
                    if (num <= 10) container = act1Scenes;
                    else if (num <= 20) container = act2Scenes;
                    else container = act3Scenes;

                    const card = document.createElement('div');
                    card.className = 'scene-card' + (scene.locked ? ' locked' : '');
                    card.id = 'scene-' + num;

                    // Get beats for this scene
                    const sceneBeats = scene.beats || [];
                    const sceneLockIcon = scene.locked ? '<span class="lock-indicator" title="Locked - finalized">&#128274;</span>' : '';

                    card.innerHTML = `
                        <div class="scene-header" onclick="toggleScene(${num})">
                            <span class="scene-number">${num}</span>
                            <span class="scene-title editable" data-field="scene_title" data-scene="${num}">${scene.title || 'Untitled'}</span>${sceneLockIcon}
                            <div class="item-actions">
                                <button class="action-btn edit-btn" onclick="event.stopPropagation(); editScene(${num}, '${(scene.title || '').replace(/'/g, "\\'")}')" title="Edit">&#9998;</button>
                                <button class="action-btn delete-btn" onclick="event.stopPropagation(); deleteScene(${num})" title="Delete">&#10005;</button>
                            </div>
                            <span class="scene-toggle">▼</span>
                        </div>
                        <div class="scene-beats">
                            ${scene.description ? `<div class="scene-description">${scene.description}</div>` : ''}
                            ${sceneBeats.length > 0
                                ? sceneBeats.map((b, bidx) => `
                                    <div class="beat-item">
                                        <div class="beat-bullet"></div>
                                        <div class="beat-text editable" data-field="beat" data-scene="${num}" data-beat-idx="${bidx}">${b}</div>
                                        <button class="action-btn delete-btn beat-delete" onclick="event.stopPropagation(); deleteBeat(${num}, ${bidx + 1})" title="Delete beat">&#10005;</button>
                                    </div>
                                `).join('')
                                : '<div class="no-beats">Use /beat ${num} to add beats</div>'
                            }
                        </div>
                    `;

                    container.appendChild(card);
                });

                // Add empty placeholders for acts with no scenes
                if (act1Scenes.children.length === 0) {
                    act1Scenes.innerHTML = '<div class="empty-scenes">No scenes yet.</div>';
                }
                if (act2Scenes.children.length === 0) {
                    act2Scenes.innerHTML = '<div class="empty-scenes">No scenes yet.</div>';
                }
                if (act3Scenes.children.length === 0) {
                    act3Scenes.innerHTML = '<div class="empty-scenes">No scenes yet.</div>';
                }
            }
        }

        function toggleCommandHelp() {
            const help = document.getElementById('commandHelp');
            const toggle = document.querySelector('.help-toggle');
            help.classList.toggle('visible');
            toggle.classList.toggle('active');
        }

        function insertCommand(cmd) {
            messageInput.value = cmd;
            messageInput.focus();
            // Place cursor at end
            messageInput.setSelectionRange(cmd.length, cmd.length);
        }

        // Toast notification system
        function showToast(message, type = 'success') {
            const toast = document.createElement('div');
            toast.className = `toast toast-${type}`;
            toast.textContent = message;
            toast.style.cssText = `
                position: fixed;
                bottom: 100px;
                left: 50%;
                transform: translateX(-50%);
                padding: 12px 24px;
                background: ${type === 'success' ? '#20C997' : type === 'error' ? '#DC3545' : '#333'};
                color: white;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 500;
                z-index: 10000;
                box-shadow: 0 4px 12px rgba(0,0,0,0.2);
                animation: toastIn 0.3s ease;
            `;
            document.body.appendChild(toast);
            setTimeout(() => {
                toast.style.animation = 'toastOut 0.3s ease';
                setTimeout(() => toast.remove(), 300);
            }, 3000);
        }

        // Undo function
        async function doUndo() {
            try {
                const response = await fetch('/api/undo');
                const result = await response.json();
                if (result.success) {
                    showToast(`Undone: ${result.undone.action} ${result.undone.type}`);
                    // Refresh state
                    const stateResponse = await fetch('/state');
                    const state = await stateResponse.json();
                    updateSidebar(state);
                } else {
                    showToast(result.error || 'Nothing to undo', 'error');
                }
            } catch (e) {
                showToast('Failed to undo', 'error');
            }
        }

        // Export function
        async function doExport() {
            try {
                const response = await fetch('/api/export?format=markdown');
                const result = await response.json();
                if (result.success) {
                    // Create download
                    const blob = new Blob([result.content], { type: 'text/markdown' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = result.filename || 'project.md';
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);
                    showToast('Exported to ' + result.filename);
                } else {
                    showToast(result.error || 'Export failed', 'error');
                }
            } catch (e) {
                showToast('Failed to export', 'error');
            }
        }

        // Strip directives from text
        function stripDirectives(text) {
            return text.replace(/\\[DIRECTIVE:[^\\]]+\\]\\s*/g, '');
        }

        // Auto-resize textarea
        messageInput.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 120) + 'px';
        });

        // Send message on Enter (Shift+Enter for new line) or Cmd/Ctrl+Enter
        messageInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
            if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                e.preventDefault();
                sendMessage();
            }
        });

        // Toggle sidebar with Escape key
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                toggleSidebar();
            }
        });

        sendButton.addEventListener('click', sendMessage);

        // Session ID for this chat
        const SESSION_ID = {{SESSION_ID}};

        // Load conversation history and state on page load
        async function loadSession() {
            console.log('loadSession() called for session:', SESSION_ID);

            // Load messages
            const msgResponse = await fetch('/api/sessions/' + SESSION_ID + '/messages');
            const msgData = await msgResponse.json();
            console.log('Messages loaded:', msgData.messages ? msgData.messages.length : 0);

            if (msgData.messages && msgData.messages.length > 0) {
                // Render existing messages
                msgData.messages.forEach(msg => {
                    if (msg.role === 'user') {
                        addMessage(msg.content, 'user');
                    } else {
                        addAssistantMessage(msg.content);
                    }
                });
            } else {
                // Show welcome message for new sessions with onboarding tips
                addAssistantMessage("Hi! I'm Syd. Got an idea for a romantic comedy?\\n\\nTell me anything - a character, a situation, a vibe.");
                showOnboardingTips();
            }

            // Load current state
            console.log('Fetching state...');
            const stateResponse = await fetch('/state');
            const state = await stateResponse.json();
            console.log('State loaded:', state);
            if (state && !state.error) {
                console.log('Calling updateSidebar with state');
                updateSidebar(state);
            } else {
                console.error('State error:', state);
            }

            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }

        function addAssistantMessage(text) {
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message assistant';

            const avatar = document.createElement('div');
            avatar.className = 'message-avatar';
            avatar.innerHTML = '<img src="/static/syd_logo.png" alt="Syd">';

            const content = document.createElement('div');
            content.className = 'message-content';
            content.textContent = text;

            messageDiv.appendChild(avatar);
            messageDiv.appendChild(content);
            messagesDiv.appendChild(messageDiv);
        }

        // Show onboarding tips for new sessions
        function showOnboardingTips() {
            const tipsDiv = document.createElement('div');
            tipsDiv.className = 'onboarding-tips';
            tipsDiv.innerHTML = `
                <div class="onboarding-tip">
                    <strong>Getting Started</strong>
                    <p>Start by pitching your romcom idea - a character, a situation, or just a vibe!</p>
                </div>
                <div class="onboarding-tip">
                    <strong>Quick Commands</strong>
                    <p>Use <code>/character</code>, <code>/scene</code>, and <code>/beat</code> to add elements directly.</p>
                </div>
                <div class="onboarding-tip">
                    <strong>Lock Your Decisions</strong>
                    <p>Say "lock the title" or "lock the logline" when you're happy with them.</p>
                </div>
            `;
            messagesDiv.appendChild(tipsDiv);
        }

        // Confetti celebration for handoff ready
        let hasShownCelebration = false;
        function showCelebration() {
            if (hasShownCelebration) return;
            hasShownCelebration = true;

            const colors = ['#DC3545', '#20C997', '#FFD700', '#FF69B4', '#4169E1'];
            for (let i = 0; i < 50; i++) {
                const confetti = document.createElement('div');
                confetti.className = 'confetti';
                confetti.style.left = Math.random() * 100 + 'vw';
                confetti.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)];
                confetti.style.animationDelay = Math.random() * 2 + 's';
                confetti.style.borderRadius = Math.random() > 0.5 ? '50%' : '0';
                document.body.appendChild(confetti);
                setTimeout(() => confetti.remove(), 5000);
            }
            showToast('Your romcom is ready for BRAINSTORM!', 'success');
        }

        // Load session on page load
        loadSession();

        // =====================================================================
        // INTERACTIVE BRAINSTORM WITH VOTING & CHECKPOINTS
        // =====================================================================

        let brainstormEventSource = null;
        let currentVotingSceneNum = null;
        let currentVotes = { books: 2, plays: 2, scripts: 2 };  // Default to 2 stars

        function startBrainstormProgressStream() {
            const overlay = document.getElementById('brainstormOverlay');
            overlay.classList.add('active');

            // Initialize star rating click handlers
            initStarRatings();

            brainstormEventSource = new EventSource('/api/brainstorm/progress');

            brainstormEventSource.onmessage = function(event) {
                const data = JSON.parse(event.data);

                if (data.type === 'done' || data.type === 'idle') {
                    brainstormEventSource.close();
                    if (data.status === 'completed') {
                        showBrainstormComplete();
                    } else if (data.status === 'error') {
                        showBrainstormError(data.error);
                    }
                    return;
                }

                // Handle different states
                handleBrainstormState(data);
            };

            brainstormEventSource.onerror = function(error) {
                console.error('SSE Error:', error);
                brainstormEventSource.close();
                pollBrainstormStatus();
            };
        }

        function handleBrainstormState(data) {
            const progressCard = document.getElementById('progressCard');
            const votingPanel = document.getElementById('expertVotingPanel');
            const checkpointPanel = document.getElementById('checkpointPanel');

            // Hide all panels first
            progressCard.style.display = 'none';
            votingPanel.classList.remove('active');
            checkpointPanel.classList.remove('active');

            if (data.status === 'awaiting_vote') {
                // Show voting panel
                showExpertVotingPanel(data);
            } else if (data.status === 'checkpoint') {
                // Show checkpoint panel
                showCheckpointPanel(data);
            } else if (data.status === 'running') {
                // Show progress
                progressCard.style.display = 'block';
                updateBrainstormProgress(data);
            } else if (data.status === 'completed') {
                showBrainstormComplete();
            } else if (data.status === 'error') {
                showBrainstormError(data.error);
            }
        }

        function showExpertVotingPanel(data) {
            const votingPanel = document.getElementById('expertVotingPanel');
            votingPanel.classList.add('active');

            currentVotingSceneNum = data.awaiting_vote_for_scene;
            currentVotes = { books: 2, plays: 2, scripts: 2 };  // Reset to default

            // Update title
            document.getElementById('votingSceneTitle').textContent =
                'Scene ' + data.current_scene + ': ' + data.current_scene_title;

            // Update expert content
            const perspectives = data.current_expert_perspectives || {};
            document.getElementById('booksExpertContent').textContent =
                perspectives.books || '(No response from this expert)';
            document.getElementById('playsExpertContent').textContent =
                perspectives.plays || '(No response from this expert)';
            document.getElementById('scriptsExpertContent').textContent =
                perspectives.scripts || '(No response from this expert)';

            // Reset star ratings to default (2 stars)
            resetStarRatings();
        }

        function showCheckpointPanel(data) {
            const checkpointPanel = document.getElementById('checkpointPanel');
            checkpointPanel.classList.add('active');

            const actNum = data.checkpoint_act;
            document.getElementById('checkpointTitle').textContent = 'Act ' + actNum + ' Complete!';

            // Populate scenes list
            const scenesContainer = document.getElementById('checkpointScenes');
            scenesContainer.innerHTML = '';

            const completedScenes = data.completed_scenes_data || [];
            completedScenes.forEach(scene => {
                const sceneEl = document.createElement('div');
                sceneEl.className = 'checkpoint-scene';
                sceneEl.innerHTML = `
                    <div class="checkpoint-scene-header">
                        <span class="checkpoint-scene-title">Scene ${scene.scene_num}: ${scene.title}</span>
                        <span style="color: #888; font-size: 12px;">Click to expand</span>
                    </div>
                    <div class="checkpoint-scene-preview">${scene.blueprint_preview || 'No preview available'}</div>
                `;
                sceneEl.onclick = function() {
                    this.classList.toggle('expanded');
                };
                scenesContainer.appendChild(sceneEl);
            });

            // Update continue button text
            const nextAct = actNum === 1 ? 'Act 2' : 'Act 3';
            document.getElementById('continueBtn').textContent = 'Continue to ' + nextAct;
        }

        function initStarRatings() {
            document.querySelectorAll('.star-rating').forEach(ratingEl => {
                const bucket = ratingEl.dataset.bucket;
                ratingEl.querySelectorAll('.star').forEach(star => {
                    star.onclick = function() {
                        const value = parseInt(this.dataset.value);
                        setStarRating(bucket, value);
                    };
                });
            });
        }

        function setStarRating(bucket, value) {
            currentVotes[bucket] = value;

            // Update visual
            const ratingEl = document.querySelector(`.star-rating[data-bucket="${bucket}"]`);
            ratingEl.querySelectorAll('.star').forEach(star => {
                const starValue = parseInt(star.dataset.value);
                if (starValue <= value) {
                    star.classList.add('active');
                } else {
                    star.classList.remove('active');
                }
            });
        }

        function resetStarRatings() {
            ['books', 'plays', 'scripts'].forEach(bucket => {
                setStarRating(bucket, 2);  // Default to 2 stars
            });
        }

        async function submitVotes() {
            if (!currentVotingSceneNum) {
                console.error('No scene number for voting');
                return;
            }

            const btn = document.getElementById('synthesizeBtn');
            btn.disabled = true;
            btn.textContent = 'Synthesizing...';

            try {
                const response = await fetch('/api/brainstorm/vote', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        scene_num: currentVotingSceneNum,
                        votes: currentVotes
                    })
                });

                const result = await response.json();
                if (!result.success) {
                    console.error('Vote submission failed:', result.error);
                }
            } catch (e) {
                console.error('Vote submission error:', e);
            }

            btn.disabled = false;
            btn.textContent = 'Synthesize Scene Blueprint';
        }

        async function continueFromCheckpoint() {
            const btn = document.getElementById('continueBtn');
            btn.disabled = true;
            btn.textContent = 'Continuing...';

            try {
                const response = await fetch('/api/brainstorm/checkpoint/continue', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({})
                });

                const result = await response.json();
                if (!result.success) {
                    console.error('Checkpoint continue failed:', result.error);
                }
            } catch (e) {
                console.error('Checkpoint continue error:', e);
            }

            btn.disabled = false;
            btn.textContent = 'Continue to Next Act';
        }

        function updateBrainstormProgress(data) {
            const fill = document.getElementById('brainstormProgressFill');
            const sceneNum = document.getElementById('brainstormSceneNum');
            const totalScenes = document.getElementById('brainstormTotalScenes');
            const currentScene = document.getElementById('brainstormCurrentScene');
            const estimate = document.getElementById('brainstormEstimate');

            const completed = data.completed_scenes || 0;
            const total = data.total_scenes || 30;
            const percent = (completed / total) * 100;

            fill.style.width = percent + '%';
            sceneNum.textContent = completed;
            totalScenes.textContent = total;

            if (data.current_scene_title) {
                currentScene.textContent = 'Processing: Scene ' + data.current_scene + ' - ' + data.current_scene_title;
            } else if (data.status === 'running') {
                currentScene.textContent = 'Synthesizing...';
            }

            const remaining = total - completed;
            if (remaining > 0) {
                estimate.textContent = remaining + ' scenes remaining';
            } else {
                estimate.textContent = 'Finishing up...';
            }
        }

        function showBrainstormComplete() {
            const progressCard = document.getElementById('progressCard');
            const votingPanel = document.getElementById('expertVotingPanel');
            const checkpointPanel = document.getElementById('checkpointPanel');

            votingPanel.classList.remove('active');
            checkpointPanel.classList.remove('active');
            progressCard.style.display = 'block';

            progressCard.innerHTML = `
                <h2 style="color: #20C997;">Brainstorm Complete!</h2>
                <p class="subtitle">All scene blueprints have been generated with your input.</p>
                <p style="color: #666; margin: 20px 0; font-size: 14px;">
                    Your romcom is now ready for the WRITE phase.
                </p>
                <button onclick="closeBrainstormOverlay()" class="brainstorm-complete-btn">
                    Done
                </button>
            `;
        }

        function showBrainstormError(error) {
            const progressCard = document.getElementById('progressCard');
            progressCard.style.display = 'block';
            progressCard.innerHTML = `
                <h2 style="color: #DC3545;">Brainstorm Error</h2>
                <p class="subtitle">${error || 'An error occurred during brainstorm generation.'}</p>
                <button onclick="closeBrainstormOverlay()" class="brainstorm-complete-btn" style="background: #DC3545;">
                    Close
                </button>
            `;
        }

        function closeBrainstormOverlay() {
            document.getElementById('brainstormOverlay').classList.remove('active');
            // Reset panels
            document.getElementById('progressCard').style.display = 'block';
            document.getElementById('expertVotingPanel').classList.remove('active');
            document.getElementById('checkpointPanel').classList.remove('active');
        }

        // Fallback polling if SSE fails
        async function pollBrainstormStatus() {
            const overlay = document.getElementById('brainstormOverlay');
            while (overlay.classList.contains('active')) {
                try {
                    const response = await fetch('/api/brainstorm/status');
                    const data = await response.json();

                    if (data.status === 'completed') {
                        showBrainstormComplete();
                        break;
                    } else if (data.status === 'error') {
                        showBrainstormError(data.error);
                        break;
                    } else if (!data.active && data.status === 'idle') {
                        break;
                    }

                    handleBrainstormState(data);
                    await new Promise(r => setTimeout(r, 2000));
                } catch (e) {
                    console.error('Polling error:', e);
                    break;
                }
            }
        }

        // =====================================================================
        // HANDOFF BUTTON HANDLER
        // =====================================================================

        // Handoff button handler
        handoffButton.addEventListener('click', async function() {
            handoffButton.disabled = true;
            const handoffStatus = document.getElementById('handoffStatus');
            handoffStatus.textContent = 'Exporting to BRAINSTORM...';
            handoffStatus.className = 'handoff-status';

            try {
                const response = await fetch('/api/handoff', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ session_id: SESSION_ID })
                });
                const result = await response.json();

                if (result.success) {
                    handoffStatus.textContent = 'Handoff complete! Starting brainstorm...';
                    handoffStatus.className = 'handoff-status';

                    // Start brainstorm progress stream if brainstorm was started
                    if (result.brainstorm_started) {
                        setTimeout(() => {
                            startBrainstormProgressStream();
                        }, 500);
                    } else if (result.redirect_url) {
                        // Fallback to redirect if no brainstorm
                        setTimeout(() => {
                            window.location.href = result.redirect_url;
                        }, 1500);
                    }
                } else {
                    handoffStatus.textContent = result.error || 'Handoff failed';
                    handoffStatus.className = 'handoff-status error';
                    handoffButton.disabled = false;
                }
            } catch (e) {
                handoffStatus.textContent = 'Connection error';
                handoffStatus.className = 'handoff-status error';
                handoffButton.disabled = false;
            }
        });

        // Store last message for retry
        let lastMessage = '';

        async function sendMessage(retryMessage = null) {
            const message = retryMessage || messageInput.value.trim();
            if (!message) return;

            lastMessage = message;

            // Add user message (only if not a retry)
            if (!retryMessage) {
                addMessage(message, 'user');
                messageInput.value = '';
                messageInput.style.height = 'auto';
            }

            // Send to backend and stream response
            sendButton.disabled = true;
            sendButton.classList.add('loading');
            showTypingIndicator();
            updateAutosaveIndicator('saving');

            try {
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message })
                });

                const reader = response.body.getReader();
                const decoder = new TextDecoder();

                removeTypingIndicator();
                const messageDiv = createAssistantMessage();
                const content = messageDiv.querySelector('.message-content');

                let buffer = '';

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    const text = decoder.decode(value);
                    const lines = text.split('\\n');

                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            const data = line.slice(6);
                            if (data === '[DONE]') continue;

                            try {
                                const parsed = JSON.parse(data);
                                if (parsed.type === 'chunk') {
                                    // Buffer the chunk and strip directives before displaying
                                    buffer += parsed.content;
                                    content.textContent = stripDirectives(buffer);
                                    messagesDiv.scrollTop = messagesDiv.scrollHeight;
                                } else if (parsed.type === 'state') {
                                    updateSidebar(parsed.state);
                                    updateAutosaveIndicator('saved');
                                }
                            } catch (e) {}
                        }
                    }
                }
                updateAutosaveIndicator('saved');
            } catch (error) {
                removeTypingIndicator();
                addErrorMessage('Could not connect to server');
                updateAutosaveIndicator('error');
            }

            sendButton.disabled = false;
            sendButton.classList.remove('loading');
            messageInput.focus();
        }

        function addErrorMessage(errorText) {
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message assistant';

            const avatar = document.createElement('div');
            avatar.className = 'message-avatar';
            avatar.innerHTML = '<img src="/static/syd_logo.png" alt="Syd">';

            const content = document.createElement('div');
            content.className = 'message-content error-message';
            content.innerHTML = `
                <span>Error: ${errorText}</span>
                <button class="retry-btn" onclick="retryLastMessage()">Retry</button>
            `;

            messageDiv.appendChild(avatar);
            messageDiv.appendChild(content);
            messagesDiv.appendChild(messageDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }

        function retryLastMessage() {
            if (lastMessage) {
                // Remove the error message
                const messages = messagesDiv.querySelectorAll('.message');
                const lastMsg = messages[messages.length - 1];
                if (lastMsg && lastMsg.querySelector('.error-message')) {
                    lastMsg.remove();
                }
                sendMessage(lastMessage);
            }
        }

        function updateAutosaveIndicator(status) {
            let indicator = document.getElementById('autosaveIndicator');
            if (!indicator) {
                indicator = document.createElement('div');
                indicator.id = 'autosaveIndicator';
                indicator.className = 'autosave-indicator';
                const inputContainer = document.querySelector('.input-container');
                if (inputContainer) {
                    inputContainer.insertBefore(indicator, inputContainer.firstChild);
                }
            }

            if (status === 'saving') {
                indicator.className = 'autosave-indicator saving';
                indicator.innerHTML = 'Saving...';
            } else if (status === 'saved') {
                indicator.className = 'autosave-indicator saved';
                const now = new Date();
                indicator.innerHTML = `Saved ${now.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}`;
            } else if (status === 'error') {
                indicator.className = 'autosave-indicator';
                indicator.innerHTML = 'Save failed';
            }
        }

        function addMessage(text, sender) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${sender}`;

            const avatar = document.createElement('div');
            avatar.className = 'message-avatar';
            avatar.textContent = sender === 'user' ? 'You' : 'Syd';

            const content = document.createElement('div');
            content.className = 'message-content';
            content.textContent = text;

            messageDiv.appendChild(avatar);
            messageDiv.appendChild(content);
            messagesDiv.appendChild(messageDiv);

            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }

        function createAssistantMessage() {
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message assistant';

            const avatar = document.createElement('div');
            avatar.className = 'message-avatar';
            avatar.innerHTML = '<img src="/static/syd_logo.png" alt="Syd">';

            const content = document.createElement('div');
            content.className = 'message-content';
            content.textContent = '';

            messageDiv.appendChild(avatar);
            messageDiv.appendChild(content);
            messagesDiv.appendChild(messageDiv);

            return messageDiv;
        }

        function showTypingIndicator() {
            const indicator = document.createElement('div');
            indicator.className = 'message assistant';
            indicator.id = 'typingIndicator';
            indicator.innerHTML = `
                <div class="message-avatar"><img src="/static/syd_logo.png" alt="Syd"></div>
                <div class="typing-dots-container">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            `;
            messagesDiv.appendChild(indicator);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }

        function removeTypingIndicator() {
            const indicator = document.getElementById('typingIndicator');
            if (indicator) indicator.remove();
        }

        function animateUpdate(elementId) {
            const el = document.getElementById(elementId);
            if (el) {
                el.classList.add('just-updated');
                setTimeout(() => el.classList.remove('just-updated'), 500);
            }
        }

        function updateSidebar(state) {
            console.log('updateSidebar called with:', state);
            const fields = state.fields;
            const locked = state.locked;
            console.log('Fields:', fields);
            console.log('Title:', fields.title);
            console.log('Characters:', fields.characters);

            const titleLocked = locked && locked.title;
            const loglineLocked = locked && locked.logline;

            // Title
            const titleValue = document.getElementById('titleValue');
            if (fields.title) {
                const changed = !previousState || previousState.fields.title !== fields.title;
                titleValue.textContent = fields.title;
                titleValue.className = 'field-value locked editable';
                titleValue.dataset.field = 'title';
                if (changed) animateUpdate('titleValue');
            } else {
                titleValue.textContent = 'Untitled';
                titleValue.className = 'field-value pending editable';
                titleValue.dataset.field = 'title';
            }

            // Logline
            const loglineValue = document.getElementById('loglineValue');
            if (fields.logline) {
                const changed = !previousState || previousState.fields.logline !== fields.logline;
                loglineValue.textContent = fields.logline;
                loglineValue.className = 'field-value locked editable';
                loglineValue.dataset.field = 'logline';
                if (changed) animateUpdate('loglineValue');
            } else {
                loglineValue.textContent = "What's the one-sentence pitch?";
                loglineValue.className = 'field-value pending editable';
                loglineValue.dataset.field = 'logline';
            }

            // Character count
            const charCount = fields.characters ? fields.characters.length : 0;
            document.getElementById('characterCount').textContent = charCount;

            // Characters - render as cards
            const container = document.getElementById('charactersContainer');
            const noChars = document.getElementById('noCharacters');

            if (fields.characters && fields.characters.length > 0) {
                if (noChars) noChars.style.display = 'none';

                // Clear existing cards (except the placeholder)
                const existingCards = container.querySelectorAll('.character-card');
                existingCards.forEach(c => c.remove());

                fields.characters.forEach((char, idx) => {
                    const card = document.createElement('div');
                    card.className = 'character-card' + (char.locked ? ' locked' : '');

                    const escapedName = (char.name || '').replace(/'/g, "\\'").replace(/"/g, '&quot;');
                    const lockIcon = char.locked ? '<span class="lock-indicator" title="Locked - finalized">&#128274;</span>' : '';
                    card.innerHTML = `
                        <div class="character-card-header">
                            <span class="name editable" data-field="character_name" data-old-name="${escapedName}">${char.name || 'Unnamed'}</span>${lockIcon}
                            <span class="role">${(char.role || '').replace('_', ' ')}</span>
                            <div class="item-actions">
                                <button class="action-btn edit-btn" onclick="editCharacter('${escapedName}')" title="Edit">&#9998;</button>
                                <button class="action-btn delete-btn" onclick="deleteCharacter('${escapedName}')" title="Delete">&#10005;</button>
                            </div>
                        </div>
                        ${char.description ? `<div class="character-description editable" data-field="character_description" data-name="${escapedName}">${char.description}</div>` : ''}
                    `;

                    container.appendChild(card);
                });
            } else {
                if (noChars) noChars.style.display = 'block';
            }

            // Notebook
            const notebookValue = document.getElementById('notebookValue');
            const notebookCount = document.getElementById('notebookCount');
            if (fields.notebook && fields.notebook.length > 0) {
                const changed = !previousState || (previousState.fields.notebook || []).length !== fields.notebook.length;
                notebookCount.textContent = fields.notebook.length;
                // Show last 5 ideas
                const recent = fields.notebook.slice(-5).reverse();
                notebookValue.innerHTML = recent.map(n => '<div class="notebook-item">' + n + '</div>').join('');
                if (changed) animateUpdate('notebookValue');
            } else {
                notebookCount.textContent = '0';
                notebookValue.innerHTML = '<div class="empty-hint">Ideas saved during chat</div>';
            }

            // Update building tab
            updateBuildingTab(state);

            // Update handoff checklist
            updateHandoffChecklist(state);

            // Store state for comparison
            previousState = JSON.parse(JSON.stringify(state));
        }

        function updateHandoffChecklist(state) {
            const validation = state.handoff_validation || {};
            const checks = validation.checks || {};
            const checklist = document.getElementById('handoffChecklist');
            const handoffButton = document.getElementById('handoffButton');

            // Build checklist HTML
            let html = '';
            const checkOrder = ['title_locked', 'logline_locked', 'characters_defined', 'scenes_created', 'beats_added'];

            for (const key of checkOrder) {
                const check = checks[key];
                if (!check) continue;

                const iconClass = check.passed ? 'passed' : 'pending';
                const icon = check.passed ? '&#10003;' : '&#9675;';

                html += `
                    <div class="check-item">
                        <div class="check-icon ${iconClass}">${icon}</div>
                        <span class="check-label">${check.label}</span>
                        <span class="check-value">${check.value}</span>
                    </div>
                `;
            }

            checklist.innerHTML = html;

            // Enable/disable handoff button
            handoffButton.disabled = !validation.ready;

            // Celebrate when handoff becomes ready
            if (validation.ready) {
                showCelebration();
            }
        }
    </script>

    <!-- Brainstorm Progress Overlay -->
    <div class="brainstorm-overlay" id="brainstormOverlay">
        <!-- Progress Card (shown during running/synthesizing) -->
        <div class="brainstorm-progress-card" id="progressCard">
            <h2>Generating Scene Blueprints</h2>
            <p class="subtitle">Consulting expert knowledge bases for each scene...</p>
            <div class="brainstorm-progress-bar">
                <div class="brainstorm-progress-fill" id="brainstormProgressFill"></div>
            </div>
            <div class="brainstorm-scene-info">
                <span id="brainstormSceneNum">0</span> of <span id="brainstormTotalScenes">30</span> scenes complete
            </div>
            <div class="brainstorm-current-scene" id="brainstormCurrentScene">
                Preparing...
            </div>
            <div class="brainstorm-estimate" id="brainstormEstimate">
                Estimated time: ~25-45 minutes
            </div>
        </div>

        <!-- Expert Voting Panel (shown during awaiting_vote) -->
        <div class="expert-voting-container" id="expertVotingPanel">
            <div class="voting-header">
                <h2 id="votingSceneTitle">Scene 1: Title</h2>
                <p>Rate each expert's guidance (click stars). Higher ratings = more influence on the final blueprint.</p>
            </div>
            <div class="expert-cards">
                <!-- Books Expert -->
                <div class="expert-card" data-bucket="books">
                    <div class="expert-card-header">
                        <span class="expert-name"><span class="emoji">📚</span>Structure Expert</span>
                        <div class="star-rating" data-bucket="books">
                            <span class="star" data-value="1">★</span>
                            <span class="star active" data-value="2">★</span>
                            <span class="star" data-value="3">★</span>
                        </div>
                    </div>
                    <div class="expert-content" id="booksExpertContent">Loading...</div>
                </div>
                <!-- Plays Expert -->
                <div class="expert-card" data-bucket="plays">
                    <div class="expert-card-header">
                        <span class="expert-name"><span class="emoji">🎭</span>Story Patterns Expert</span>
                        <div class="star-rating" data-bucket="plays">
                            <span class="star" data-value="1">★</span>
                            <span class="star active" data-value="2">★</span>
                            <span class="star" data-value="3">★</span>
                        </div>
                    </div>
                    <div class="expert-content" id="playsExpertContent">Loading...</div>
                </div>
                <!-- Scripts Expert -->
                <div class="expert-card" data-bucket="scripts">
                    <div class="expert-card-header">
                        <span class="expert-name"><span class="emoji">🎬</span>Reference Expert</span>
                        <div class="star-rating" data-bucket="scripts">
                            <span class="star" data-value="1">★</span>
                            <span class="star active" data-value="2">★</span>
                            <span class="star" data-value="3">★</span>
                        </div>
                    </div>
                    <div class="expert-content" id="scriptsExpertContent">Loading...</div>
                </div>
            </div>
            <button class="synthesize-btn" id="synthesizeBtn" onclick="submitVotes()">
                Synthesize Scene Blueprint
            </button>
        </div>

        <!-- Checkpoint Panel (shown during checkpoint) -->
        <div class="checkpoint-container" id="checkpointPanel">
            <div class="checkpoint-header">
                <h2 id="checkpointTitle">Act 1 Complete!</h2>
                <p>Review your scene blueprints before continuing. Click a scene to expand its preview.</p>
            </div>
            <div class="checkpoint-scenes" id="checkpointScenes">
                <!-- Scenes populated dynamically -->
            </div>
            <button class="continue-btn" id="continueBtn" onclick="continueFromCheckpoint()">
                Continue to Next Act
            </button>
        </div>
    </div>
</body>
</html>
"""

if __name__ == "__main__":
    import uvicorn
    print("Starting Lizzy IDEATE web interface...")
    print("Open http://localhost:8888 in your browser")
    uvicorn.run(app, host="0.0.0.0", port=8888, log_level="warning")
