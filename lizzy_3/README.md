# lizzy_3

A unified, chat-based screenwriting assistant for romantic comedies.

## Origin

lizzy_3 is the next evolution of LIZZY, a framework originally built as the practical implementation of a master's thesis:

> **"Automating the Screenplay: The Creative and Technical Viability of AI in Screenwriting"**
> Eliana Jansick, M.A.

The thesis argued that AI can function as a collaborative screenwriting partner when built with:
- **Structured prompt engineering** (not fine-tuning)
- **Vector + graph-based retrieval** (LightRAG) for domain expertise
- **Memory retention** for narrative coherence
- **Iterative feedback loops** (Kozmetsky's CIM framework)

The original LIZZY proved the concept. lizzy_3 takes the lessons learned and builds something more streamlined — one continuous conversation instead of four separate phases.

## Vision

One continuous conversation that guides writers from initial idea through finished screenplay. No phase switching, no CLI juggling — just a collaborative chat with Syd and the expert panel.

## Architecture

### How It Works

Syd (the LLM) has two knowledge sources:

```
┌─────────────────┐                      ┌─────────────────┐
│    LightRAG     │                      │    Hindsight    │
│                 │                      │                 │
│  DOMAIN EXPERT  │                      │   SYD'S BRAIN   │
│   (shared)      │                      │  (per-project)  │
│                 │                      │                 │
│ Craft books     │                      │ What Syd knows  │
│ Plays           │         ┌──────────▶ │ going into the  │
│ Scripts         │         │            │ conversation    │
└────────┬────────┘         │            └────────┬────────┘
         │                  │                     │
         │            ┌─────┴───────┐             │
         │            │   SQLite    │             │
         │            │ (notebook)  │             │
         │            │             │             │
         │            │ Characters  │             │
         │            │ Scenes      │             │
         │            │ Notes       │             │
         │            └─────────────┘             │
         │              manual edit               │
         │                                        │
         └──────────────┬─────────────────────────┘
                        ▼
                  ┌───────────┐
                  │    LLM    │
                  │   (Syd)   │
                  └───────────┘
```

| Component | What it is | Example |
|-----------|------------|---------|
| **LightRAG** | Domain expertise (shared across all projects) | "Meet-cutes need tension + chemistry" |
| **Hindsight** | Syd's brain (per-project memory) | "User prefers witty banter, hates big misunderstandings" |
| **SQLite** | The notebook (structured editor for Hindsight) | `Emma: 32, divorce attorney` |

### SQLite → Hindsight

SQLite is a **structured editor** for what Hindsight knows. Instead of typing "Emma is 32, a divorce attorney" into chat, you fill out a form in the outline UI.

```
┌─────────────────┐         ┌─────────────────┐
│     SQLite      │ ──────▶ │    Hindsight    │
│  (manual edit)  │  sync   │  (Syd's brain)  │
└─────────────────┘         └─────────────────┘
                                    ▲
                                    │ learns
                                    │
                            ┌───────────────┐
                            │  Conversation │
                            └───────────────┘
```

Hindsight learns from two sources:
1. **SQLite sync** — manual prep (characters, scenes, notes you define in the UI)
2. **Conversation** — what happens in the room ("user got excited about fake-dating trope")

Each project gets its own Hindsight bank:
- `project-second-chances` → `bank_id="project-1"`
- `project-untitled-romcom` → `bank_id="project-2"`

Switching projects = switching Syd's memory context.

### Project Creation

When a new project is created (with template option enabled), the following data structures are initialized:

```
PROJECT CREATION FLOW
=====================

┌─────────────────────────────────────────────────────────────────────────┐
│                         NEW PROJECT CREATED                             │
│                    (with template checkbox = ON)                        │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           SQLite (data/lizzy.db)                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  PROJECT table                                                          │
│  ├── id, title, logline, genre                                          │
│  └── memory_bank_id: "lizzy-{random}"  ◄── unique per project           │
│                                                                         │
│  WRITER_NOTES table                                                     │
│  └── theme, tone, comps, braindump, outline (empty)                     │
│                                                                         │
│  CHARACTERS table (5 rows)                                              │
│  ├── 1. Protagonist                                                     │
│  ├── 2. Love Interest                                                   │
│  ├── 3. Best Friend                                                     │
│  ├── 4. Obstacle                                                        │
│  └── 5. Mentor                                                          │
│                                                                         │
│  SCENES table (30 rows - romcom beat sheet)                             │
│  ├──  1. Opening Image                                                  │
│  ├──  2. Theme Stated                                                   │
│  ├──  3. Setup - Protagonist's World                                    │
│  ├──  4. Setup - The Flaw                                               │
│  ├──  5. Catalyst / Meet-Cute                                           │
│  ├──  6. Debate - Should They?                                          │
│  ├──  7. Break Into Two                                                 │
│  ├──  8. B Story / Supporting Cast                                      │
│  ├──  9. Fun and Games - Falling                                        │
│  ├── 10. Fun and Games - The Date                                       │
│  ├── 11. Fun and Games - Getting Closer                                 │
│  ├── 12. Midpoint - The Kiss / Declaration                              │
│  ├── 13. Bad Guys Close In - Doubts                                     │
│  ├── 14. Bad Guys Close In - External Pressure                          │
│  ├── 15. Bad Guys Close In - Secrets Surface                            │
│  ├── 16. All Is Lost - The Breakup                                      │
│  ├── 17. Dark Night of the Soul                                         │
│  ├── 18. Break Into Three - Realization                                 │
│  ├── 19. Gathering the Team                                             │
│  ├── 20. Finale - Storming the Castle                                   │
│  ├── 21. Finale - The Grand Gesture                                     │
│  ├── 22. Finale - Confronting the Flaw                                  │
│  ├── 23. Finale - The Choice                                            │
│  ├── 24. Final Image - Together                                         │
│  └── 25-30. Tag Scenes 1-6                                              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    Hindsight Memory (Embedded Postgres)                 │
├─────────────────────────────────────────────────────────────────────────┤
│  Bank: "lizzy-{random}"  ◄── matches project.memory_bank_id             │
│  └── memories: [] (empty on creation, populated during chat)            │
└─────────────────────────────────────────────────────────────────────────┘
```

**Template vs Blank:**

| Option | project | writer_notes | characters | scenes | memory_bank |
|--------|---------|--------------|------------|--------|-------------|
| Template ON | 1 row | 1 row | 5 rows | 30 rows | new ID |
| Template OFF | 1 row | 0 rows | 0 rows | 0 rows | new ID |

**External resources (shared, not per-project):**
- `buckets/books-final/` — Screenwriting craft (10 docs)
- `buckets/scripts-final/` — Romcom screenplays (85 docs)
- `buckets/plays-final/` — Shakespeare (42 docs)

### Syd's Tools (Live Outline Editing)

Syd can edit the outline during conversation via function calling. When the user mentions a character detail or scene idea, Syd saves it automatically.

```python
# api/syd_tools.py - Tool definitions
from api.syd_tools import SYD_TOOLS

# api/syd_tool_executor.py - Executes tools + syncs to Hindsight
from api.syd_tool_executor import SydToolExecutor
```

**Available tools:**

| Tool | Fields |
|------|--------|
| `update_project` | title, logline, genre, description |
| `update_notes` | theme, tone, comps, braindump |
| `create_character` | name, role, description, arc, age, personality, flaw, backstory, relationships |
| `update_character` | character_id + any field above |
| `delete_character` | character_id |
| `create_scene` | scene_number, title, description, characters, tone, beats |
| `update_scene` | scene_id + any field above |
| `delete_scene` | scene_id |

**Example flow:**
```
User: "Emma should be a divorce attorney, 32, kind of cynical about love"

Syd: "Love that - cynicism as her armor."
      ↓
      [calls create_character(name="Emma", age="32", role="protagonist",
                              description="divorce attorney, cynical about love")]
      ↓
      SQLite updated → syncs to Hindsight → UI reflects change
```

### Data Flow

```
User: "What should Emma's meet-cute look like?"
                         │
                         ▼
                   ┌───────────┐
                   │    Syd    │
                   └─────┬─────┘
                         │
         ┌───────────────┴───────────────┐
         ▼                               ▼
    LightRAG                        Hindsight
         │                               │
    "Meet-cutes need               "Emma: divorce attorney
     tension, chemistry,            User wants witty banter
     reversal..."                   Hates big misunderstandings
                                    Ben: wedding planner"
         │                               │
         └───────────────┬───────────────┘
                         ▼
                   ┌───────────┐
                   │  RESPONSE │
                   └───────────┘
    "Given Emma's a divorce attorney and Ben plans
     weddings, their meet-cute could be at the
     courthouse - she's filing papers, he's picking
     up a license. Quick banter about endings vs
     beginnings. No contrived misunderstanding -
     just genuine worldview clash."
```

Hindsight contains both the structured data (from SQLite) and conversation context. Syd queries two sources: LightRAG for domain expertise, Hindsight for project memory.

### System Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         User Interface                       │
│  home │ projects │ workspace │ buckets │ graph │ settings   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Server                          │
│                      api/server.py                           │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
       ┌───────────┐   ┌───────────┐   ┌───────────┐
       │  SQLite   │   │ LightRAG  │   │ Hindsight │
       │(notebook) │   │ (domain)  │   │  (brain)  │
       └─────┬─────┘   └─────┬─────┘   └─────┬─────┘
             │               │               │
             │          books-final          │
             │          plays-final     per-project
             │          scripts-final   memory banks
             │               │               │
             │               └───────┬───────┘
             │                       │
             │                       ▼
             │                 ┌───────────┐
             └────── sync ────▶│    Syd    │◀── conversation
                               │   (LLM)   │     learns
                               └───────────┘
                                     │
                                     ▼ tool calls
                               ┌───────────┐
                               │  SQLite   │ (loop)
                               └───────────┘
```

**The loop:** Syd reads from Hindsight → responds → tool calls update SQLite → syncs to Hindsight

### Conversation Assembly

How a message to Syd gets assembled:

```
1. USER OPENS CHAT
──────────────────
   Load project_id → set bank_id for Hindsight
   Check active_buckets from UI
   Recall project context from Hindsight

2. BUILD SYSTEM PROMPT
──────────────────────
   ┌─────────────────────────────────────────────────┐
   │ PART 1: Syd's identity                          │
   │ "You are Syd, a creative screenwriting          │
   │  partner specializing in romantic comedies..."  │
   │                                                 │
   │ PART 2: Bucket awareness                        │
   │ "You have access to three expert buckets:       │
   │  📚 books-final - USE WHEN: act breaks...       │
   │  🎭 plays-final - USE WHEN: flat dialogue...    │
   │  🎬 scripts-final - USE WHEN: writing scenes..."│
   │                                                 │
   │ PART 3: Active bucket state                     │
   │ "ACTIVE: Structure, Dialogue" or               │
   │ "NO BUCKETS ACTIVE. Ask before querying."       │
   │                                                 │
   │ PART 4: Project context (from Hindsight)        │
   │ "Emma: 34, family lawyer, protagonist           │
   │  Ben: wedding planner, love interest            │
   │  User prefers banter over slapstick"            │
   └─────────────────────────────────────────────────┘

3. ASSEMBLE API REQUEST
───────────────────────
   messages = [
     { role: "system", content: <assembled prompt> },
     ...chat_history,
     { role: "user", content: "current message" }
   ]
   tools = SYD_TOOLS (query_bucket, update_character, etc.)

4. SYD RESPONDS
───────────────
   Option A: Simple response → display to user

   Option B: Suggests bucket → "Want me to pull in scripts-final?"
             User confirms → Syd calls query_bucket tool
             Tool executor queries LightRAG → returns result
             Syd synthesizes response with domain knowledge

   Option C: Updates outline → Syd calls update_character tool
             Tool executor updates SQLite + syncs to Hindsight
             UI updates in real-time
```

**Message flow:**
```
User message
     │
     ▼
┌─────────┐   ┌─────────┐   ┌─────────┐
│Hindsight│──▶│ System  │◀──│ Bucket  │
│(recall) │   │ Prompt  │   │ State   │
└─────────┘   └────┬────┘   └─────────┘
                   │
     ┌─────────────┼─────────────┐
     ▼             ▼             ▼
  Tools       History       Message
     │             │             │
     └─────────────┼─────────────┘
                   ▼
              OpenAI API
                   │
     ┌─────────────┼─────────────┐
     ▼             ▼             ▼
 [tool call]  [response]   [tool call]
     │                          │
     ▼                          ▼
 LightRAG                   SQLite
  query                     update
     │                          │
     └──────────┬───────────────┘
                ▼
           Hindsight
            retain
                │
                ▼
          User sees
          Syd response
```

## Dependencies

| Package | Purpose | Status |
|---------|---------|--------|
| `openai` | LLM API (GPT-4o, tool calling) | v2.14.0 |
| `lightrag-hku` | Knowledge graph RAG for domain expertise | v1.4.9.10 |
| `hindsight-all` | Agent memory system (embedded) | v0.1.16 |
| `fastapi` | Web server (via hindsight) | v0.127.1 |
| `uvicorn` | ASGI server (via hindsight) | v0.40.0 |
| `neo4j` | Graph database driver for entity exploration | v5.0+ |
| `networkx` | GraphML parsing for Neo4j import | v3.0+ |
| `sqlite3` | Structured data storage (built-in) | Python stdlib |

---

## Package Notes

### openai (v2.14.0)

The core LLM interface. We use this for:

- **Chat completions** — Syd and expert conversations
- **Tool/function calling** — Reliable state updates (replaces directive parsing)
- **Streaming** — Real-time response display

Key usage pattern:
```python
from openai import AsyncOpenAI

client = AsyncOpenAI()

response = await client.chat.completions.create(
    model="gpt-4o",
    messages=[...],
    tools=[
        {"type": "function", "function": {"name": "save_character", ...}},
        {"type": "function", "function": {"name": "add_scene", ...}},
    ],
    stream=True
)
```

Tool calling replaces the legacy `[DIRECTIVE:...]` regex parsing — GPT explicitly calls functions when it wants to save state.

---

### lightrag-hku (v1.4.9.10)

Knowledge graph-based RAG. Unlike basic vector search, LightRAG extracts entities and relationships to build a structured graph, then combines graph traversal with vector search.

**Our buckets** (in `./buckets/`):
- `books/` — Screenwriting craft, structure, beats
- `plays/` — Shakespeare's complete works (dialogue, dramatic patterns)
- `scripts/` — Selected romcom screenplays (execution, visual storytelling)

Buckets can be managed via the web UI at `/buckets.html` or the API.

**Query modes:**
- `naive` — Basic search
- `local` — Context-focused retrieval
- `global` — Broad knowledge retrieval
- `hybrid` — Combines local + global (we use this)
- `mix` — Full graph + vector integration

Key usage pattern:
```python
from lightrag import LightRAG, QueryParam

rag = LightRAG(working_dir="./rag_buckets/books")
await rag.initialize_storages()

response = await rag.aquery(
    "How to structure a romantic comedy midpoint?",
    param=QueryParam(mode="hybrid")
)
```

**Latency optimization:** Query all 3 buckets in parallel with `asyncio.gather()`.

---

### hindsight-all (v0.1.16)

Agent memory system that enables learning across conversations. Uses biomimetic memory structures.

**Memory types:**
- **World** — Factual knowledge about the environment
- **Experiences** — The agent's own encounters and outcomes
- **Opinions** — Beliefs with confidence scores
- **Observations** — Derived insights from reflection

**Core operations:**
- **Retain** — Store new information (extracts facts, entities, relationships)
- **Recall** — Retrieve relevant memories (semantic + keyword + graph + temporal)
- **Reflect** — Analyze memories to form new connections and opinions

**How we use it:**
- Remember user preferences across sessions ("prefers witty banter")
- Track project state and decisions ("Emma is the protagonist")
- Learn what works ("user liked the breakfast scene idea")
- Maintain continuity across the entire writing process

Key usage pattern:
```python
from hindsight import HindsightClient, HindsightServer

# Start embedded server
server = HindsightServer()
server.start()

# Use client
client = HindsightClient()

# Store memory
await client.retain("User prefers character-driven comedy over slapstick")

# Retrieve relevant memories
memories = await client.recall("What kind of comedy does the user like?")

# Reflect to form new insights
await client.reflect()
```

---

### neo4j (v5.0+) + networkx (v3.0+)

Graph database integration for exploring entity relationships across knowledge buckets.

**How we use it:**
- Import LightRAG's GraphML files into Neo4j for advanced querying
- Find shortest paths between characters/concepts
- Explore entity neighborhoods (2-hop subgraphs)
- Search entities by type (CHARACTER, LOCATION, THEME, etc.)
- Execute custom Cypher queries for complex analysis

**API Endpoints:**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/graph/sync` | POST | Sync all bucket graphs to Neo4j |
| `/api/graph/sync/{bucket}` | POST | Sync single bucket |
| `/api/graph/data/{bucket}` | GET | Get graph data for visualization |
| `/api/graph/entity` | POST | Query entity + relationships |
| `/api/graph/path` | POST | Find shortest path between entities |
| `/api/graph/neighbors` | POST | Get 2-hop neighborhood |
| `/api/graph/types/{bucket}` | GET | Get entity type stats |
| `/api/graph/entities/{bucket}/{type}` | GET | Get entities by type |
| `/api/graph/cypher` | POST | Execute raw Cypher |

---

### fastapi (v0.127.1) + uvicorn (v0.40.0)

Web framework and ASGI server. Came as dependencies of hindsight-all.

**How we use it:**
- REST API for all data operations
- Static file serving for the frontend (HTML/JS)
- CORS middleware for local development

```bash
# Start server
cd lizzy_3
python -m api.server
# Server runs on http://localhost:8000
```

---

### sqlite3 (Python stdlib)

Local SQLite database for structured project data. Single-user, file-based storage perfect for screenwriting projects.

**Schema** (`api/database.py`):
- `project` — Title, logline, genre, description
- `writer_notes` — Theme, tone, comps, braindump, outline
- `characters` — Name, role, description, arc, age, personality, flaw, backstory, relationships
- `scenes` — Scene number, title, description, characters, tone, beats, canvas_content (JSON)

**Database location:** `data/lizzy.db`

```python
from api.database import db

# Get project
project = db.get_project()

# Update character
db.update_character(1, name="Emma", arc="learns to trust")

# Upsert scene
db.upsert_scene(1, title="Meet Cute", description="They collide at a coffee shop")
```

---

## API Reference

### Bucket Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/buckets` | GET | List all buckets |
| `/api/buckets` | POST | Create new bucket |
| `/api/buckets/{name}` | DELETE | Delete bucket |
| `/api/buckets/{name}/documents` | GET | List documents in bucket |
| `/api/buckets/{name}/documents` | POST | Upload document |
| `/api/buckets/{name}/query` | POST | Query bucket (LightRAG) |
| `/api/buckets/{name}/reset-stuck` | POST | Reset stuck processing docs |

### Outline Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/outline` | GET | Get full outline (project, notes, characters, scenes) |
| `/api/outline/project` | GET | Get project metadata |
| `/api/outline/project` | PUT | Update project metadata |
| `/api/outline/notes` | GET | Get writer notes |
| `/api/outline/notes` | PUT | Update writer notes |
| `/api/outline/characters` | GET | List all characters |
| `/api/outline/characters` | POST | Create character |
| `/api/outline/characters/{id}` | GET | Get character by ID |
| `/api/outline/characters/{id}` | PUT | Update character |
| `/api/outline/characters/{id}` | DELETE | Delete character |
| `/api/outline/scenes` | GET | List all scenes |
| `/api/outline/scenes` | POST | Create scene |
| `/api/outline/scenes/{id}` | GET | Get scene by ID |
| `/api/outline/scenes/{id}` | PUT | Update scene |
| `/api/outline/scenes/{id}` | DELETE | Delete scene |

### Expert Chat Endpoint

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/expert/chat` | POST | Chat with domain expert (bucket + system prompt) |

**Request body:**
```json
{
  "bucket": "plays-final",
  "system_prompt": "You are a story patterns expert...",
  "message": "What makes a great romantic comedy opening?",
  "history": [],
  "rag_mode": "hybrid"
}
```

### Graph Endpoints

See Neo4j section above for graph-related endpoints.

---

## Frontend Pages

| Page | URL | Description |
|------|-----|-------------|
| Home | `/home.html` | Landing page |
| Projects | `/projects.html` | Project list and creation |
| Workspace | `/workspace.html` | Combined workspace: outline (left) + Syd chat (right) + Canvas tab |
| Buckets | `/buckets.html` | Manage LightRAG knowledge buckets |
| Graph | `/graph.html` | Explore Neo4j entity relationships |
| Settings | `/settings.html` | Theme, export, clear data |

**Workspace tabs:**
- Project — Title, logline, genre, description
- Notes — Theme, tone, comps, braindump
- Characters — Character list with add/edit
- Scenes — Scene list with add/edit
- Canvas — Screenplay writing (one scene at a time, proper formatting)

**User flow:** Home → Projects → Workspace (outline + chat + canvas in one view)

---

## Setup

```bash
cd lizzy_3
source venv/bin/activate
python -m api.server
```

**Environment variables** (from `../.env`):
- `OPENAI_API_KEY` — Required for LLM and embeddings
- `NEO4J_URI` — Optional, defaults to `bolt://localhost:7687`
- `NEO4J_USER` — Optional, defaults to `neo4j`
- `NEO4J_PASSWORD` — Optional, defaults to `password`

**Starting Neo4j** (optional, for graph exploration):
```bash
# Docker
docker run -d --name neo4j -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password neo4j:latest

# Or use Neo4j Desktop
```

