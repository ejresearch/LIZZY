# lizzy_3

A screenwriting assistant for romantic comedies. One conversation from idea to screenplay.

## Origin

Built as the practical implementation of:

> **"Automating the Screenplay: The Creative and Technical Viability of AI in Screenwriting"**
> Eliana Jansick, M.A.

The thesis argued AI works as a collaborative screenwriting partner when built with structured prompts, knowledge retrieval, and memory. The original LIZZY proved the concept. lizzy_3 streamlines it into one continuous conversation.

---

## Quick Start

```bash
cd lizzy_3
source venv/bin/activate
pip install -r requirements.txt
python -m api.server
```

Open `http://localhost:8000/home.html`

**Required:** `OPENAI_API_KEY` in environment or `../.env`

---

## Features

| Feature | Description |
|---------|-------------|
| **Syd** | AI writing partner with domain expertise and project memory |
| **Knowledge Buckets** | RAG-powered expertise (screenwriting books, plays, scripts) |
| **Outline Editor** | Characters, scenes, notes - structured story bible |
| **Canvas** | Screenplay formatting (sluglines, action, dialogue) |
| **Tool Use** | Syd can edit your outline during conversation |
| **Memory** | Per-project memory that persists and learns |
| **Reflection** | Analyzes sessions to form insights about your preferences |

---

## Workspace

```
┌─────────────────────────────────────────────────────────────┐
│  lizzy   [Title]                    [Save]  Projects  ...   │
├─────────────────────────────────────────────────────────────┤
│  Project │ Notes │ Characters │ Scenes │ Canvas             │
│  ────────────────────────────────────   ┌─────────────────┐ │
│                                         │ Chat with Syd   │ │
│  [Outline Forms]                        │ [Books] [Plays] │ │
│  [Character Modal]                      │ [Scripts]       │ │
│  [Scene List]                           │                 │ │
│  [Canvas Editor]                        │ Conversations ▾ │ │
│                                         └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**Tabs:** Project metadata, writer notes, characters (add/edit/delete), scenes (reorder, delete), canvas (screenplay editor)

**Chat:** Toggle knowledge buckets, conversation history persists, Syd can edit outline via tools

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        WORKSPACE UI                          │
│         Outline Editor  │  Canvas  │  Chat with Syd          │
└────────────────────────────────┬─────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────┐
│                      FastAPI Server                          │
└──────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│     SQLite      │  │    LightRAG     │  │   Hindsight     │
│   (notebook)    │  │    (domain)     │  │    (memory)     │
│                 │  │                 │  │                 │
│ • Project       │  │ • books-final   │  │ • Per-project   │
│ • Characters    │  │ • plays-final   │  │ • Retain/Recall │
│ • Scenes        │  │ • scripts-final │  │ • Reflect       │
│ • Conversations │  │                 │  │                 │
└────────┬────────┘  └────────┬────────┘  └────────┬────────┘
         │                    │                    │
         └────────────────────┴────────────────────┘
                              │
                              ▼
                        ┌───────────┐
                        │    Syd    │ ← GPT-4o + Tools
                        │   (LLM)   │
                        └───────────┘
```

### Core Concepts

| Component | Role | Example |
|-----------|------|---------|
| **SQLite** | Structured data (your notebook) | `Emma: 32, divorce attorney, protagonist` |
| **LightRAG** | Domain expertise (shared) | "Meet-cutes need tension + chemistry" |
| **Hindsight** | Project memory (per-project) | "User prefers witty banter" |
| **Syd** | AI partner with tools | Creates characters, edits scenes via chat |

### How Syd Learns

```
User: "Emma should be a divorce attorney, cynical about love"
                              │
                              ▼
                     Syd responds + uses tool
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
         SQLite          Hindsight         UI Update
    (create_character)    (retain)      (list refreshes)
```

Hindsight learns from:
1. **Outline sync** — Manual edits in the UI
2. **Conversation** — What you discuss with Syd
3. **Reflection** — End-of-session analysis

---

## Tech Stack

| Package | Purpose |
|---------|---------|
| `openai` | LLM (GPT-4o, tool calling) |
| `lightrag-hku` | Knowledge graph RAG |
| `hindsight-all` | Agent memory (includes FastAPI, uvicorn) |
| `neo4j` | Graph exploration (optional) |
| `sqlite3` | Local data storage |

---

## API Reference

### Chat
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/expert/chat` | POST | Chat with Syd (RAG + memory + tools) |
| `/api/reflect` | POST | Trigger memory reflection |

### Outline
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/outline` | GET | Full outline (project, notes, characters, scenes) |
| `/api/outline/project` | GET/PUT | Project metadata |
| `/api/outline/notes` | GET/PUT | Writer notes |
| `/api/outline/characters` | GET/POST | List/create characters |
| `/api/outline/characters/{id}` | GET/PUT/DELETE | Character by ID |
| `/api/outline/scenes` | GET/POST | List/create scenes |
| `/api/outline/scenes/{id}` | GET/PUT/DELETE | Scene by ID |
| `/api/outline/scenes/{id}/reorder` | PUT | Move scene |

### Conversations
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/conversations` | GET/POST | List/create chats |
| `/api/conversations/{id}` | GET/PUT/DELETE | Chat by ID |

### Buckets
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/buckets` | GET/POST | List/create buckets |
| `/api/buckets/{name}` | DELETE | Delete bucket |
| `/api/buckets/{name}/documents` | GET/POST | Bucket documents |
| `/api/buckets/{name}/query` | POST | Query bucket (LightRAG) |

---

## Project Template

New projects can include a 30-scene romcom beat sheet:

1. Opening Image → 5. Meet-Cute → 12. Midpoint → 16. All Is Lost → 21. Grand Gesture → 24. Final Image

Plus 5 character slots: Protagonist, Love Interest, Best Friend, Obstacle, Mentor

---

## What's Next

- [ ] Export canvas to FDX/PDF
- [ ] Multi-project dashboard
- [ ] Voice mode for brainstorming
