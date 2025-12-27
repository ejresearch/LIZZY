# Lizzy - AI-Assisted Screenplay Writing Framework

**A modular system for writing feature-length romantic comedy screenplays with AI assistance**

---

## What is Lizzy?

Lizzy is a complete framework for writing screenplays using AI, structured memory (SQLite), and knowledge graphs (LightRAG). It takes you from initial concept to finished screenplay through a streamlined pipeline.

**The Pipeline:**
```
IDEATE → BRAINSTORM → WRITE → EXPORT
   ↓          ↓           ↓        ↓
 Concept   Generate    Convert   Compile
 + Setup   Blueprints  to Prose  Script
```

IDEATE handles everything: conversational story development AND project creation in one step.

**Powered by:**
- OpenAI GPT-4o / GPT-4o-mini
- LightRAG knowledge graphs
- SQLite structured memory
- FastAPI web interfaces
- Rich CLI tools

---

## Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/ejresearch/LIZZY.git
cd LIZZY

# Install dependencies
pip install openai lightrag-hku rich fastapi uvicorn pyvis cohere python-dotenv pydantic

# Configure API keys
cp .env.example .env
# Edit .env with your OpenAI API key
```

**Required:** `OPENAI_API_KEY` from https://platform.openai.com/api-keys

### Create Your First Screenplay

**Option A: Web UI (Recommended)**
```bash
python -m backend.ideate_web
# Opens http://localhost:8888
# Chat with Syd to develop your story
# Click "Create Project" when ready
```

**Option B: CLI Quick Mode**
```bash
python -m backend.ideate --quick
# Rapid Q&A for writers who know their story
```

**Then continue with:**
```bash
# Generate scene blueprints
python -m backend.automated_brainstorm

# Write screenplay prose
python -m backend.automated_write

# Export to screenplay format
python -m backend.export
```

**Total cost:** ~$0.60 for a complete 30-scene screenplay

---

## The Pipeline

### IDEATE (Entry Point)

**Conversational story development + project creation**

```bash
# Web UI - guided conversation with Syd
python -m backend.ideate_web

# CLI - quick mode for experienced writers
python -m backend.ideate --quick
```

- Share your story idea with Syd (AI assistant)
- Develop title, logline, characters, and 30-scene beat sheet
- **Automatically creates project** when you click "Create Project"
- No separate setup steps needed

**Modes:**
- **Guided**: Full conversation for exploring ideas
- **Quick**: Rapid Q&A when you already know your story

### BRAINSTORM

**Generate scene blueprints using RAG knowledge**

```bash
# Batch mode (fast)
python -m backend.automated_brainstorm

# Interactive chat mode (deep exploration)
python -m backend.interactive_brainstorm
```

- Queries 3 expert knowledge buckets (books, plays, scripts)
- GPT-4o-mini synthesizes insights into blueprints
- ~2 minutes for all 30 scenes

### WRITE

**Generate prose for each scene**

```bash
# Batch mode (all scenes)
python -m backend.automated_write

# Interactive mode (single scenes with revision control)
python -m backend.write
```

- Converts blueprints to 700-900 word scenes
- Maintains continuity across scenes
- Version control for all drafts
- Golden-era romcom tone

### EXPORT

**Compile to industry-standard formats**

```bash
python -m backend.export
```

- Plain text (.txt)
- Markdown (.md)
- Fountain (.fountain) - for Final Draft, Highland, Fade In
- Final Draft XML (.fdx) - direct import

### Edit Project (Optional)

**Modify existing projects**

```bash
python -m backend.edit_project "Project Name"
```

- Add/edit/delete characters and scenes
- Update writer notes
- View brainstorm sessions and drafts

---

## Project Structure

```
LIZZY_ROMCOM/
├── backend/                    # Core Python modules
│   ├── ideate.py              # IDEATE phase logic + CLI quick mode
│   ├── ideate_web.py          # IDEATE web interface (port 8888)
│   ├── project_creator.py     # Project creation from IDEATE sessions
│   ├── edit_project.py        # Edit existing projects
│   ├── automated_brainstorm.py # Batch blueprint generation
│   ├── interactive_brainstorm.py # Chat-based brainstorming
│   ├── automated_write.py     # Batch prose generation
│   ├── write.py               # Interactive prose generation
│   ├── export.py              # Screenplay compilation
│   ├── database.py            # SQLite management
│   ├── config.py              # Path configuration
│   ├── prompt_studio/         # Advanced prompt composition
│   ├── brainstorm/            # Confidence tracking
│   └── screenplay_formatter/  # Format validation
│
├── servers/                    # FastAPI web application
│   ├── landing_server.py      # Main server (port 8003)
│   ├── routers/               # API endpoints
│   └── services/              # Business logic
│
├── frontend/                   # Web UI
│   ├── landing_page.html      # Project dashboard
│   ├── brainstorm_page.html   # Brainstorm interface
│   └── write_page.html        # Writing interface
│
├── projects/                   # User screenplay projects
│   └── {project_name}/
│       ├── {project_name}.db  # Per-project SQLite database
│       └── exports/           # Exported screenplays
│
├── rag_buckets/               # Knowledge graph indices
│   ├── books/                 # Screenplay structure expertise
│   ├── plays/                 # Dialogue & dramatic theory
│   └── scripts/               # Visual storytelling
│
└── docs/                      # Documentation
```

---

## CLI Reference

### Project Creation

| Command | Purpose |
|---------|---------|
| `python -m backend.ideate_web` | Web UI with Syd (port 8888) |
| `python -m backend.ideate --quick` | CLI quick mode |

### Writing Pipeline

| Command | Purpose |
|---------|---------|
| `python -m backend.automated_brainstorm` | Batch blueprints |
| `python -m backend.interactive_brainstorm` | Chat brainstorming |
| `python -m backend.automated_write` | Batch prose generation |
| `python -m backend.write` | Interactive prose generation |
| `python -m backend.export` | Compile screenplay |

### Project Management

| Command | Purpose |
|---------|---------|
| `python -m backend.edit_project` | Edit existing project |

### Web Servers

| Command | URL | Purpose |
|---------|-----|---------|
| `python servers/landing_server.py` | http://localhost:8003 | Project dashboard |
| `python -m backend.ideate_web` | http://localhost:8888 | IDEATE interface |

---

## Knowledge Graph System

Three expert RAG buckets powered by LightRAG:

| Bucket | Expertise | Use For |
|--------|-----------|---------|
| **books** | Screenplay structure, beat engineering | Act breaks, pacing, turning points |
| **plays** | Dialogue, dramatic theory | Character voice, conflict, emotional beats |
| **scripts** | Visual storytelling | Scene setting, action, visual comedy |

**Manage buckets:**
```bash
python manage_buckets.py
```

---

## Database Schema

Each project gets an isolated SQLite database:

| Table | Purpose |
|-------|---------|
| `projects` | Project metadata |
| `characters` | Character profiles |
| `scenes` | 30-beat scene outlines |
| `brainstorm_sessions` | AI-generated blueprints |
| `scene_drafts` | Versioned prose drafts |
| `drafts` | Full screenplay versions |
| `writer_notes` | Logline, theme, tone, comps |

---

## Cost Estimates

### Full 30-Scene Screenplay

| Phase | Cost |
|-------|------|
| Brainstorm (all scenes) | ~$0.15 |
| Write (GPT-4o) | ~$0.45 |
| **Total** | **~$0.60** |

Budget option with GPT-4o-mini: ~$0.18 total

---

## Golden-Era Romcom Tone

The WRITE module is tuned for classic romantic comedy style:

**Inspired by:** When Harry Met Sally, You've Got Mail, Pretty Woman, Notting Hill

**Principles:**
- Genuine emotional stakes
- Witty, quotable dialogue
- Earned romantic moments
- Heart over hijinks

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| "No projects found" | Create one with `python -m backend.ideate_web` |
| "No blueprint available" | Run BRAINSTORM first |
| "OpenAI API key not found" | Set `OPENAI_API_KEY` in .env |
| "Port already in use" | `pkill -f ideate_web` |

---

## Research Background

This implementation validates the framework from:

> **"LIZZY: A MODULAR FRAMEWORK FOR AI-ASSISTED LONG-FORM WRITING"**
> Jansick, E. (2025)

**Core hypothesis:** Modular architecture + structured memory + dynamic RAG produces higher-quality creative writing than vanilla LLM prompting.

---

## Contact

**Research & Development:** Elle Jansick (ellejansickresearch@gmail.com)

**Repository:** https://github.com/ejresearch/LIZZY

---

*Lizzy - Because every great story deserves great tools.*
