# Lizzy 2.0 - Complete Architecture Map

**Every function, where it lives, how it's routed**

---

## Table of Contents

1. [Core Pipeline Modules](#core-pipeline-modules)
2. [Prompt Studio System](#prompt-studio-system)
3. [Utility Modules](#utility-modules)
4. [Root Scripts (Entry Points)](#root-scripts-entry-points)
5. [Data Flow Diagram](#data-flow-diagram)
6. [Routing Map](#routing-map)

---

## Core Pipeline Modules

### 1. START Module
**Location:** `lizzy/start.py`

**Purpose:** Initialize new screenplay projects

**Classes:**
- `StartModule` - Project creation orchestrator

**Key Functions:**
```python
create_project(name: str)              # Creates project directory structure
_init_database()                       # Creates SQLite schema
_create_directories()                  # Creates folders (projects/, rag_buckets/)
```

**Routing:**
```
User → python3 -m lizzy.start
     → StartModule.create_project()
     → Creates: projects/{name}/{name}.db
                projects/{name}/exports/
```

**Database Schema Created:**
- `scenes` - Scene metadata
- `characters` - Character bios
- `notes` - Writer's notes
- `brainstorm_sessions` - AI brainstorm results
- `drafts` - Full screenplay exports

---

### 2. INTAKE Module
**Location:** `lizzy/intake.py`

**Purpose:** Populate project with story data (30-beat structure)

**Classes:**
- `IntakeModule` - Data collection orchestrator

**Key Functions:**
```python
run()                                  # Main CLI flow
_get_project_metadata()                # Collect title, logline, genre
_get_character_bios()                  # Collect character info
_get_30_scenes()                       # Collect 30-beat structure
_save_to_database()                    # Save all data to SQLite
display_summary()                      # Show what was created
```

**Routing:**
```
User → python3 -m lizzy.intake "Project Name"
     → IntakeModule.run()
     → Rich UI prompts user for input
     → Saves to: projects/{name}/{name}.db
```

**Database Tables Populated:**
- `scenes` (30 rows) - scene_number, title, description, characters, tone
- `characters` (N rows) - name, role, description, arc
- `notes` (N rows) - category, content

---

### 3. BRAINSTORM Module
**Location:** `lizzy/automated_brainstorm.py` + `lizzy/interactive_brainstorm.py`

**Purpose:** Generate scene blueprints using LLMs + RAG

#### 3a. Automated Brainstorm
**Location:** `lizzy/automated_brainstorm.py`

**Classes:**
- `AutomatedBrainstorm` - Fully automated brainstorming

**Key Functions:**
```python
run_session(scene_number, bucket_name)  # Run brainstorm for one scene
_load_scene_data()                      # Get scene from database
_query_rag_bucket()                     # Query LightRAG knowledge graph
_synthesize_with_gpt()                  # Combine context + RAG → blueprint
_save_session()                         # Save to brainstorm_sessions table
```

**Routing:**
```
User → python3 -m lizzy.automated_brainstorm
     → AutomatedBrainstorm.run_session()
     → Loads: scenes table
     → Queries: rag_buckets/{bucket}/
     → Calls: GPT-4o-mini for synthesis
     → Saves to: brainstorm_sessions table
```

#### 3b. Interactive Brainstorm
**Location:** `lizzy/interactive_brainstorm.py`

**Classes:**
- `InteractiveBrainstorm` - Multi-turn chat-based brainstorming

**Key Functions:**
```python
run_session(scene_number)              # Start interactive session
_chat_loop()                           # Multi-turn conversation
_execute_expert_query()                # Query RAG buckets
_get_ai_response()                     # Get GPT response
_display_conversation()                # Rich formatted chat display
```

**Routing:**
```
User → python3 -m lizzy.interactive_brainstorm
     → InteractiveBrainstorm.run_session()
     → Multi-turn chat interface
     → Can query multiple RAG buckets
     → Saves final blueprint to: brainstorm_sessions table
```

---

### 4. WRITE Module
**Location:** `lizzy/write.py`

**Purpose:** Convert blueprints → screenplay prose (700-900 words)

**Classes:**
- `WriteModule` - Draft generation orchestrator
- `SceneContext` (dataclass) - Scene + blueprint + continuity
- `Draft` (dataclass) - Generated prose + metadata

**Key Functions:**
```python
load_scene_context(scene_number)       # Load scene + blueprint + prev/next
generate_draft(context)                # Generate prose with GPT-4o
_build_write_prompt()                  # Assemble rich prompt
save_draft(draft)                      # Save to scene_drafts table
get_all_drafts(scene_number)           # Retrieve all versions
display_draft(draft)                   # Rich formatted output
```

**Routing:**
```
User → python3 -m lizzy.write
     → WriteModule.load_scene_context()
     → Queries: scenes, brainstorm_sessions, scene_drafts
     → Generates: 700-900 word prose with GPT-4o
     → Saves to: scene_drafts table (with versioning)
```

**Database Table:**
- `scene_drafts` - scene_id, content, version, word_count, tokens, cost

---

## Prompt Studio System

### 5. Block System (Phase 1)
**Location:** `lizzy/prompt_studio/blocks/`

**Purpose:** Composable data blocks for prompt assembly

#### Base Block
**Location:** `lizzy/prompt_studio/blocks/base.py`

**Classes:**
- `Block` (ABC) - Abstract base class
- `BlockMetadata` (dataclass) - Execution metadata

**Key Functions:**
```python
execute(project_name, **kwargs) -> str  # Execute block, return data
get_description() -> str                # Human-readable description
validate() -> Tuple[bool, str]          # Check if block is valid
```

#### SQL Blocks (7 types)
**Location:** `lizzy/prompt_studio/blocks/sql_blocks.py`

**Classes:**
1. `SceneBlock` - Fetch scene data
2. `CharacterBiosBlock` - All character bios
3. `WriterNotesBlock` - Writer notes by category
4. `ProjectMetadataBlock` - Project info + story spine
5. `AllScenesBlock` - List all 30 scenes
6. `PreviousSceneBlock` - Previous scene for continuity
7. `NextSceneBlock` - Next scene for foreshadowing

**Each executes:**
```python
execute(project_name) -> str
  → Queries: projects/{project_name}/{project_name}.db
  → Returns: Formatted string with SQL data
```

#### RAG Blocks (4 types)
**Location:** `lizzy/prompt_studio/blocks/rag_blocks.py`

**Classes:**
1. `BooksQueryBlock` - Structure/beat engineering expert
2. `PlaysQueryBlock` - Dialogue/dramatic theory expert
3. `ScriptsQueryBlock` - Visual storytelling expert
4. `MultiExpertQueryBlock` - All 3 experts at once

**Each executes:**
```python
execute(project_name, query) -> str
  → Queries: rag_buckets/{bucket}/ with LightRAG
  → Returns: Formatted string with RAG results
```

#### Static Blocks (3 types)
**Location:** `lizzy/prompt_studio/blocks/static_blocks.py`

**Classes:**
1. `TextBlock` - Plain text
2. `TemplateBlock` - Text with variable substitution
3. `HeaderBlock` - Formatted section headers

**Each executes:**
```python
execute(project_name, **kwargs) -> str
  → Returns: Formatted text
```

---

### 6. Prompt Assembly Engine
**Location:** `lizzy/prompt_studio/engine.py`

**Purpose:** Execute blocks and assemble into prompts

**Classes:**
- `PromptEngine` - Block orchestrator
- `PromptResult` (dataclass) - Assembled prompt + metadata

**Key Functions:**
```python
assemble(blocks, project_name, **kwargs) -> PromptResult
  → Validates each block
  → Executes in order
  → Joins with separator
  → Returns: Final prompt + metadata
```

**Routing:**
```
Blocks → PromptEngine.assemble()
       → Validates each block
       → Executes: block.execute(project_name, **kwargs)
       → Joins outputs
       → Returns: PromptResult(prompt, metadata, timing, chars)
```

---

### 7. Block Registry
**Location:** `lizzy/prompt_studio/registry.py`

**Purpose:** Discover and register all available blocks

**Classes:**
- `BlockRegistry` - Block discovery system

**Key Functions:**
```python
get_all_blocks() -> List[Type[Block]]   # Get all block classes
get_block_by_name(name) -> Type[Block]  # Get specific block class
get_block_info() -> Dict                # Get metadata about all blocks
```

**Routing:**
```
Import → BlockRegistry auto-discovers all Block subclasses
       → Registers in internal dict
       → Available for lookup by name
```

---

### 8. AI Composer (Phase 2)
**Location:** `lizzy/prompt_studio/ai_composer.py`

**Purpose:** Natural language → Blocks → Prompt

**Classes:**
- `EntityParser` - Extract entities from user input
- `SQLLookup` - Find scenes/characters in database
- `BlockBuilder` - Convert entities → blocks
- `AIBlockComposer` - Orchestrates entire flow
- `ComposeResult` (dataclass) - Result with parsed entities

**Key Functions:**

#### EntityParser
```python
parse(user_input, project_name) -> Dict
  → Calls: GPT-4o-mini with extraction prompt
  → Returns: {scene_reference, character_names, topic, buckets, intent}
```

#### SQLLookup
```python
find_scene_number(reference) -> int     # "scene 4" → 4
find_character_names(names) -> List     # Fuzzy match character names
```

#### BlockBuilder
```python
build(parsed_entities) -> List[Block]
  → Converts entities to appropriate blocks
  → Returns: List of instantiated blocks
```

#### AIBlockComposer
```python
compose(user_input) -> ComposeResult
  → EntityParser: user_input → entities
  → SQLLookup: entities → concrete data
  → BlockBuilder: entities → blocks
  → PromptEngine: blocks → prompt
  → Returns: ComposeResult with everything
```

**Routing:**
```
User: "Help me with scene 4, check scripts"
     ↓
EntityParser → GPT-4o-mini
     ↓ {scene_reference: "4", buckets: ["scripts"]}
SQLLookup → Database
     ↓ scene_number: 4
BlockBuilder
     ↓ [SceneBlock(4), ScriptsQueryBlock("scene 4")]
PromptEngine
     ↓ "SCENE 4: Coffee Shop\n\n[scripts expert response]"
User ← Final prompt
```

---

### 9. Executor (Phase 4)
**Location:** `lizzy/prompt_studio/executor.py`

**Purpose:** Execute prompts with LLMs

**Classes:**
- `PromptExecutor` - General prompt execution
- `BrainstormExecutor` - Specialized for brainstorming
- `ExecutionResult` (dataclass) - LLM response + metadata

**Key Functions:**

#### PromptExecutor
```python
execute(prompt, model, temperature, max_tokens) -> ExecutionResult
  → Calls: OpenAI API (GPT-4o or GPT-4o-mini)
  → Returns: ExecutionResult(success, response, tokens, cost)
```

#### BrainstormExecutor
```python
generate_scene_ideas(prompt) -> ExecutionResult   # 3 creative approaches
analyze_scene(prompt) -> ExecutionResult          # Structural analysis
get_expert_feedback(prompt, focus) -> ExecutionResult  # Focused guidance
```

**Routing:**
```
Prompt → PromptExecutor.execute()
       → OpenAI API call
       → Returns: ExecutionResult(response, tokens, cost)
```

---

### 10. Web Interface (Phase 3)
**Location:** `prompt_studio_server.py` (root)

**Purpose:** FastAPI backend for chat UI

**Endpoints:**

#### GET /
```python
async def root()
  → Serves: prompt_studio_ui.html
```

#### POST /api/chat
```python
async def chat(request: ChatRequest) -> ChatResponse
  → AIBlockComposer.compose(message)
  → Returns: parsed entities, blocks, prompt
```

#### POST /api/execute
```python
async def execute(request: ExecuteRequest) -> ExecuteResponse
  → PromptExecutor.execute(prompt)
  → Returns: LLM response, tokens, cost
```

#### GET /api/blocks
```python
async def list_blocks() -> List[BlockInfo]
  → BlockRegistry.get_block_info()
  → Returns: All available block types
```

#### GET /api/projects
```python
async def list_projects() -> Dict
  → Scans: projects/ directory
  → Returns: List of available projects
```

#### GET /api/health
```python
async def health()
  → Returns: {"status": "healthy"}
```

**Routing:**
```
Browser → http://localhost:8001/
        → prompt_studio_ui.html (loaded)

User types: "Help with scene 4"
        ↓ POST /api/chat
Server → AIBlockComposer.compose()
        ↓ ComposeResult
Browser ← Shows blocks + prompt

User clicks: "Execute"
        ↓ POST /api/execute
Server → PromptExecutor.execute()
        ↓ ExecutionResult
Browser ← Shows LLM response
```

---

### 11. Chat UI
**Location:** `prompt_studio_ui.html` (root)

**Purpose:** Interactive web interface

**Key JavaScript Functions:**

```javascript
async function sendMessage()
  → POST /api/chat
  → Displays: user message, AI response, blocks, prompt

async function executePrompt()
  → POST /api/execute
  → Displays: LLM response in chat

function updateBlocksPanel(blocks)
  → Displays: Visual block list

function updatePromptPreview(prompt)
  → Displays: Prompt with copy/save buttons

async function loadProjects()
  → GET /api/projects
  → Populates: Project dropdown
```

**User Flow:**
```
1. Load page → loadProjects()
2. Select project → currentProject = "the_proposal_2_0"
3. Type message → sendMessage()
4. See blocks → updateBlocksPanel()
5. See prompt → updatePromptPreview()
6. Click execute → executePrompt()
7. See response → Display in chat
```

---

## Utility Modules

### 12. Bucket Manager
**Location:** `lizzy/bucket_manager.py`

**Purpose:** Manage RAG knowledge buckets

**Classes:**
- `BucketManager` - CRUD for knowledge buckets

**Key Functions:**
```python
create_bucket(name, documents)         # Create LightRAG index
query_bucket(name, query)              # Query knowledge graph
list_buckets()                         # List all buckets
delete_bucket(name)                    # Remove bucket
```

**Routing:**
```
User → python3 manage_buckets.py (root script)
     → BucketManager.create_bucket()
     → LightRAG indexing
     → Saves to: rag_buckets/{name}/
```

---

### 13. Graph Visualizer
**Location:** `lizzy/graph_visualizer.py`

**Purpose:** Visualize LightRAG knowledge graphs

**Classes:**
- `GraphVisualizer` - Create interactive HTML graphs

**Key Functions:**
```python
visualize_bucket(bucket_name)          # Create graph HTML
_load_graph_data()                     # Load from LightRAG
_create_network()                      # Build pyvis network
save()                                 # Save to HTML
```

**Routing:**
```
User → python3 examples_visualize.py
     → GraphVisualizer.visualize_bucket()
     → Reads: rag_buckets/{name}/graph_chunk_entity_relation.graphml
     → Generates: {bucket}_graph.html
```

---

### 14. Bucket Analyzer
**Location:** `lizzy/bucket_analyzer.py`

**Purpose:** Analyze RAG bucket contents and structure

**Classes:**
- `BucketAnalyzer` - Statistical analysis

**Key Functions:**
```python
analyze(bucket_name)                   # Full analysis
get_stats()                            # Entity/relationship counts
get_top_entities()                     # Most connected nodes
get_communities()                      # Detect clusters
```

---

### 15. Multi-Bucket Explorer
**Location:** `lizzy/multi_bucket_explorer.py`

**Purpose:** Query multiple RAG buckets simultaneously

**Classes:**
- `MultiBucketExplorer` - Multi-expert queries

**Key Functions:**
```python
query_all(question)                    # Query all buckets
query_specific(question, buckets)      # Query subset
compare_responses()                    # Side-by-side comparison
```

---

### 16. Reranker
**Location:** `lizzy/reranker.py`

**Purpose:** Rerank RAG results using Cohere

**Classes:**
- `Reranker` - Cohere-based reranking

**Key Functions:**
```python
rerank(query, documents)               # Rerank with Cohere API
```

---

### 17. Database Utilities
**Location:** `lizzy/database.py`

**Purpose:** Database helper functions

**Functions:**
```python
get_connection(project_name)           # Get SQLite connection
execute_query(sql, params)             # Execute SQL
fetch_one(sql, params)                 # Fetch single row
fetch_all(sql, params)                 # Fetch all rows
```

---

## Root Scripts (Entry Points)

### 18. Launcher Scripts

#### start_prompt_studio.sh
```bash
#!/bin/bash
python3 prompt_studio_server.py
```
**Purpose:** Start web server on port 8001

#### manage_buckets.py
```python
# CLI for bucket management
BucketManager → create/query/delete/list buckets
```

#### ai_composer_cli.py
```python
# CLI for AI composer (without web UI)
AIBlockComposer → Natural language → Prompt
```

#### prompt_studio_cli.py
```python
# CLI for manual block composition
BlockRegistry → Select blocks → PromptEngine
```

#### test_write.py
```python
# Test script for WRITE module
WriteModule → Load → Generate → Save → Retrieve
```

#### example_prompt_studio.py
```python
# Examples of Prompt Studio usage
5 examples showing different block combinations
```

#### examples_visualize.py
```python
# Generate graph visualizations
GraphVisualizer → Create HTML graphs for all buckets
```

---

## Data Flow Diagram

### Complete Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                     LIZZY 2.0 PIPELINE                      │
└─────────────────────────────────────────────────────────────┘

1. PROJECT CREATION
   User
    ↓
   lizzy/start.py
    ↓
   projects/{name}/{name}.db (SQLite)
   projects/{name}/exports/

2. DATA INTAKE
   User (via Rich UI)
    ↓
   lizzy/intake.py
    ↓
   Database: scenes (30), characters (N), notes (N)

3. RAG BUCKET CREATION (Parallel)
   Documents (books/plays/scripts)
    ↓
   lizzy/bucket_manager.py
    ↓
   LightRAG indexing
    ↓
   rag_buckets/{name}/graph_chunk_entity_relation.graphml

4. BRAINSTORMING
   Scene data + RAG buckets
    ↓
   lizzy/automated_brainstorm.py OR lizzy/interactive_brainstorm.py
    ↓
   Queries: LightRAG knowledge graphs
    ↓
   Synthesizes: GPT-4o-mini
    ↓
   Database: brainstorm_sessions (blueprint)

5. WRITING
   Blueprint + Scene data + Continuity
    ↓
   lizzy/write.py
    ↓
   Generates: GPT-4o (700-900 word prose)
    ↓
   Database: scene_drafts (versioned)

6. PROMPT STUDIO (Alternative path for 3-5)
   User natural language
    ↓
   lizzy/prompt_studio/ai_composer.py
    ↓
   Entities → Blocks → Prompt
    ↓
   lizzy/prompt_studio/executor.py
    ↓
   GPT-4o response
```

---

## Routing Map

### By User Action

#### "I want to create a new screenplay"
```
Entry: python3 -m lizzy.start
Route: lizzy/start.py → StartModule.create_project()
Output: projects/{name}/ with database
```

#### "I want to fill in my story details"
```
Entry: python3 -m lizzy.intake "Project Name"
Route: lizzy/intake.py → IntakeModule.run()
Output: Database populated with 30 scenes, characters, notes
```

#### "I want to add knowledge sources"
```
Entry: python3 manage_buckets.py
Route: lizzy/bucket_manager.py → BucketManager
Output: rag_buckets/{name}/ with LightRAG index
```

#### "I want to brainstorm a scene (automated)"
```
Entry: python3 -m lizzy.automated_brainstorm
Route: lizzy/automated_brainstorm.py → AutomatedBrainstorm.run_session()
Flow: Load scene → Query RAG → Synthesize → Save blueprint
Output: brainstorm_sessions table entry
```

#### "I want to brainstorm a scene (interactive)"
```
Entry: python3 -m lizzy.interactive_brainstorm
Route: lizzy/interactive_brainstorm.py → InteractiveBrainstorm.run_session()
Flow: Multi-turn chat → Query RAG on demand → Save final blueprint
Output: brainstorm_sessions table entry
```

#### "I want to write a scene"
```
Entry: python3 -m lizzy.write
Route: lizzy/write.py → WriteModule
Flow: Load context → Generate prose → Save draft
Output: scene_drafts table entry (versioned)
```

#### "I want to use Prompt Studio (web UI)"
```
Entry: ./start_prompt_studio.sh
Route: prompt_studio_server.py (FastAPI)
Flow:
  Browser → http://localhost:8001/
         → prompt_studio_ui.html
  User types → POST /api/chat
            → lizzy/prompt_studio/ai_composer.py
            → ComposeResult
  User clicks Execute → POST /api/execute
                     → lizzy/prompt_studio/executor.py
                     → ExecutionResult
Output: Chat interface with blocks + prompts + LLM responses
```

#### "I want to visualize knowledge graphs"
```
Entry: python3 examples_visualize.py
Route: lizzy/graph_visualizer.py → GraphVisualizer
Output: HTML files with interactive graphs
```

---

## Module Dependencies

### Dependency Tree

```
lizzy/
├── start.py
│   └── database.py
│
├── intake.py
│   └── database.py
│
├── automated_brainstorm.py
│   ├── database.py
│   └── bucket_manager.py → LightRAG
│
├── interactive_brainstorm.py
│   ├── database.py
│   └── bucket_manager.py → LightRAG
│
├── write.py
│   ├── database.py
│   └── OpenAI (AsyncOpenAI)
│
├── bucket_manager.py
│   └── LightRAG
│
├── graph_visualizer.py
│   └── LightRAG + pyvis
│
└── prompt_studio/
    ├── blocks/
    │   ├── base.py (ABC)
    │   ├── sql_blocks.py → database.py
    │   ├── rag_blocks.py → bucket_manager.py
    │   └── static_blocks.py
    │
    ├── registry.py → blocks/
    │
    ├── engine.py → blocks/base.py
    │
    ├── ai_composer.py
    │   ├── OpenAI (GPT-4o-mini for entity parsing)
    │   ├── database.py (SQL lookup)
    │   ├── registry.py (block discovery)
    │   └── engine.py (prompt assembly)
    │
    └── executor.py
        └── OpenAI (GPT-4o for execution)

Root Scripts:
├── prompt_studio_server.py
│   ├── FastAPI
│   ├── lizzy/prompt_studio/ai_composer.py
│   ├── lizzy/prompt_studio/executor.py
│   └── lizzy/prompt_studio/registry.py
│
├── prompt_studio_ui.html
│   └── Vanilla JavaScript + Tailwind CSS
│
└── manage_buckets.py
    └── lizzy/bucket_manager.py
```

---

## External API Dependencies

### OpenAI (via openai package)

**Used by:**
- `lizzy/automated_brainstorm.py` → GPT-4o-mini (synthesis)
- `lizzy/interactive_brainstorm.py` → GPT-4o-mini (chat)
- `lizzy/write.py` → GPT-4o (prose generation)
- `lizzy/prompt_studio/ai_composer.py` → GPT-4o-mini (entity parsing)
- `lizzy/prompt_studio/executor.py` → GPT-4o (prompt execution)

**Cost tracking:**
- All modules estimate costs based on tokens
- Typical: $0.015 per scene (WRITE)
- Typical: $0.005 per brainstorm

### LightRAG

**Used by:**
- `lizzy/bucket_manager.py` → Indexing + querying
- `lizzy/automated_brainstorm.py` → RAG queries
- `lizzy/interactive_brainstorm.py` → RAG queries
- `lizzy/prompt_studio/blocks/rag_blocks.py` → RAG queries
- `lizzy/graph_visualizer.py` → Graph reading

**Storage:**
- `rag_buckets/{name}/graph_chunk_entity_relation.graphml`
- `rag_buckets/{name}/kv_store_*.json`

### Cohere (via cohere package)

**Used by:**
- `lizzy/reranker.py` → Rerank RAG results

**API Key:** `by3MxnzMxF7MDE0o4vQfTel7a0sBMzJPGhOO4Ej5`

---

## Database Schema Summary

### SQLite Database
**Location:** `projects/{name}/{name}.db`

**Tables:**

1. **scenes** (created by START, populated by INTAKE)
   - id, scene_number, title, description, characters, tone

2. **characters** (created by START, populated by INTAKE)
   - id, name, role, description, arc

3. **notes** (created by START, populated by INTAKE)
   - id, category, content

4. **brainstorm_sessions** (created by START, populated by BRAINSTORM)
   - id, scene_id, tone, bucket_used, content

5. **drafts** (created by START, for full screenplay exports)
   - id, version, content, scene_id

6. **scene_drafts** (created by WRITE, for individual scene drafts)
   - id, scene_id, content, version, word_count, tokens_used, cost_estimate

---

## Port Assignments

### Web Servers

- **Port 8001** - Prompt Studio (`prompt_studio_server.py`)
- **Port 8000** - (Used by another service, avoided)

---

## File System Organization

```
LIZZY_ROMCOM/
├── lizzy/                          # Core package
│   ├── start.py                    # 1. Project creation
│   ├── intake.py                   # 2. Data collection
│   ├── automated_brainstorm.py     # 3a. Automated brainstorm
│   ├── interactive_brainstorm.py   # 3b. Interactive brainstorm
│   ├── write.py                    # 4. Draft generation
│   ├── bucket_manager.py           # RAG management
│   ├── graph_visualizer.py         # Graph visualization
│   ├── database.py                 # DB utilities
│   ├── reranker.py                 # Cohere reranking
│   └── prompt_studio/              # Prompt Studio subsystem
│       ├── blocks/
│       │   ├── base.py             # Abstract Block
│       │   ├── sql_blocks.py       # 7 SQL blocks
│       │   ├── rag_blocks.py       # 4 RAG blocks
│       │   └── static_blocks.py    # 3 static blocks
│       ├── registry.py             # Block discovery
│       ├── engine.py               # Prompt assembly
│       ├── ai_composer.py          # Natural language → blocks
│       └── executor.py             # LLM execution
│
├── projects/                       # Project data
│   └── {name}/
│       ├── {name}.db               # SQLite database
│       └── exports/                # Future: exported scripts
│
├── rag_buckets/                    # Knowledge graphs
│   └── {bucket_name}/
│       └── graph_chunk_entity_relation.graphml
│
├── docs/                           # Documentation
│   ├── WRITE_MODULE.md
│   ├── PROMPT_STUDIO_ARCHITECTURE.md
│   └── ...
│
├── prompt_studio_server.py         # FastAPI backend
├── prompt_studio_ui.html           # Web interface
├── start_prompt_studio.sh          # Server launcher
├── manage_buckets.py               # Bucket CLI
├── test_write.py                   # WRITE tests
└── README.md                       # Main readme
```

---

## Summary: Every Function's Location & Route

| Function | File | Entry Point | Route |
|----------|------|-------------|-------|
| Create project | `lizzy/start.py` | `python3 -m lizzy.start` | StartModule → DB creation |
| Collect data | `lizzy/intake.py` | `python3 -m lizzy.intake` | IntakeModule → Rich UI → DB |
| Automated brainstorm | `lizzy/automated_brainstorm.py` | `python3 -m lizzy.automated_brainstorm` | Scene → RAG → GPT → DB |
| Interactive brainstorm | `lizzy/interactive_brainstorm.py` | `python3 -m lizzy.interactive_brainstorm` | Chat → RAG → GPT → DB |
| Generate prose | `lizzy/write.py` | `python3 -m lizzy.write` | Context → GPT-4o → DB |
| Manage RAG buckets | `lizzy/bucket_manager.py` | `python3 manage_buckets.py` | CLI → LightRAG |
| Visualize graphs | `lizzy/graph_visualizer.py` | `python3 examples_visualize.py` | LightRAG → HTML |
| SQL blocks | `lizzy/prompt_studio/blocks/sql_blocks.py` | Via Prompt Studio | DB query → formatted string |
| RAG blocks | `lizzy/prompt_studio/blocks/rag_blocks.py` | Via Prompt Studio | LightRAG query → formatted string |
| Static blocks | `lizzy/prompt_studio/blocks/static_blocks.py` | Via Prompt Studio | Text → formatted string |
| Block registry | `lizzy/prompt_studio/registry.py` | Auto-imported | Discovers all Block subclasses |
| Prompt assembly | `lizzy/prompt_studio/engine.py` | Via Composer | Blocks → validated → joined |
| Natural language composer | `lizzy/prompt_studio/ai_composer.py` | Web UI or CLI | NL → GPT parse → SQL → Blocks → Prompt |
| LLM executor | `lizzy/prompt_studio/executor.py` | Web UI | Prompt → GPT-4o → Response |
| Web server | `prompt_studio_server.py` | `./start_prompt_studio.sh` | FastAPI → 5 endpoints |
| Chat UI | `prompt_studio_ui.html` | Browser → :8001 | JavaScript → API calls |

---

**This is the complete routing map for Lizzy 2.0!**

Every function, every file, every API call, every database query - all documented.
