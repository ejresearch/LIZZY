"""
Web interface for IDEATE - Conversational Pre-Planning

Run with: python -m lizzy.ideate_web
Then open: http://localhost:8000
"""

import os
import json
import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from .ideate import IdeateSession

app = FastAPI()

# Serve static files
STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Global session (for demo - in production use session management)
session = None

@app.on_event("startup")
async def startup():
    global session
    session = IdeateSession(debug=False)
    print("Session initialized")

    # TEMPORARILY DISABLED: Pre-initialize all buckets
    # print("Initializing RAG buckets...")
    # for bucket_name in ["scripts", "books", "plays"]:
    #     rag = session._get_rag_instance(bucket_name)
    #     if rag:
    #         await rag.initialize_storages()
    #         session._initialized_buckets.add(bucket_name)
    #         print(f"  {bucket_name} bucket ready")
    # print("All buckets initialized")
    print("Buckets disabled - faster startup")

@app.get("/", response_class=HTMLResponse)
async def get_chat():
    return HTML_TEMPLATE

@app.post("/chat")
async def chat(request: Request):
    """Process a message and return streamed response."""
    data = await request.json()
    message = data.get("message", "")

    if not message:
        return {"error": "No message provided"}

    async def generate():
        try:
            print(f"Processing message: {message[:50]}...")
            full_response = ""
            async for chunk in session.process_message_stream(message):
                full_response += chunk
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"

            print(f"Response complete: {len(full_response)} chars")

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

@app.get("/state")
async def get_state():
    """Get current session state."""
    if session:
        return session.get_state()
    return {"error": "No session"}

@app.post("/save")
async def save_to_database(request: dict):
    """Save current session to database."""
    from pathlib import Path

    if not session:
        return {"error": "No session to save"}

    db_path = request.get("db_path")
    if not db_path:
        return {"error": "db_path required"}

    try:
        project_id = session.save_to_database(Path(db_path))
        return {
            "success": True,
            "project_id": project_id,
            "message": "Project saved successfully"
        }
    except Exception as e:
        return {"error": str(e)}

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lizzy IDEATE - Syd v2</title>
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

        /* Progress Tracker */
        .progress-tracker {
            background: white;
            border-radius: 16px;
            padding: 16px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04), 0 8px 24px rgba(0, 0, 0, 0.03);
        }

        .progress-item {
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
            cursor: pointer;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04), 0 8px 24px rgba(0, 0, 0, 0.03);
        }

        .character-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08), 0 12px 32px rgba(0, 0, 0, 0.06);
        }

        .character-card.expanded {
            box-shadow: 0 4px 12px rgba(220, 53, 69, 0.15), 0 12px 32px rgba(0, 0, 0, 0.06);
        }

        .character-card-header {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .character-avatar {
            width: 32px;
            height: 32px;
            border-radius: 10px;
            background: linear-gradient(135deg, #DC3545 0%, #c82333 100%);
            color: white;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 13px;
            font-weight: 600;
            box-shadow: 0 2px 8px rgba(220, 53, 69, 0.3);
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
            background: rgba(0, 0, 0, 0.04);
            padding: 4px 8px;
            border-radius: 6px;
        }

        .character-details {
            display: none;
            margin-top: 14px;
            padding-top: 14px;
            border-top: 1px solid rgba(0, 0, 0, 0.06);
            font-size: 13px;
            line-height: 1.6;
        }

        .character-card.expanded .character-details {
            display: block;
        }

        .character-detail {
            margin-bottom: 10px;
        }

        .character-detail-label {
            font-weight: 600;
            color: #888;
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 4px;
            display: block;
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

        /* Command hints */
        .command-hints {
            padding: 12px 28px;
            background: rgba(0, 0, 0, 0.02);
            font-size: 12px;
            color: #999;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .command-hints span {
            color: #bbb;
        }

        .command-hints code {
            background: white;
            padding: 4px 10px;
            border-radius: 8px;
            font-family: 'SF Mono', 'Menlo', 'Monaco', monospace;
            font-size: 11px;
            color: #666;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
            transition: all 0.2s ease;
        }

        .command-hints code:hover {
            background: #f8f8f8;
            color: #DC3545;
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
            display: flex;
            gap: 10px;
            padding: 20px 26px;
            align-items: center;
            border-radius: 24px;
        }

        .typing-dot {
            width: 14px;
            height: 14px;
            background-color: #DC3545;
            border-radius: 50%;
            animation: pulse-bounce 1.5s infinite ease-in-out;
        }

        .typing-dot:nth-child(2) { animation-delay: 0.2s; }
        .typing-dot:nth-child(3) { animation-delay: 0.4s; }

        @keyframes pulse-bounce {
            0%, 100% {
                transform: translateY(0) scale(1);
                opacity: 0.5;
            }
            50% {
                transform: translateY(-10px) scale(1.15);
                opacity: 1;
            }
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
        }

        /* Save button */
        .save-section {
            margin-top: auto;
            padding-top: 20px;
        }

        #saveButton {
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

        #saveButton:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(32, 201, 151, 0.35);
        }

        #saveButton:disabled {
            background: #e0e0e0;
            color: #999;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }

        .save-status {
            margin-top: 10px;
            font-size: 12px;
            text-align: center;
            color: #20C997;
            font-weight: 500;
        }

        .save-status.error {
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
    </style>
</head>
<body>
    <div class="main-container">
        <div class="chat-container">
            <div class="chat-header">
                <div class="logo">
                    <img src="/static/syd_logo.png" alt="Syd" onerror="this.style.display='none'; this.parentElement.textContent='S';">
                </div>
                <div class="chat-header-text">
                    Syd
                    <span>Your romcom writing partner</span>
                </div>
            </div>

            <div class="messages" id="messages">
                <div class="message assistant">
                    <div class="message-avatar"><img src="/static/syd_logo.png" alt="Syd"></div>
                    <div class="message-content">Hi! I'm Syd. Got an idea for a romantic comedy?

Tell me anything - a character, a situation, a vibe.</div>
                </div>
            </div>

            <div class="command-hints">
                <span>Commands</span> <code>/character</code> <code>/beat</code> <code>/scene</code>
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

            <!-- Phase Indicator -->
            <div class="phase-indicator">
                <div class="phase active" id="phase1">1. Foundation</div>
                <div class="phase" id="phase2">2. Building</div>
            </div>

            <!-- Progress Tracker -->
            <div class="progress-tracker">
                <div class="progress-item pending" id="progressTitle">
                    <span class="icon">&#10003;</span>
                    <span>Title</span>
                </div>
                <div class="progress-item pending" id="progressLogline">
                    <span class="icon">&#10003;</span>
                    <span>Logline</span>
                </div>
                <div class="progress-item pending" id="progressCharacters">
                    <span class="icon">&#10003;</span>
                    <span>Characters</span>
                    <span class="count" id="characterCount">0</span>
                </div>
                <div class="progress-item pending" id="progressBeats">
                    <span class="icon">&#10003;</span>
                    <span>Beat Sheet</span>
                    <span class="count" id="beatCount">0/30</span>
                </div>
            </div>

            <div class="sidebar-section">
                <h3>Title <span class="status-badge status-pending" id="titleStatus">pending</span></h3>
                <div class="field-value empty" id="titleValue">Not set yet</div>
            </div>

            <div class="sidebar-section">
                <h3>Logline <span class="status-badge status-pending" id="loglineStatus">pending</span></h3>
                <div class="field-value empty" id="loglineValue">Not set yet</div>
            </div>

            <div class="sidebar-section">
                <h3>Characters</h3>
                <div class="character-cards" id="charactersContainer">
                    <div class="field-value empty" id="noCharacters">None defined yet</div>
                </div>
            </div>

            <div class="sidebar-section">
                <h3>Notebook <span class="count" id="notebookCount" style="font-size: 11px; color: #aaa; font-weight: 500;">(0)</span></h3>
                <div class="field-value empty" id="notebookValue">Empty</div>
            </div>

            <!-- Save Section -->
            <div class="save-section">
                <button id="saveButton" disabled>Save Project</button>
                <div class="save-status" id="saveStatus"></div>
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
        const saveButton = document.getElementById('saveButton');

        // Track previous state for detecting changes
        let previousState = null;

        function toggleSidebar() {
            sidebar.classList.toggle('collapsed');
            expandBtn.style.display = sidebar.classList.contains('collapsed') ? 'block' : 'none';
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

        // Save button handler
        saveButton.addEventListener('click', async function() {
            saveButton.disabled = true;
            const saveStatus = document.getElementById('saveStatus');
            saveStatus.textContent = 'Saving...';
            saveStatus.className = 'save-status';

            try {
                const response = await fetch('/save', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ db_path: 'lizzy.db' })
                });
                const result = await response.json();

                if (result.success) {
                    saveStatus.textContent = 'Saved!';
                    saveStatus.className = 'save-status';
                } else {
                    saveStatus.textContent = result.error || 'Save failed';
                    saveStatus.className = 'save-status error';
                }
            } catch (e) {
                saveStatus.textContent = 'Connection error';
                saveStatus.className = 'save-status error';
            }

            saveButton.disabled = false;
            setTimeout(() => { saveStatus.textContent = ''; }, 3000);
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
            const fields = state.fields;
            const locked = state.locked;

            // Determine phase
            const phase1 = document.getElementById('phase1');
            const phase2 = document.getElementById('phase2');
            const titleLocked = locked && locked.title;
            const loglineLocked = locked && locked.logline;

            if (titleLocked && loglineLocked) {
                phase1.className = 'phase complete';
                phase2.className = 'phase active';
            } else {
                phase1.className = 'phase active';
                phase2.className = 'phase';
            }

            // Update progress tracker
            const progressTitle = document.getElementById('progressTitle');
            const progressLogline = document.getElementById('progressLogline');
            const progressCharacters = document.getElementById('progressCharacters');
            const progressBeats = document.getElementById('progressBeats');

            progressTitle.className = titleLocked ? 'progress-item complete' : 'progress-item pending';
            progressLogline.className = loglineLocked ? 'progress-item complete' : 'progress-item pending';

            const charCount = fields.characters ? fields.characters.length : 0;
            document.getElementById('characterCount').textContent = charCount;
            progressCharacters.className = charCount >= 3 ? 'progress-item complete' : 'progress-item pending';

            const beatCount = fields.beats ? fields.beats.length : 0;
            document.getElementById('beatCount').textContent = beatCount + '/30';
            progressBeats.className = beatCount >= 30 ? 'progress-item complete' : 'progress-item pending';

            // Title
            const titleValue = document.getElementById('titleValue');
            const titleStatus = document.getElementById('titleStatus');
            if (fields.title) {
                const changed = !previousState || previousState.fields.title !== fields.title;
                titleValue.textContent = fields.title;
                titleValue.classList.remove('empty');
                titleStatus.textContent = 'locked';
                titleStatus.className = 'status-badge status-locked';
                if (changed) animateUpdate('titleValue');
            }

            // Logline
            const loglineValue = document.getElementById('loglineValue');
            const loglineStatus = document.getElementById('loglineStatus');
            if (fields.logline) {
                const changed = !previousState || previousState.fields.logline !== fields.logline;
                loglineValue.textContent = fields.logline;
                loglineValue.classList.remove('empty');
                loglineStatus.textContent = 'locked';
                loglineStatus.className = 'status-badge status-locked';
                if (changed) animateUpdate('loglineValue');
            }

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
                    card.onclick = () => card.classList.toggle('expanded');

                    const initial = (char.name || '?')[0].toUpperCase();
                    const roleColors = {
                        'protagonist': '#DC3545',
                        'love_interest': '#E91E63',
                        'best_friend': '#9C27B0',
                        'obstacle': '#FF5722',
                        'supporting': '#607D8B'
                    };
                    const avatarColor = roleColors[char.role] || '#DC3545';

                    let detailsHtml = '';
                    if (char.personality) detailsHtml += `<div class="character-detail"><span class="character-detail-label">Personality</span><br>${char.personality}</div>`;
                    if (char.flaw) detailsHtml += `<div class="character-detail"><span class="character-detail-label">Flaw</span><br>${char.flaw}</div>`;
                    if (char.arc) detailsHtml += `<div class="character-detail"><span class="character-detail-label">Arc</span><br>${char.arc}</div>`;
                    if (char.backstory) detailsHtml += `<div class="character-detail"><span class="character-detail-label">Backstory</span><br>${char.backstory}</div>`;

                    card.innerHTML = `
                        <div class="character-card-header">
                            <div class="character-avatar" style="background: ${avatarColor}">${initial}</div>
                            <span class="name">${char.name || 'Unnamed'}</span>
                            <span class="role">${(char.role || '').replace('_', ' ')}</span>
                        </div>
                        <div class="character-details">${detailsHtml || '<em>Click to expand when more details are added</em>'}</div>
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
                notebookCount.textContent = '(' + fields.notebook.length + ')';
                // Show last 3 ideas
                const recent = fields.notebook.slice(-3).reverse();
                notebookValue.innerHTML = recent.map(n => '<div style="margin-bottom: 6px; padding-bottom: 6px; border-bottom: 1px solid #E5E1D8;">' + n + '</div>').join('');
                notebookValue.classList.remove('empty');
                if (changed) animateUpdate('notebookValue');
            }

            // Enable save button if we have title or logline
            saveButton.disabled = !(fields.title || fields.logline);

            // Store state for comparison
            previousState = JSON.parse(JSON.stringify(state));
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
