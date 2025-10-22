# Lizzy 2.0 - AI-Assisted Screenplay Writing Framework

**Complete modular system for writing feature-length screenplays with AI assistance**

---

## 🎬 What is Lizzy?

Lizzy 2.0 is a complete framework for writing screenplays using AI, structured memory, and knowledge graphs. It takes you from story concept to finished screenplay prose through a modular pipeline.

**The System:**
```
START → INTAKE → BRAINSTORM → WRITE → Export
  ↓       ↓          ↓           ↓        ↓
Create  Collect   Generate   Convert   Compile
Project  Story    Blueprints  to Prose  Script
```

**Powered by:**
- OpenAI GPT-4o & GPT-4o-mini
- LightRAG knowledge graphs
- SQLite structured memory
- Rich CLI interfaces

---

## 🚀 Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/ejresearch/LIZZY.git
cd LIZZY

# Install dependencies
pip install openai lightrag-hku rich fastapi uvicorn pyvis

# Set API key
export OPENAI_API_KEY="sk-..."
```

### Create Your First Screenplay

```bash
# 1. Create project structure
python3 -m lizzy.start

# 2. Fill in your story (30-beat structure)
python3 -m lizzy.intake "My Screenplay"

# 3. Generate scene blueprints (optional but recommended)
python3 -m lizzy.automated_brainstorm

# 4. Write screenplay prose
python3 -m lizzy.write

# That's it! Your drafts are in the database.
```

**Total time:** ~30 minutes setup, ~10 minutes per scene

---

## 📦 What's Included

### Core Pipeline Modules

**1. START** - Project initialization
- Creates project directory structure
- Initializes SQLite database
- Sets up export folders

**2. INTAKE** - Story data collection
- 30-beat screenplay structure (Save the Cat)
- Character bios and arcs
- Writer's notes and themes
- Beautiful Rich CLI interface

**3. BRAINSTORM** - Blueprint generation (2 modes)
- **Automated:** Batch process all scenes with RAG
- **Interactive:** Chat-based deep exploration
- Queries expert knowledge buckets
- Saves blueprints to database

**4. WRITE** - Prose generation
- Converts blueprints → 700-900 word scenes
- Golden-era romcom tone (When Harry Met Sally style)
- Maintains continuity across scenes
- Version control for drafts

### Prompt Studio System

**Natural language prompt composition with visual feedback**

- **14 composable blocks** (SQL, RAG, Static)
- **AI Composer** - Natural language → automatic block building
- **Web interface** - Chat UI with visual block feedback
- **Executor** - One-click LLM execution
- **4 execution modes** - General, Ideas, Analysis, Feedback

**Start:** `./start_prompt_studio.sh` → http://localhost:8001

### Knowledge Graph System

**3 expert RAG buckets powered by LightRAG:**

- **Books** - Screenplay structure & beat engineering
- **Plays** - Dialogue & dramatic theory
- **Scripts** - Visual storytelling & execution

**Manage:** `python3 manage_buckets.py`

**Visualize:** `python3 examples_visualize.py`

---

## 🎯 Complete User Guide

### Phase 1: Project Setup

#### Create New Project
```bash
python3 -m lizzy.start
```

**What happens:**
- Creates `projects/{name}/` directory
- Initializes SQLite database with schema
- Sets up `exports/` folder

**Output:** `projects/{name}/{name}.db`

#### Populate Story Data
```bash
python3 -m lizzy.intake "Project Name"
```

**Beautiful CLI prompts you for:**
1. Project metadata (title, logline, genre)
2. Character bios (name, role, description, arc)
3. 30-beat scene structure (title, description, characters, tone)
4. Writer's notes (themes, style, references)

**Output:** Database populated with all story data

---

### Phase 2: Knowledge Preparation (One-Time)

#### Create RAG Buckets
```bash
python3 manage_buckets.py
```

**Options:**
1. Create bucket → Add documents → LightRAG indexes them
2. Query bucket → Test RAG retrieval
3. List buckets → See what exists
4. Delete bucket

**Recommended buckets:**
- `books` - Add screenplay theory PDFs/text
- `plays` - Add classic plays for dialogue study
- `scripts` - Add romcom screenplay examples

**This is one-time setup** - buckets work across all projects

---

### Phase 3: Blueprint Generation

You have **two options** for brainstorming:

#### Option A: Automated Brainstorm (Fast)
```bash
python3 -m lizzy.automated_brainstorm
```

**Process:**
- Select project
- Select scene(s) to brainstorm
- System queries all RAG buckets
- GPT-4o-mini synthesizes blueprint
- Saves to database

**Best for:** Processing many scenes quickly

#### Option B: Interactive Brainstorm (Deep)
```bash
python3 -m lizzy.interactive_brainstorm
```

**Process:**
- Select project and scene
- Multi-turn chat conversation
- You control which buckets to query
- Explore different aspects
- Save final synthesis

**Best for:** Complex scenes needing exploration

**Output:** `brainstorm_sessions` table populated with blueprints

---

### Phase 4: Prose Generation

#### Generate Scene Drafts
```bash
python3 -m lizzy.write
```

**CLI Menu:**
1. **Write a scene** - Generate new draft
   - Enter scene number
   - System loads context (scene + blueprint + continuity)
   - GPT-4o generates 700-900 words
   - Saves to database with version number

2. **View drafts** - See all versions of a scene
   - Enter scene number
   - See all versions with metadata
   - View any version

**Output:** `scene_drafts` table with versioned prose

---

### Phase 5: Prompt Studio (Advanced)

#### Launch Web Interface
```bash
./start_prompt_studio.sh
```

Open browser: http://localhost:8001

#### Use Natural Language
**Type:** "Help me with scene 4, check scripts"

**System automatically:**
1. Parses your intent with GPT-4o-mini
2. Finds scene 4 in database
3. Builds blocks:
   - SceneBlock(4) → Scene data
   - ScriptsQueryBlock("scene 4") → RAG query
4. Assembles rich prompt
5. Shows blocks + prompt in UI

#### Execute Prompts
**Click:** "Execute" button

**Choose mode:**
- General - Open-ended
- Ideas - 3 creative approaches
- Analysis - Structural breakdown
- Feedback - Expert guidance

**Get:** LLM response in chat

---

## 📁 Project Structure

```
LIZZY_ROMCOM/
├── lizzy/                          # Core package
│   ├── start.py                    # 1. Project creation
│   ├── intake.py                   # 2. Data collection
│   ├── automated_brainstorm.py     # 3a. Automated blueprints
│   ├── interactive_brainstorm.py   # 3b. Interactive blueprints
│   ├── write.py                    # 4. Prose generation
│   ├── bucket_manager.py           # RAG bucket CRUD
│   ├── graph_visualizer.py         # Graph visualization
│   ├── database.py                 # SQLite utilities
│   └── prompt_studio/              # Prompt Studio system
│       ├── blocks/                 # 14 composable blocks
│       ├── engine.py               # Prompt assembly
│       ├── ai_composer.py          # Natural language parsing
│       └── executor.py             # LLM execution
│
├── projects/                       # Your projects
│   └── {project_name}/
│       ├── {project_name}.db       # SQLite database
│       └── exports/                # Future exports
│
├── rag_buckets/                    # Knowledge graphs
│   ├── books/                      # Screenplay theory
│   ├── plays/                      # Dramatic structure
│   └── scripts/                    # Romcom examples
│
├── docs/                           # Documentation
│   ├── ARCHITECTURE_MAP.md         # Complete routing map
│   ├── WRITE_MODULE.md             # WRITE documentation
│   ├── PROMPT_STUDIO_ARCHITECTURE.md
│   └── ...
│
├── prompt_studio_server.py         # FastAPI backend
├── prompt_studio_ui.html           # Web interface
├── start_prompt_studio.sh          # Server launcher
├── manage_buckets.py               # Bucket CLI
├── test_write.py                   # WRITE tests
└── README.md                       # This file
```

---

## 🔧 CLI Tools Reference

### Core Pipeline

| Command | Purpose | Output |
|---------|---------|--------|
| `python3 -m lizzy.start` | Create project | Directory + database |
| `python3 -m lizzy.intake "Name"` | Collect story data | Populated database |
| `python3 -m lizzy.automated_brainstorm` | Batch blueprints | brainstorm_sessions |
| `python3 -m lizzy.interactive_brainstorm` | Chat-based exploration | brainstorm_sessions |
| `python3 -m lizzy.write` | Generate prose | scene_drafts |

### Utilities

| Command | Purpose |
|---------|---------|
| `./start_prompt_studio.sh` | Launch web UI (port 8001) |
| `python3 manage_buckets.py` | Manage RAG buckets |
| `python3 examples_visualize.py` | Generate graph visualizations |
| `python3 test_write.py` | Test WRITE module |

---

## 💰 Cost Estimates

### Per Scene (800 words)

**Brainstorm:**
- Automated: ~$0.005 (GPT-4o-mini)
- Interactive: ~$0.005-$0.015 (varies)

**Write:**
- Draft generation: ~$0.015 (GPT-4o)

**Total per scene:** ~$0.02

### Full 30-Scene Screenplay

**First draft:**
- Brainstorm: $0.15
- Write: $0.45
- **Total: $0.60**

**With revisions (3 drafts per scene):**
- **Total: ~$1.80**

**Extremely affordable!**

---

## 🎨 Golden-Era Romcom Tone

The WRITE module uses principles from classic romantic comedies:

**Inspired by:**
- When Harry Met Sally (Nora Ephron)
- You've Got Mail (Nora Ephron)
- Pretty Woman (J.F. Lawton)
- Sleepless in Seattle (Jeff Arch)
- Notting Hill (Richard Curtis)

**Principles:**
- Genuine emotional stakes
- Witty, quotable dialogue
- Earned romantic moments
- Universal yet specific conflicts
- Heart over hijinks

**Avoids:**
- Contrived misunderstandings
- Mean-spirited humor
- Humiliation comedy
- Relationships without foundation

---

## 🗄️ Database Schema

**SQLite database per project:**

### Tables Created by START

1. **scenes** (30 beats)
   - scene_number, title, description, characters, tone

2. **characters** (your cast)
   - name, role, description, arc

3. **notes** (writer's notes)
   - category, content

4. **brainstorm_sessions** (blueprints)
   - scene_id, tone, bucket_used, content

5. **drafts** (full screenplay exports)
   - version, content, scene_id

6. **scene_drafts** (created by WRITE)
   - scene_id, content, version, word_count, tokens, cost

---

## 🧩 Prompt Studio Deep Dive

### Block Types (14 total)

**SQL Blocks (7):**
- SceneBlock - Specific scene data
- CharacterBiosBlock - All character info
- WriterNotesBlock - Notes by category
- ProjectMetadataBlock - Project info
- AllScenesBlock - List all 30 scenes
- PreviousSceneBlock - Continuity
- NextSceneBlock - Foreshadowing

**RAG Blocks (4):**
- BooksQueryBlock - Structure expert
- PlaysQueryBlock - Dialogue expert
- ScriptsQueryBlock - Visual expert
- MultiExpertQueryBlock - All 3 at once

**Static Blocks (3):**
- TextBlock - Plain text
- TemplateBlock - Variables
- HeaderBlock - Section headers

### Natural Language Examples

**Input:** "Jenny in scene 4, check scripts"

**System builds:**
```python
[
  SceneBlock(4),
  TextBlock("Focus on character: Jenny"),
  ScriptsQueryBlock("scene 4 with Jenny")
]
```

**Input:** "Help me brainstorm scene 10 with all experts"

**System builds:**
```python
[
  SceneBlock(10),
  CharacterBiosBlock(),
  MultiExpertQueryBlock("scene 10 ideas")
]
```

### API Endpoints

**GET /** → Serve UI
**POST /api/chat** → Compose prompt from natural language
**POST /api/execute** → Execute prompt with LLM
**GET /api/blocks** → List available blocks
**GET /api/projects** → List projects
**GET /api/health** → Health check

---

## 🔄 Complete Workflow Example

### Writing "The Proposal 2.0"

```bash
# 1. Create project
python3 -m lizzy.start
# Enter: "the_proposal_2_0"

# 2. Add story data
python3 -m lizzy.intake "the_proposal_2_0"
# Fill in: characters, 30 scenes, themes

# 3. Create knowledge buckets (one-time)
python3 manage_buckets.py
# Create: books, plays, scripts buckets
# Add documents to each

# 4. Brainstorm scenes 1-5
python3 -m lizzy.automated_brainstorm
# Select scenes 1-5
# Wait ~2 minutes
# Blueprints saved

# 5. Write scenes 1-5
python3 -m lizzy.write
# For each scene:
#   - Select scene number
#   - Generate draft
#   - Review output
#   - Save

# 6. Use Prompt Studio for scene 6 (complex scene)
./start_prompt_studio.sh
# Open browser
# Type: "Help me brainstorm scene 6 with dialogue focus"
# Review blocks and prompt
# Execute
# Get creative ideas
# Take notes

# 7. Brainstorm scene 6 interactively
python3 -m lizzy.interactive_brainstorm
# Select scene 6
# Multi-turn conversation
# Incorporate Prompt Studio insights
# Save final blueprint

# 8. Write scene 6
python3 -m lizzy.write
# Generate draft
# Review
# Revise if needed (creates v2, v3...)

# Repeat for remaining scenes...
```

---

## 📊 Feature Comparison

### Automated vs Interactive Brainstorm

| Feature | Automated | Interactive |
|---------|-----------|-------------|
| Speed | Fast (1-2 min/scene) | Slow (5-15 min/scene) |
| Control | Low | High |
| Best for | Batch processing | Complex scenes |
| RAG queries | All buckets | You choose |
| Conversation | None | Multi-turn |
| Output | Blueprint | Blueprint |

### Brainstorm vs Prompt Studio

| Feature | Brainstorm | Prompt Studio |
|---------|------------|---------------|
| Purpose | Generate blueprints | Flexible prompting |
| Saves to DB | Yes | No (manual) |
| Interface | CLI | Web UI |
| Structured | Yes | No |
| Natural language | No | Yes |
| Visual feedback | No | Yes |
| Best for | Standard workflow | Experimentation |

**Use both together!** Prompt Studio for exploration, Brainstorm for production.

---

## 🛠️ Advanced Features

### Version Control

Every scene draft is versioned:
- v1 - First draft
- v2 - Revision
- v3 - Polish
- etc.

All versions preserved in database.

### Continuity Awareness

WRITE module automatically:
- Loads previous scene's draft (continuity)
- Loads next scene's outline (foreshadowing)
- Maintains character consistency
- Tracks story arc

### Cost Tracking

Every operation tracks:
- Tokens used
- Estimated cost
- Model used
- Timestamp

Review spending anytime in database.

### Graph Visualization

Explore knowledge graphs:
```bash
python3 examples_visualize.py
```

Creates interactive HTML visualizations showing:
- Entity relationships
- Knowledge clusters
- Connection strength
- Community detection

---

## 🚧 Future Features (Not Yet Built)

From white paper specs:

1. **Batch WRITE** - Process all 30 scenes automatically
2. **Export Module** - Compile to .txt, .md, screenplay format
3. **Advanced Continuity** - Cross-reference arcs and motifs
4. **Multiple Tones** - Beyond romcom (thriller, drama, etc.)
5. **Revision System** - Side-by-side version comparison
6. **Quality Metrics** - Dialogue balance, pacing analysis
7. **Web UI for WRITE** - Like Prompt Studio but for drafting
8. **Collaborative Editing** - Multi-user support

**Current focus:** Core pipeline (✅ complete)

---

## 📚 Documentation

**In `docs/` folder:**

### Core Modules
- `WRITE_MODULE.md` - Complete WRITE documentation
- `ARCHITECTURE_MAP.md` - Every function's location & routing

### Prompt Studio
- `PROMPT_STUDIO_ARCHITECTURE.md` - System design
- `PROMPT_STUDIO_IMPLEMENTATION.md` - Implementation details
- `AI_COMPOSER.md` - Natural language parser
- `CHAT_UI.md` - Web interface guide

### Utilities
- `VISUALIZATION_GUIDE.md` - Graph visualization
- `MULTI_BUCKET_GUIDE.md` - Cross-bucket queries
- `HOW_IT_WORKS_SIMPLE.md` - Beginner-friendly overview

### Reference
- `FUNCTION_LIST.md` - All functions catalog
- `SQL_TO_PROMPT_FLOW.md` - Data flow diagrams

**Start with:** `ARCHITECTURE_MAP.md` for complete system overview

---

## 🐛 Troubleshooting

### "Scene not found"
**Fix:** Run INTAKE first to populate database

### "No blueprint available"
**Fix:** Run BRAINSTORM (automated or interactive) first

### "OpenAI API key not found"
**Fix:** `export OPENAI_API_KEY="sk-..."`

### "Port 8001 already in use"
**Fix:** Kill existing server: `pkill -f prompt_studio_server`

### "LightRAG import error"
**Fix:** `pip install lightrag-hku`

### Draft quality issues
**Fix:**
- Run BRAINSTORM first for detailed blueprints
- Add more specific scene descriptions
- Use Interactive Brainstorm for complex scenes

---

## 🔬 Research Background

This implementation validates the framework presented in:

> **"LIZZY: A MODULAR FRAMEWORK FOR AI-ASSISTED LONG-FORM WRITING"**
> Jansick, E. (2025)

**Core hypothesis:**
Modular architecture + structured memory + dynamic RAG produces higher-quality creative writing than vanilla LLM prompting.

**Key innovations:**
1. Separated ideation (Brainstorm) from execution (Write)
2. Graph-based RAG for contextual inspiration
3. SQL-based structured memory for continuity
4. Modular refinement loops

**Initial validation:** Golden-era romantic comedy screenplays

**Future extension:** Novels, technical writing, research papers

---

## 📝 Example Output

### Input (Scene 1)
**Title:** "x"
**Description:** "x"
**Blueprint:** None

### Generated Draft (891 words)

```
The scene opens in a lively, bustling bookshop in the heart of New York City,
filled with the comforting smell of aged paper and fresh coffee from the small
café in the back. The shop is nestled between two larger buildings, almost like
a secret waiting to be discovered...

[Full prose with dialogue, action, character emotions, and romantic tension]
```

**Quality:**
- ✅ Golden-era romcom tone
- ✅ Visual scene setting
- ✅ Character introduction
- ✅ Proper structure

**Cost:** $0.0148
**Time:** 23 seconds

---

## 🤝 Contributing

This is a research implementation. Contributions welcome!

**Areas for contribution:**
- Additional block types for Prompt Studio
- New tone presets for WRITE
- Export format converters
- Quality analysis tools
- Alternative LLM backends

**Process:**
1. Fork repository
2. Create feature branch
3. Add tests
4. Submit pull request

---

## 📜 License

MIT License - See LICENSE file

---

## 📞 Contact

**Research & Development:**
Elle Jansick
ellejansickresearch@gmail.com

**Repository:**
https://github.com/ejresearch/LIZZY

---

## 🙏 Acknowledgments

**Inspired by:**
- Nora Ephron (screenplay craft)
- Blake Snyder (Save the Cat)
- Joseph Campbell (Hero's Journey)
- LightRAG team (graph RAG)
- OpenAI (GPT models)

**Built with:**
- Python 3.10+
- OpenAI API
- LightRAG
- Rich (CLI)
- FastAPI (web)
- SQLite (storage)

---

## ⚡ Quick Reference

### Essential Commands

```bash
# Setup
export OPENAI_API_KEY="sk-..."

# Pipeline
python3 -m lizzy.start
python3 -m lizzy.intake "Project"
python3 -m lizzy.automated_brainstorm
python3 -m lizzy.write

# Prompt Studio
./start_prompt_studio.sh

# Utilities
python3 manage_buckets.py
python3 examples_visualize.py
```

### File Locations

- Projects: `projects/{name}/{name}.db`
- RAG buckets: `rag_buckets/{bucket}/`
- Docs: `docs/`
- Tests: `test_write.py`

### Ports

- Prompt Studio: http://localhost:8001

### Key Modules

- START: `lizzy/start.py`
- INTAKE: `lizzy/intake.py`
- BRAINSTORM: `lizzy/automated_brainstorm.py` + `lizzy/interactive_brainstorm.py`
- WRITE: `lizzy/write.py`
- PROMPT STUDIO: `lizzy/prompt_studio/`

---

**🎬 Ready to write your screenplay? Start with `python3 -m lizzy.start`**

**📖 Need help? Check `docs/ARCHITECTURE_MAP.md` for complete system overview**

**💡 Questions? Open an issue on GitHub**

---

*Lizzy 2.0 - Because every great story deserves great tools.*
