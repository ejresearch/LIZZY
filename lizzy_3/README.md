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

Three-layer data architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                         User Interface                       │
│  home │ projects │ outline │ query │ buckets │ settings     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Server                          │
│                      api/server.py                           │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐   ┌─────────────────┐   ┌─────────────────┐
│    SQLite     │   │    LightRAG     │   │    Hindsight    │
│  (Structured) │   │  (Domain RAG)   │   │    (Memory)     │
├───────────────┤   ├─────────────────┤   ├─────────────────┤
│ Project data  │   │ books-final     │   │ World network   │
│ Characters    │   │ plays-final     │   │ Experience      │
│ Scenes        │   │ scripts-final   │   │ Opinions        │
│ Writer notes  │   │                 │   │ Observations    │
└───────────────┘   └─────────────────┘   └─────────────────┘
        │                     │                     │
        │                     ▼                     │
        │           ┌─────────────────┐             │
        │           │      Neo4j      │             │
        │           │ (Graph Explore) │             │
        │           └─────────────────┘             │
        │                                           │
        └───────────────────────────────────────────┘
```

**Expert Pattern:** `LLM + System Prompt + RAG Bucket = Expert`

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
- `scenes` — Scene number, title, description, characters, tone, beats

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
| Outline | `/outline.html` | Project editor (tabbed: Project, Notes, Characters, Scenes) |
| Query | `/query.html` | Expert chat interface (Books, Plays, Scripts experts) |
| Buckets | `/buckets.html` | Manage LightRAG knowledge buckets |
| Graph | `/graph.html` | Explore Neo4j entity relationships |
| Settings | `/settings.html` | Theme, export, clear data |

**User flow:** Home → Projects → Outline → (Query for expert help)

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

