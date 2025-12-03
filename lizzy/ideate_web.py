"""
Web interface for IDEATE - Conversational Pre-Planning

Run with: python -m lizzy.ideate_web
Then open: http://localhost:8888
"""

import os
import json
import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from .ideate import IdeateSession
from .database import Database

app = FastAPI()

# Serve static files
STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Database path for session persistence
DB_PATH = Path(__file__).parent.parent / "ideate_sessions.db"

# Global session and current session ID
session = None
current_session_id = None
db = None

@app.on_event("startup")
async def startup():
    global db
    db = Database(DB_PATH)
    db.initialize_schema()
    print(f"Database initialized at {DB_PATH}")

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


@app.post("/api/handoff")
async def handoff_to_brainstorm(request: Request):
    """
    Hand off the ideation session to BRAINSTORM phase.

    Validates the session is ready, then exports to the main Lizzy database
    for use in BRAINSTORM/WRITE phases.
    """
    from pathlib import Path

    if not session:
        return {"error": "No active session"}

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
        # Export to main lizzy database
        db_path = Path(__file__).parent.parent / "lizzy.db"
        project_id = session.save_to_database(db_path)

        # Mark session as handed off in ideate database
        if current_session_id:
            db.update_ideate_session(
                current_session_id,
                stage="handed_off"
            )

        return {
            "success": True,
            "project_id": project_id,
            "message": "Successfully handed off to BRAINSTORM phase",
            # Could redirect to brainstorm web interface if it exists
            # "redirect_url": f"/brainstorm/{project_id}"
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }

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
            transition: background-color 0.15s ease;
        }

        .editable:hover {
            background-color: rgba(0, 0, 0, 0.05);
        }

        .editable.editing {
            background-color: white;
            cursor: text;
        }

        .inline-edit-input {
            width: 100%;
            padding: 4px 8px;
            font-size: inherit;
            font-family: inherit;
            border: 2px solid #FF6B9D;
            border-radius: 4px;
            outline: none;
            box-sizing: border-box;
        }

        .inline-edit-input:focus {
            box-shadow: 0 0 0 3px rgba(255, 107, 157, 0.2);
        }

        .edit-hint {
            font-size: 10px;
            color: #888;
            font-style: italic;
            margin-top: 2px;
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
                        <div class="field-value pending" id="titleValue">Untitled</div>
                    </div>

                    <div class="field-block" id="loglineBlock">
                        <div class="field-label">Logline</div>
                        <div class="field-value pending" id="loglineValue">What's the one-sentence pitch?</div>
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
        document.addEventListener('dblclick', function(e) {
            const el = e.target.closest('.editable');
            if (!el || el.classList.contains('editing')) return;

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

        // Add editable class to title/logline on load
        document.addEventListener('DOMContentLoaded', function() {
            const titleValue = document.getElementById('titleValue');
            const loglineValue = document.getElementById('loglineValue');
            if (titleValue) {
                titleValue.classList.add('editable');
                titleValue.dataset.field = 'title';
            }
            if (loglineValue) {
                loglineValue.classList.add('editable');
                loglineValue.dataset.field = 'logline';
            }
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
                    card.className = 'scene-card';
                    card.id = 'scene-' + num;

                    // Get beats for this scene
                    const sceneBeats = scene.beats || [];

                    card.innerHTML = `
                        <div class="scene-header" onclick="toggleScene(${num})">
                            <span class="scene-number">${num}</span>
                            <span class="scene-title editable" data-field="scene_title" data-scene="${num}">${scene.title || 'Untitled'}</span>
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

        // Send message on Enter (Shift+Enter for new line)
        messageInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
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
                // Show welcome message for new sessions
                addAssistantMessage("Hi! I'm Syd. Got an idea for a romantic comedy?\\n\\nTell me anything - a character, a situation, a vibe.");
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

        // Load session on page load
        loadSession();

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
                    handoffStatus.textContent = 'Handoff complete!';
                    handoffStatus.className = 'handoff-status';
                    // Optionally redirect to BRAINSTORM
                    if (result.redirect_url) {
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

        async function sendMessage() {
            const message = messageInput.value.trim();
            if (!message) return;

            // Add user message
            addMessage(message, 'user');
            messageInput.value = '';
            messageInput.style.height = 'auto';

            // Send to backend and stream response
            sendButton.disabled = true;
            showTypingIndicator();

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
                                }
                            } catch (e) {}
                        }
                    }
                }
            } catch (error) {
                removeTypingIndicator();
                addMessage('Error: Could not connect to server', 'assistant');
            }

            sendButton.disabled = false;
            messageInput.focus();
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
                titleValue.className = 'field-value locked';
                if (changed) animateUpdate('titleValue');
            } else {
                titleValue.textContent = 'Untitled';
                titleValue.className = 'field-value pending';
            }

            // Logline
            const loglineValue = document.getElementById('loglineValue');
            if (fields.logline) {
                const changed = !previousState || previousState.fields.logline !== fields.logline;
                loglineValue.textContent = fields.logline;
                loglineValue.className = 'field-value locked';
                if (changed) animateUpdate('loglineValue');
            } else {
                loglineValue.textContent = "What's the one-sentence pitch?";
                loglineValue.className = 'field-value pending';
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
                    card.className = 'character-card';

                    const escapedName = (char.name || '').replace(/'/g, "\\'").replace(/"/g, '&quot;');
                    card.innerHTML = `
                        <div class="character-card-header">
                            <span class="name editable" data-field="character_name" data-old-name="${escapedName}">${char.name || 'Unnamed'}</span>
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
        }
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    import uvicorn
    print("Starting Lizzy IDEATE web interface...")
    print("Open http://localhost:8888 in your browser")
    uvicorn.run(app, host="0.0.0.0", port=8888, log_level="warning")
