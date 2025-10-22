# Prompt Studio Chat UI ✨💬

**Simple, functional chat interface with visual block feedback**

---

## 🎯 What It Is

A **chat-first web interface** where you type naturally and see the blocks being built in real-time.

```
Type → AI Parses → Blocks Built → Visual Feedback → Copy/Save
```

**No drag-and-drop complexity. Just chat!**

---

## 🚀 Quick Start

### Start the Server

```bash
./start_prompt_studio.sh

# Or manually:
python3 prompt_studio_server.py
```

###Open Your Browser

```
http://localhost:8001
```

That's it! Start chatting.

---

## 💬 How To Use

### 1. Select Your Project

Choose from the dropdown at the top (auto-loaded from `projects/` directory)

### 2. Type Naturally

Examples:
- "Help me with scene 1, what do books say about openings?"
- "Jenny in scene 4 dealing with disappointment, check scripts"
- "Show me the wedding scene with all three experts"

### 3. See Blocks Build

The right panel shows:
- **Blocks Used**: Which blocks were created
- **Prompt Preview**: The assembled prompt
- **Stats**: Character count, execution time

### 4. Take Action

- **📋 Copy**: Copy prompt to clipboard
- **💾 Save**: Download as .txt file

---

## 🎨 UI Layout

```
┌─────────────────────────────────────────────────────────┐
│  ✨ PROMPT STUDIO                                       │
│  Chat-based prompt composer                            │
├─────────────────────────────────────────────────────────┤
│  Select Project: [The Proposal 2 0 ▼]                  │
├──────────────────────────┬──────────────────────────────┤
│  💬 CHAT (2/3 width)     │  🧩 BLOCKS (1/3 width)      │
│                          │                              │
│  🤖: Hi! Tell me what    │  Blocks Used:               │
│      you're working on   │  1. Scene 1                 │
│                          │  2. Books Query             │
│  👤: Scene 1, books      │                              │
│      expert              │  📄 Prompt Preview:         │
│                          │  SCENE 1: ...               │
│  🤖: ✅ Built with       │  [TRUNCATED]                │
│      2 blocks            │                              │
│                          │  [📋 Copy] [💾 Save]        │
│  [What are you working   │                              │
│   on?  ] [Send]          │  555 chars • 0.44ms         │
└──────────────────────────┴──────────────────────────────┘
```

---

## 🎓 Example Session

### Example 1: Scene Lookup

**You type:**
> "Show me scene 1"

**AI responds:**
> ✅ Built your prompt with 2 blocks

**Blocks panel shows:**
```
1. Section header: 'SCENE 1'
2. Scene 1 data (title, description, characters)
```

**Prompt preview:**
```
================================================================================
                                SCENE 1
================================================================================

SCENE 1: x
Description: x
Characters: ...
```

---

### Example 2: Expert Consultation

**You type:**
> "Help with scene 1, what do books say about romantic comedy openings?"

**AI responds:**
> ✅ Built your prompt with 6 blocks
> Detected: Scene: scene 1 • Buckets: books • Topic: romantic comedy openings

**Blocks panel shows:**
```
1. Section header: 'SCENE 1'
2. Scene 1 data
3. Section header: 'WORKING ON'
4. Text: 'romantic comedy openings'
5. Section header: 'EXPERT GUIDANCE'
6. Books bucket query: 'romantic comedy openings...'
```

---

### Example 3: Character Focus

**You type:**
> "Jenny in scene 4 dealing with disappointment, check scripts bucket"

**AI detects:**
- Scene: 4
- Character: Jenny
- Topic: dealing with disappointment
- Bucket: scripts

**Blocks built:**
```
1. Section header: 'SCENE 4'
2. Scene 4 data
3. Section header: 'CHARACTERS'
4. Text: Jenny's bio
5. Section header: 'WORKING ON'
6. Text: 'dealing with disappointment'
7. Section header: 'EXPERT GUIDANCE'
8. Scripts query: 'dealing with disappointment focusing on Jenny'
```

---

## 🔧 Technical Details

### Stack

**Backend:**
- FastAPI (Python web framework)
- AIBlockComposer (our natural language engine)
- SQLite (project data)
- LightRAG (knowledge buckets)

**Frontend:**
- Pure HTML + JavaScript (no build step!)
- Tailwind CSS (via CDN)
- Vanilla JS (simple and fast)

**No React, no npm, no build process - just works!**

###API Endpoints

```
GET  /                  - Serve chat UI
POST /api/chat          - Process chat message
GET  /api/projects      - List available projects
GET  /api/blocks        - List available block types
GET  /api/health        - Health check
GET  /docs              - API documentation
```

### Chat API

**Request:**
```json
{
  "project_name": "the_proposal_2_0",
  "message": "Help with scene 1, check books",
  "session_id": "optional-uuid"
}
```

**Response:**
```json
{
  "session_id": "abc-123",
  "parsed_entities": {
    "scene_reference": "scene 1",
    "buckets": ["books"],
    "intent": "get_inspiration"
  },
  "blocks_used": [
    "Section header: 'SCENE 1'",
    "Scene 1 data",
    "Books bucket query..."
  ],
  "prompt": "SCENE 1: ...",
  "total_chars": 555,
  "execution_time_ms": 0.44
}
```

---

## 🎨 UI Features

### Chat Interface

- **Real-time typing indicators**
- **Message history**
- **User (blue) vs AI (purple) messages**
- **Entity detection feedback** (shows what AI understood)
- **Smooth scrolling**
- **Keyboard shortcuts** (Enter to send)

### Visual Block Feedback

- **Numbered blocks** (1, 2, 3...)
- **Hover effects** (cards lift on hover)
- **Color-coded** (purple theme)
- **Descriptions** (what each block does)

### Prompt Preview

- **Truncated view** (first 500 chars)
- **Full text on save**
- **Character count**
- **Execution time**
- **Copy to clipboard**
- **Save to file**

---

## 📊 Performance

### Typical Response Times

- **Frontend**: <50ms (instant feedback)
- **AI Parsing**: ~500-1000ms (GPT-4o-mini)
- **SQL Lookup**: <1ms
- **Block Building**: <1ms
- **Block Execution**: 1-5ms (without RAG)
- **RAG Queries**: 500-2000ms (if buckets exist)

**Total**: ~1-3 seconds for full cycle

### Cost

- **AI Parsing**: ~$0.0001 per message
- **RAG Queries**: ~$0.001 per query

**Very affordable for interactive use!**

---

## 🔮 Future Enhancements

### Planned Features

1. **Session Memory** - Remember conversation context
2. **Multi-turn Refinement** - "Also add scripts bucket"
3. **Smart Suggestions** - AI suggests next actions
4. **Query History** - Rerun previous queries
5. **Export Options** - Send directly to brainstorm modules
6. **Theme Toggle** - Dark mode
7. **Voice Input** - Speak your queries

---

## 🛠️ Development

### Running Locally

```bash
# Start server
python3 prompt_studio_server.py

# Visit in browser
open http://localhost:8001
```

### Modifying the UI

Edit `prompt_studio_ui.html` - no build step needed!

Changes refresh on page reload.

### Modifying the Backend

Edit `prompt_studio_server.py` - restart server to see changes.

### API Documentation

Visit `http://localhost:8001/docs` for interactive API docs (Swagger UI)

---

## 📁 Files

```
prompt_studio_server.py      # FastAPI backend (177 lines)
prompt_studio_ui.html         # Chat UI (350+ lines)
start_prompt_studio.sh        # Launcher script

lizzy/prompt_studio/
├── ai_composer.py            # Natural language engine
├── blocks/                   # 14 block types
├── engine.py                 # Prompt assembly
└── registry.py               # Block discovery
```

---

## ✅ What's Working

- ✅ **Chat interface** - Beautiful, responsive
- ✅ **Natural language parsing** - AI understands your input
- ✅ **SQL lookup** - Finds scenes/characters automatically
- ✅ **Block building** - Creates blocks from entities
- ✅ **Visual feedback** - Shows blocks being built
- ✅ **Prompt preview** - See the assembled prompt
- ✅ **Copy/Save** - Export your prompts
- ✅ **Project selection** - Choose from existing projects
- ✅ **Real-time updates** - Smooth, responsive UI

---

## 🎯 Use Cases

### Use Case 1: Quick Scene Lookup

**Old way:**
```python
blocks = [SceneBlock(scene_number=5)]
prompt = assemble_prompt(blocks, "my_project")
```

**New way:**
```
Open browser → Type "scene 5" → Get prompt
```

**Time saved:** ~2 minutes → ~5 seconds

---

### Use Case 2: Expert Consultation

**Old way:**
```python
blocks = [
    SceneBlock(5),
    BooksQueryBlock("romantic tension"),
]
prompt = assemble_prompt(blocks, "my_project")
```

**New way:**
```
Type: "scene 5, what do books say about romantic tension?"
```

**Time saved:** ~3 minutes → ~10 seconds

---

### Use Case 3: Iterative Refinement

**Future capability:**
```
You: "scene 5, books expert"
AI: [builds prompt]
You: "also add scripts"
AI: [adds scripts block, updates prompt]
You: "perfect, copy it"
```

**Conversational workflow!**

---

## 📚 Related Docs

- **PROMPT_STUDIO_ARCHITECTURE.md** - Block system design
- **AI_COMPOSER.md** - Natural language engine
- **PROMPT_STUDIO_IMPLEMENTATION.md** - Implementation details

---

## 🎉 Summary

**Chat UI** is a simple, functional interface that makes Prompt Studio **conversational**:

1. **Type naturally** - No code required
2. **See blocks** - Visual feedback
3. **Get prompt** - Assembled automatically
4. **Copy/Save** - Take action

**No drag-and-drop complexity. Just chat!**

---

## 🚀 Try It Now

```bash
# Start the server
./start_prompt_studio.sh

# Open browser
open http://localhost:8001

# Start chatting!
```

---

**The easiest way to compose prompts from your screenplay data!**
