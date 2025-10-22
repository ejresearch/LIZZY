# Prompt Studio Architecture

**Version:** 1.0 (Backend-First MVP)
**Date:** October 22, 2025

---

## 🎯 Vision

Prompt Studio is a **block-based prompt composition system** inspired by Scratch. It allows you to visually compose LLM prompts by combining data blocks like building blocks:

- 🗄️ **SQL Blocks** - Pull data from your project database
- 🧠 **RAG Blocks** - Query knowledge graph buckets
- 📝 **Static Blocks** - Add text, templates, headers

**Goal**: Make all your data sources **composable** so you can build custom prompts for brainstorming, querying, or any LLM task.

---

## 🏗️ Current Implementation (Phase 1: Backend)

### Directory Structure

```
lizzy/prompt_studio/
├── __init__.py                # Public API
├── blocks/
│   ├── __init__.py
│   ├── base.py               # Base Block class
│   ├── sql_blocks.py         # SceneBlock, CharacterBiosBlock, etc.
│   ├── rag_blocks.py         # BooksQueryBlock, PlaysQueryBlock, etc.
│   └── static_blocks.py      # TextBlock, TemplateBlock, etc.
├── engine.py                 # PromptEngine - assembles blocks
└── registry.py               # BlockRegistry - discovery system

prompt_studio_cli.py          # Simple CLI for testing
```

---

## 🧩 Block System

### Base Block Class

All blocks inherit from `Block`:

```python
from lizzy.prompt_studio.blocks.base import Block

class Block(ABC):
    def execute(self, project_name: str, **kwargs) -> str:
        """Execute block and return formatted string"""
        pass

    def get_description(self) -> str:
        """Human-readable description"""
        pass

    def validate(self) -> tuple[bool, Optional[str]]:
        """Validate block configuration"""
        pass
```

### Available Blocks (17 total)

#### SQL Blocks (7)
- **SceneBlock** - Get specific scene data
- **CharacterBiosBlock** - All character bios
- **WriterNotesBlock** - Writer notes (all or by category)
- **ProjectMetadataBlock** - Project info + story spine
- **AllScenesBlock** - List all scenes
- **PreviousSceneBlock** - Scene N-1
- **NextSceneBlock** - Scene N+1

#### RAG Blocks (4)
- **BooksQueryBlock** - Query books expert (structure)
- **PlaysQueryBlock** - Query plays expert (dialogue)
- **ScriptsQueryBlock** - Query scripts expert (visual)
- **MultiExpertQueryBlock** - Query all 3 experts at once

#### Static Blocks (3)
- **TextBlock** - Simple static text
- **TemplateBlock** - Text with {variable} substitution
- **SectionHeaderBlock** - Formatted headers with dividers

---

## ⚙️ Prompt Engine

### How It Works

```python
from lizzy.prompt_studio import PromptEngine
from lizzy.prompt_studio.blocks import SceneBlock, CharacterBiosBlock

# 1. Create blocks
blocks = [
    SceneBlock(scene_number=5),
    CharacterBiosBlock(),
]

# 2. Assemble prompt
engine = PromptEngine()
result = engine.assemble(blocks, project_name="The Proposal 2.0")

# 3. Use the prompt
print(result.prompt)
print(f"Total chars: {result.total_chars}")
print(f"Execution time: {result.total_execution_time_ms}ms")
```

### What `assemble()` Does

1. **Validates** each block
2. **Executes** each block in order
3. **Collects** output strings
4. **Joins** them with separator (default: `\n\n`)
5. **Returns** `PromptResult` with:
   - `prompt` - Final assembled string
   - `metadata` - Execution stats per block
   - `total_execution_time_ms` - Total time
   - `total_chars` - Total prompt length
   - `errors` - Any errors that occurred

---

## 📋 Block Registry

Discovery system for available blocks:

```python
from lizzy.prompt_studio import BlockRegistry

# List all block types
block_types = BlockRegistry.list_blocks()
# ['scene', 'character_bios', 'books_query', ...]

# Get blocks by category
categories = BlockRegistry.get_blocks_by_category()
# {'SQL Blocks': [...], 'RAG Blocks': [...], 'Static Blocks': [...]}

# Create a block by type name
block = BlockRegistry.create_block('scene', scene_number=5)

# Get info about all blocks
info = BlockRegistry.get_block_info()
```

---

## 🖥️ CLI Interface

### Launch

```bash
python3 prompt_studio_cli.py
```

### Features

1. **List available blocks** - See all 17 block types
2. **Show block info** - Detailed table of blocks
3. **Example: Basic prompt** - Scene + Characters
4. **Example: RAG query** - Query books expert
5. **Example: Multi-expert** - Query all 3 buckets
6. **Custom composition** - Build your own prompt interactively

### Example Session

```
1. Select "Custom composition"
2. Add SceneBlock (scene 5)
3. Add CharacterBiosBlock
4. Add BooksQueryBlock ("romantic tension techniques")
5. Done - see assembled prompt
```

Result:
```
SCENE 5: [title]
Act: [act]
Description: [description]
Characters: [characters]

CHARACTER BIOS:
Emma: [bio]
Jake: [bio]

BOOKS EXPERT (Structure & Beat Engineering):
Query: romantic tension techniques
Response: [RAG results...]
```

---

## 🔄 Integration with Brainstorm Modules

### Next Steps (Phase 2)

Modify `automated_brainstorm.py` and `interactive_brainstorm.py` to:

1. **Accept custom prompt blocks** as an alternative to default prompts
2. **Allow users to select**: "Use default prompt" or "Use custom blocks"

### Proposed API

```python
# automated_brainstorm.py
from lizzy.prompt_studio.blocks import SceneBlock, BooksQueryBlock

# Option 1: Use custom blocks
custom_blocks = [
    SceneBlock(scene_number=5),
    BooksQueryBlock(query="scene structure"),
]

brainstorm = AutomatedBrainstorm(project_name, custom_blocks=custom_blocks)
await brainstorm.run_batch_processing()

# Option 2: Use defaults (current behavior)
brainstorm = AutomatedBrainstorm(project_name)
await brainstorm.run_batch_processing()
```

### Integration Benefits

- **Flexibility** - Users can customize what data goes into prompts
- **Testing** - Easy A/B testing of different prompt compositions
- **Control** - Full control over context injection
- **Reusability** - Save block configurations as "recipes"

---

## 📊 Example Use Cases

### Use Case 1: Enhanced Scene Processing

```python
blocks = [
    SectionHeaderBlock(title="CURRENT SCENE"),
    SceneBlock(scene_number=5),

    SectionHeaderBlock(title="CONTEXT"),
    PreviousSceneBlock(scene_number=5),
    NextSceneBlock(scene_number=5),

    SectionHeaderBlock(title="CHARACTERS"),
    CharacterBiosBlock(),

    SectionHeaderBlock(title="EXPERT GUIDANCE"),
    MultiExpertQueryBlock(query="how to build tension in this scene"),
]
```

### Use Case 2: Quick RAG Query

```python
blocks = [
    TextBlock("I need help with dialogue pacing."),
    PlaysQueryBlock(query="dialogue pacing techniques", mode="hybrid"),
]
```

### Use Case 3: Story Spine Analysis

```python
blocks = [
    ProjectMetadataBlock(),  # Shows full story spine
    TextBlock("Analyze the overall story structure and identify weak points."),
]
```

### Use Case 4: Character-Focused Query

```python
blocks = [
    CharacterBiosBlock(),
    TextBlock("Based on these character bios, suggest 3 potential conflicts."),
    BooksQueryBlock(query="character conflict generation"),
]
```

---

## 🔮 Future: Web UI (Phase 2)

### Vision

Visual drag-and-drop interface:

```
┌─────────────────────────────────────────┐
│         PROMPT STUDIO (Web UI)          │
│                                         │
│  ┌───────────┐                          │
│  │ BLOCKS    │                          │
│  ├───────────┤      ┌──────────────┐   │
│  │ SQL       │ ───► │ CANVAS       │   │
│  │ • Scene   │      │              │   │
│  │ • Chars   │      │ [Scene 5]    │   │
│  │           │      │      ↓        │   │
│  │ RAG       │      │ [Chars]      │   │
│  │ • Books   │      │      ↓        │   │
│  │ • Plays   │      │ [Books Q]    │   │
│  │           │      │              │   │
│  │ Static    │      └──────────────┘   │
│  │ • Text    │                          │
│  └───────────┘                          │
│                                         │
│  Target: [Automated ▼] [Interactive]   │
│                                         │
│              [🚀 Run Prompt]            │
└─────────────────────────────────────────┘
```

### Tech Stack (Proposed)

- **Backend**: FastAPI (serves blocks, executes prompts)
- **Frontend**: React + React Flow (visual editor)
- **State**: Block configurations stored as JSON
- **Execution**: POST to `/api/execute` with block array

---

## 📈 Metrics & Monitoring

### Block Execution Metadata

Each block execution tracks:
- `block_type` - Type of block
- `block_id` - Unique identifier
- `execution_time_ms` - How long it took
- `data_size_chars` - Size of output
- `error` - Any error that occurred

### PromptResult

After assembling a prompt:
- `prompt` - Final string
- `metadata` - Array of block metadata
- `total_execution_time_ms` - Total assembly time
- `total_chars` - Total prompt length
- `errors` - List of errors

---

## 🎓 Code Examples

### Example 1: Simple Scene Prompt

```python
from lizzy.prompt_studio import assemble_prompt
from lizzy.prompt_studio.blocks import SceneBlock, CharacterBiosBlock

blocks = [
    SceneBlock(scene_number=1),
    CharacterBiosBlock(),
]

prompt = assemble_prompt(blocks, project_name="The Proposal 2.0")
print(prompt)
```

### Example 2: Multi-Expert Consultation

```python
from lizzy.prompt_studio import PromptEngine
from lizzy.prompt_studio.blocks import (
    TextBlock,
    MultiExpertQueryBlock,
)

blocks = [
    TextBlock("I need expert advice on the following:"),
    MultiExpertQueryBlock(query="how to write a compelling meet-cute", mode="hybrid"),
]

engine = PromptEngine()
result = engine.assemble(blocks, project_name="The Proposal 2.0")

print(result.prompt)
print(f"\nStats: {result.total_chars} chars, {result.total_execution_time_ms:.2f}ms")
```

### Example 3: Template Block

```python
from lizzy.prompt_studio.blocks import TemplateBlock

template = """
Scene: {scene_number}
Project: {project_name}
Task: {task}
"""

block = TemplateBlock(
    template=template,
    variables={'scene_number': 5, 'task': 'Analyze structure'}
)

output = block.execute(project_name="The Proposal 2.0")
```

### Example 4: Conditional Block Logic

```python
def build_prompt_for_scene(scene_number: int, include_rag: bool = False):
    blocks = [
        SceneBlock(scene_number=scene_number),
    ]

    if scene_number > 1:
        blocks.append(PreviousSceneBlock(scene_number=scene_number))

    if scene_number < 30:
        blocks.append(NextSceneBlock(scene_number=scene_number))

    if include_rag:
        blocks.append(
            BooksQueryBlock(query="scene structure analysis")
        )

    return assemble_prompt(blocks, project_name="The Proposal 2.0")
```

---

## ✅ Current Status

### ✅ Completed (Phase 1)

- [x] Base Block class with validation
- [x] 7 SQL blocks (Scene, Characters, Notes, etc.)
- [x] 4 RAG blocks (Books, Plays, Scripts, Multi-Expert)
- [x] 3 Static blocks (Text, Template, Header)
- [x] PromptEngine with metadata tracking
- [x] BlockRegistry for discovery
- [x] Simple CLI for testing

### 🚧 In Progress

- [ ] Integration with automated_brainstorm.py
- [ ] Integration with interactive_brainstorm.py
- [ ] End-to-end testing

### 📋 Future (Phase 2)

- [ ] Web UI (React + FastAPI)
- [ ] Drag-and-drop visual composer
- [ ] Save/load block configurations
- [ ] Preset "recipes" for common tasks
- [ ] Block validation UI
- [ ] Live prompt preview

---

## 🧪 Testing

### Run the CLI

```bash
cd /Users/elle_jansick/LIZZY_ROMCOM
python3 prompt_studio_cli.py
```

Try:
1. List blocks
2. Show info
3. Run examples
4. Custom composition

### Python API

```python
from lizzy.prompt_studio import PromptEngine, BlockRegistry
from lizzy.prompt_studio.blocks import SceneBlock

# List all blocks
print(BlockRegistry.list_blocks())

# Create and execute
block = SceneBlock(scene_number=1)
output = block.execute(project_name="The Proposal 2.0")
print(output)
```

---

## 💡 Design Philosophy

### Why Blocks?

1. **Composability** - Mix and match data sources
2. **Reusability** - Save configurations
3. **Testability** - Easy to test individual blocks
4. **Visibility** - See exactly what data goes into prompts
5. **Flexibility** - Build custom workflows

### Why Backend-First?

1. **Foundation** - Get the engine right
2. **API** - Define clean interfaces
3. **Testing** - Validate logic before UI
4. **Iteration** - Easy to refine based on usage

### Future: Visual UI

Once the backend is solid, add:
- Drag-and-drop visual composer
- Live preview
- Save/share configurations
- One-click execution

---

## 📚 Related Documentation

- **FUNCTION_LIST.md** - All brainstorm functions
- **PROMPT_ARCHITECTURE.md** - Current prompt design
- **SQL_TO_PROMPT_FLOW.md** - How data flows to prompts
- **MODULE_STATUS_REPORT.md** - Overall project status

---

## 🔗 Quick Links

- **CLI**: `prompt_studio_cli.py`
- **Core Engine**: `lizzy/prompt_studio/engine.py`
- **Block Types**: `lizzy/prompt_studio/blocks/`
- **Registry**: `lizzy/prompt_studio/registry.py`

---

**Status**: Backend complete, ready for integration testing
**Next**: Integrate with automated/interactive brainstorm modules
**Future**: Build web UI for visual composition
