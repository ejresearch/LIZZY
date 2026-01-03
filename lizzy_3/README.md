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
| **Outline Editor** | Characters, acts, scenes - structured story bible |
| **3-Act Structure** | Organize scenes into acts with collapsible sections |
| **Canvas** | Screenplay formatting (sluglines, action, dialogue) |
| **Tool Use** | Syd can edit your outline during conversation |
| **Memory Tab** | View what Syd remembers about your project |
| **Reflection** | Analyzes sessions to form insights about your preferences |

---

## Workspace

```
┌─────────────────────────────────────────────────────────────┐
│  lizzy   [Title]              ● ● ● ●   [Save]  Projects    │
├─────────────────────────────────────────────────────────────┤
│  Idea │ Project │ Notes │ Characters │ Scenes │ Canvas │ Memory
│  ─────────────────────────────────────  ┌─────────────────┐ │
│                                         │ Chat with Syd   │ │
│  [Outline Forms]                        │ [Books] [Plays] │ │
│  [Character Cards]                      │ [Scripts]       │ │
│  [Acts → Scenes]                        │ ✎ ✕ + Convos ▾  │ │
│  [Canvas Editor]                        │                 │ │
│  [Memory Viewer]                        └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**Tabs:**
- **Idea** - Quick capture for initial sparks
- **Project** - Title, logline, description
- **Notes** - Theme, tone, comps, braindump
- **Characters** - Add/edit/delete with detailed profiles
- **Scenes** - 3-act structure with collapsible acts
- **Canvas** - Write screenplay content per scene
- **Memory** - View Syd's memory about your project

**Chat:** Toggle knowledge buckets, rename/delete conversations, Syd edits outline via tools

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
│ • Acts/Scenes   │  │ • scripts-final │  │ • Reflect       │
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
| `/api/outline` | GET | Full outline (project, notes, characters, acts, scenes) |
| `/api/outline/project` | GET/PUT | Project metadata |
| `/api/outline/notes` | GET/PUT | Writer notes |
| `/api/outline/characters` | GET/POST | List/create characters |
| `/api/outline/characters/{id}` | GET/PUT/DELETE | Character by ID |
| `/api/outline/acts` | GET/POST | List/create acts |
| `/api/outline/acts/{id}` | GET/PUT/DELETE | Act by ID |
| `/api/outline/scenes` | GET/POST | List/create scenes |
| `/api/outline/scenes/{id}` | GET/PUT/DELETE | Scene by ID |
| `/api/outline/scenes/{id}/act` | PUT | Assign scene to act |

### Conversations
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/conversations` | GET/POST | List/create chats |
| `/api/conversations/{id}` | GET/PUT/DELETE | Chat by ID (rename, delete) |

### Memory (Hindsight)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/memory/banks` | GET | List all memory banks |
| `/api/memory/banks/{id}/memories` | GET | List memories in a bank |
| `/api/memory/banks/{id}/entities` | GET | List entities (characters, concepts) |
| `/api/memory/banks/{id}/stats` | GET | Memory bank statistics |

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
