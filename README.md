# Lizzy: A Research Implementation for AI-Assisted Long-Form Writing

**YT Research | April 2025**

## Abstract

This is a focused research implementation of the Lizzy framework described in "LIZZY: A MODULAR FRAMEWORK FOR AI-ASSISTED LONG-FORM WRITING" (Jansick, 2025). This version tests the core hypothesis: **Can a modular, RAG-augmented system with structured memory produce higher-quality creative writing outputs than vanilla LLM prompting?**

Tested on romantic comedy screenplays as the initial use case, the system architecture is designed for extensibility to other long-form writing domains.

## Research Problem

Long-form creative writing with AI faces four key challenges:

1. **Limited Context and Memory** - LLMs lose narrative continuity over lengthy documents
2. **Lack of Iterative Refinement** - Single-pass generation without feedback loops
3. **Generic and Disconnected Outputs** - No dynamic integration of source materials
4. **Fragmented Workflows** - Creative ideation separated from structured planning

**Lizzy addresses these through modular architecture + graph-based RAG + structured SQL memory.**

## System Architecture

### Core Components

```
lizzy/
├── config.py          # System configuration
├── database.py        # SQL-based structured memory
├── lightrag.py        # Graph/vector-based document retrieval
├── start.py           # Project initialization module
├── intake.py          # Metadata capture module
├── brainstorm.py      # RAG-powered ideation module
└── write.py           # Draft synthesis module
```

### The Four-Module Pipeline

1. **Start** → Initialize isolated SQLite database for project
2. **Intake** → Capture characters, scenes, structural elements
3. **Brainstorm** → Query thematic buckets, generate contextual ideas
4. **Write** → Synthesize brainstorms into polished draft

### LightRAG Integration

Three thematic content buckets provide contextual inspiration:

- **Books** - Screenwriting theory (Save the Cat, The Writer's Journey, etc.)
- **Plays** - Classic dramatic structure (Shakespeare, etc.)
- **Scripts** - Contemporary romantic comedy exemplars

Graph/vector-based retrieval ensures semantically relevant context informs each brainstorming session.

## Tech Stack

- **LLM**: OpenAI GPT-4o-mini (cost-efficient, fast iteration)
- **RAG**: LightRAG (open-source graph-based vector database)
- **Memory**: SQLite (isolated project databases, versioned drafts)
- **Prompting**: Structured templates with dynamic context injection

## Installation

```bash
# Clone repository
cd /Users/elle_jansick/LIZZY_ROMCOM

# Install dependencies
pip install lightrag-hku openai rich

# Configure API key
export OPENAI_API_KEY="your-openai-key"
```

## Usage

```bash
# 1. Initialize project
python -m lizzy.start "My Romantic Comedy"

# 2. Add characters and scenes
python -m lizzy.intake "My Romantic Comedy"

# 3. Generate brainstorming ideas (RAG-powered)
python -m lizzy.brainstorm "My Romantic Comedy" --tone "Romantic Dramedy"

# 4. Synthesize final draft
python -m lizzy.write "My Romantic Comedy"
```

## Experimental Design

### Hypothesis

Modular RAG-augmented writing produces:
- Higher narrative coherence
- Better character consistency
- More authentic dialogue
- Improved thematic depth

Compared to direct LLM prompting.

### Tone Conditions

1. **Cheesy Romcom** - Light, formulaic, crowd-pleasing
2. **Romantic Dramedy** - Grounded, emotionally complex
3. **Shakespearean Comedy** - Witty, structured, literary

### Evaluation Metrics (Planned)

- Narrative coherence scoring (human evaluation)
- Character consistency checks (automated + human)
- Comparative user studies (Lizzy vs ChatGPT direct)
- Output quality rubrics

## Current Status

**Phase 1: Core Implementation** ✅
- Four-module pipeline functional
- LightRAG integration complete
- SQL structured memory working

**Phase 2: Validation** (In Progress)
- User studies with writers
- Output quality assessment
- Comparative analysis

**Phase 3: Extension** (Future)
- Adapt to novels, technical writing, research papers
- Multi-genre support
- Collaborative editing features

## Key Innovations

1. **Structured Memory** - Each project in isolated SQLite database with versioned drafts
2. **Dynamic RAG** - Context-aware retrieval from thematic source buckets
3. **Modular Refinement** - Iterative brainstorm → write → revise loop
4. **Genre-Agnostic Architecture** - Initial romcom focus, designed for extensibility

## Research Context

This implementation validates the theoretical framework presented in:

> Jansick, E. (2025). "LIZZY: A MODULAR FRAMEWORK FOR AI-ASSISTED LONG-FORM WRITING."
> YT Research White Paper.

The goal is to demonstrate that **structured memory + dynamic retrieval + modular iteration** produces superior creative outputs compared to monolithic LLM generation.

## Citation

If you use this system in research, please cite:

```
Jansick, E. (2025). Lizzy: A Modular Framework for AI-Assisted Long-Form Writing.
YT Research. https://github.com/ytresearch/lizzy
```

## License

MIT License - See LICENSE file

## Contact

**YT Research**
ellejansickresearch@gmail.com

---

*Built to test the hypothesis that AI-assisted writing benefits from modular architecture, structured memory, and dynamic contextual retrieval.*
