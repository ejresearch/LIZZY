"""
Web interface for IDEATE - Conversational Pre-Planning

Run with: python -m lizzy.ideate_web
Then open: http://localhost:8000
"""

import os
import json
import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from .ideate import IdeateSession

app = FastAPI()

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
    <title>Lizzy IDEATE - Syd</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Georgia', 'Times New Roman', serif;
            background: #F5F1E8;
            height: 100vh;
            display: flex;
        }

        .main-container {
            display: flex;
            width: 100%;
            height: 100vh;
            position: relative;
        }

        .chat-container {
            flex: 1;
            background: #FDFBF7;
            display: flex;
            flex-direction: column;
        }

        .sidebar {
            width: 300px;
            background: #F5F1E8;
            color: #2D2D2D;
            padding: 24px;
            overflow-y: auto;
            border-left: 1px solid #E5E1D8;
            transition: width 0.3s ease, padding 0.3s ease;
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
            margin-bottom: 20px;
        }

        .sidebar h2 {
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            color: #6C6C6C;
            margin: 0;
            font-weight: 600;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        }

        .collapse-btn {
            background: none;
            border: none;
            cursor: pointer;
            padding: 4px;
            color: #6C6C6C;
            font-size: 16px;
            transition: color 0.2s;
        }

        .collapse-btn:hover {
            color: #DC3545;
        }

        .expand-btn {
            position: absolute;
            right: 0;
            top: 50%;
            transform: translateY(-50%);
            background: #F5F1E8;
            border: 1px solid #E5E1D8;
            border-right: none;
            border-radius: 8px 0 0 8px;
            padding: 12px 8px;
            cursor: pointer;
            color: #6C6C6C;
            font-size: 14px;
            display: none;
        }

        .expand-btn:hover {
            color: #DC3545;
            background: #FDFBF7;
        }

        .sidebar.collapsed + .expand-btn {
            display: block;
        }

        .sidebar h3 {
            font-size: 12px;
            color: #4A4A4A;
            margin: 20px 0 8px 0;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 8px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        }

        .field-value {
            background: white;
            padding: 10px 12px;
            border-radius: 8px;
            font-size: 12px;
            line-height: 1.5;
            font-family: 'Georgia', serif;
            border: 1px solid #E5E1D8;
        }

        .field-value.empty {
            color: #999999;
            font-style: italic;
        }

        .chat-header {
            padding: 16px 24px;
            background: #DC3545;
            color: white;
            font-size: 18px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 12px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
        }

        .chat-header .logo {
            width: 36px;
            height: 36px;
            background: white;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            color: #DC3545;
            font-size: 16px;
        }

        .chat-header span {
            font-size: 12px;
            color: rgba(255, 255, 255, 0.85);
            font-weight: 400;
            font-style: italic;
        }

        .messages {
            flex: 1;
            overflow-y: auto;
            padding: 24px;
            display: flex;
            flex-direction: column;
            gap: 20px;
        }

        .message {
            display: flex;
            gap: 12px;
            max-width: 85%;
            animation: fadeIn 0.3s ease-in;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .message.user {
            align-self: flex-end;
            flex-direction: row-reverse;
        }

        .message-avatar {
            width: 32px;
            height: 32px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 600;
            flex-shrink: 0;
            font-size: 11px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        }

        .user .message-avatar {
            background: #DC3545;
            color: white;
        }

        .assistant .message-avatar {
            background: #20C997;
            color: white;
        }

        .message-content {
            padding: 14px 18px;
            border-radius: 12px;
            line-height: 1.7;
            white-space: pre-wrap;
            font-size: 15px;
        }

        .user .message-content {
            background: #DC3545;
            color: white;
        }

        .assistant .message-content {
            background: white;
            color: #2D2D2D;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02), 0 4px 12px rgba(0, 0, 0, 0.04);
            border: 1px solid #E5E1D8;
        }

        .input-container {
            padding: 16px 24px;
            border-top: 1px solid #E5E1D8;
            display: flex;
            gap: 12px;
            background: #FDFBF7;
        }

        #messageInput {
            flex: 1;
            padding: 14px 18px;
            border: 1px solid #E5E1D8;
            border-radius: 12px;
            font-size: 15px;
            font-family: 'Georgia', serif;
            resize: none;
            max-height: 120px;
            background: white;
            color: #2D2D2D;
        }

        #messageInput::placeholder {
            color: #999999;
        }

        #messageInput:focus {
            outline: none;
            border-color: #DC3545;
            box-shadow: 0 0 0 4px rgba(220, 53, 69, 0.15);
        }

        #sendButton {
            padding: 14px 24px;
            background: #DC3545;
            color: white;
            border: none;
            border-radius: 12px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease-out;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        }

        #sendButton:hover {
            background: #C82333;
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(220, 53, 69, 0.3);
        }

        #sendButton:disabled {
            background: #E5E1D8;
            color: #999999;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }

        .typing-indicator {
            display: flex;
            gap: 4px;
            padding: 12px 16px;
        }

        .typing-indicator span {
            width: 8px;
            height: 8px;
            background: #9ca3af;
            border-radius: 50%;
            animation: bounce 1.4s infinite ease-in-out;
        }

        .typing-indicator span:nth-child(1) { animation-delay: -0.32s; }
        .typing-indicator span:nth-child(2) { animation-delay: -0.16s; }

        @keyframes bounce {
            0%, 80%, 100% { transform: scale(0); }
            40% { transform: scale(1); }
        }

        .status-badge {
            display: inline-block;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 9px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-weight: 600;
        }

        .status-locked {
            background: #20C997;
            color: white;
        }

        .status-pending {
            background: #4D4D4D;
            color: #999999;
        }

        .sidebar h3:first-of-type {
            margin-top: 0;
        }

        .typing-indicator span {
            background: #DC3545;
        }
    </style>
</head>
<body>
    <div class="main-container">
        <div class="chat-container">
            <div class="chat-header">
                <div class="logo">S</div>
                <div>
                    Syd
                    <span>Your romcom writing partner</span>
                </div>
            </div>

            <div class="messages" id="messages">
                <div class="message assistant">
                    <div class="message-avatar">Syd</div>
                    <div class="message-content">Hi! I'm Syd. Got an idea for a romantic comedy?

Tell me anything - a character, a situation, a vibe.</div>
                </div>
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
                <button class="collapse-btn" onclick="toggleSidebar()" title="Collapse">◀</button>
            </div>

            <h3>Title <span class="status-badge status-pending" id="titleStatus">pending</span></h3>
            <div class="field-value empty" id="titleValue">Not set yet</div>

            <h3>Logline <span class="status-badge status-pending" id="loglineStatus">pending</span></h3>
            <div class="field-value empty" id="loglineValue">Not set yet</div>

            <h3>Characters</h3>
            <div class="field-value empty" id="charactersValue">None defined yet</div>

            <h3>Outline</h3>
            <div class="field-value empty" id="outlineValue">0 beats</div>

            <h3>Beats</h3>
            <div class="field-value empty" id="beatsValue">0 scenes</div>

            <h3>Notebook</h3>
            <div class="field-value empty" id="notebookValue">Empty</div>
        </div>
        <button class="expand-btn" id="expandBtn" onclick="toggleSidebar()" title="Expand">▶</button>
    </div>

    <script>
        const messagesDiv = document.getElementById('messages');
        const messageInput = document.getElementById('messageInput');
        const sendButton = document.getElementById('sendButton');
        const sidebar = document.getElementById('sidebar');
        const expandBtn = document.getElementById('expandBtn');

        function toggleSidebar() {
            sidebar.classList.toggle('collapsed');
            expandBtn.style.display = sidebar.classList.contains('collapsed') ? 'block' : 'none';
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

        sendButton.addEventListener('click', sendMessage);

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
                                    content.textContent += parsed.content;
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
            avatar.textContent = 'Syd';

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
                <div class="message-avatar">Syd</div>
                <div class="message-content typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            `;
            messagesDiv.appendChild(indicator);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }

        function removeTypingIndicator() {
            const indicator = document.getElementById('typingIndicator');
            if (indicator) indicator.remove();
        }

        function updateSidebar(state) {
            const fields = state.fields;
            const locked = state.locked;

            // Title
            const titleValue = document.getElementById('titleValue');
            const titleStatus = document.getElementById('titleStatus');
            if (fields.title) {
                titleValue.textContent = fields.title;
                titleValue.classList.remove('empty');
                titleStatus.textContent = 'locked';
                titleStatus.className = 'status-badge status-locked';
            }

            // Logline
            const loglineValue = document.getElementById('loglineValue');
            const loglineStatus = document.getElementById('loglineStatus');
            if (fields.logline) {
                loglineValue.textContent = fields.logline;
                loglineValue.classList.remove('empty');
                loglineStatus.textContent = 'locked';
                loglineStatus.className = 'status-badge status-locked';
            }

            // Characters
            const charactersValue = document.getElementById('charactersValue');
            if (fields.characters && fields.characters.length > 0) {
                const names = fields.characters.map(c => c.name || 'Unnamed').join(', ');
                charactersValue.textContent = names;
                charactersValue.classList.remove('empty');
            }

            // Outline
            const outlineValue = document.getElementById('outlineValue');
            if (fields.outline && fields.outline.length > 0) {
                outlineValue.textContent = fields.outline.length + ' beats';
                outlineValue.classList.remove('empty');
            }

            // Beats
            const beatsValue = document.getElementById('beatsValue');
            if (fields.beats && fields.beats.length > 0) {
                beatsValue.textContent = fields.beats.length + ' scenes';
                beatsValue.classList.remove('empty');
            }

            // Notebook
            const notebookValue = document.getElementById('notebookValue');
            if (fields.notebook && fields.notebook.length > 0) {
                notebookValue.textContent = fields.notebook.length + ' ideas';
                notebookValue.classList.remove('empty');
            }
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
