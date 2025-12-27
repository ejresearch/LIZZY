# Prompt Studio

**Block-based prompt composition system for Lizzy**

## Quick Start

### Python API

```python
from backend.prompt_studio import assemble_prompt
from backend.prompt_studio.blocks import SceneBlock, CharacterBiosBlock

blocks = [
    SceneBlock(scene_number=5),
    CharacterBiosBlock(),
]

prompt = assemble_prompt(blocks, project_name="the_proposal_2_0")
print(prompt)
```

### CLI

```bash
python3 prompt_studio_cli.py
```

## Available Blocks

### SQL Blocks (7)
- `SceneBlock(scene_number)` - Scene data
- `CharacterBiosBlock()` - All characters
- `WriterNotesBlock(category=None)` - Notes
- `ProjectMetadataBlock()` - Project info
- `AllScenesBlock()` - Scene list
- `PreviousSceneBlock(scene_number)` - Previous scene
- `NextSceneBlock(scene_number)` - Next scene

### RAG Blocks (4)
- `BooksQueryBlock(query, mode="hybrid")` - Structure expert
- `PlaysQueryBlock(query, mode="hybrid")` - Dialogue expert
- `ScriptsQueryBlock(query, mode="hybrid")` - Visual expert
- `MultiExpertQueryBlock(query, mode="hybrid")` - All 3 experts

### Static Blocks (3)
- `TextBlock(text)` - Static text
- `TemplateBlock(template, variables)` - Templates
- `SectionHeaderBlock(title)` - Headers

## Examples

### Basic Scene Prompt

```python
from backend.prompt_studio.blocks import SceneBlock, SectionHeaderBlock

blocks = [
    SectionHeaderBlock(title="SCENE CONTEXT"),
    SceneBlock(scene_number=1),
]

prompt = assemble_prompt(blocks, project_name="my_project")
```

### RAG Query

```python
from backend.prompt_studio.blocks import BooksQueryBlock

blocks = [
    BooksQueryBlock(query="romantic comedy structure", mode="hybrid"),
]

prompt = assemble_prompt(blocks, project_name="my_project")
```

### With Metadata

```python
from backend.prompt_studio import PromptEngine

engine = PromptEngine()
result = engine.assemble(blocks, project_name="my_project")

print(result.prompt)
print(f"Execution time: {result.total_execution_time_ms}ms")
print(f"Total chars: {result.total_chars}")
```

## Documentation

- **Architecture**: `/docs/PROMPT_STUDIO_ARCHITECTURE.md`
- **Implementation**: `/docs/PROMPT_STUDIO_IMPLEMENTATION.md`
- **Examples**: `example_prompt_studio.py`

## Status

✅ **Phase 1 Complete** - Backend fully implemented
🚧 **Phase 2 Next** - Integration with brainstorm modules
📋 **Phase 3 Future** - Web UI

## Quick Reference

```python
# Import everything
from backend.prompt_studio import (
    PromptEngine,
    assemble_prompt,
    BlockRegistry,
)
from backend.prompt_studio.blocks import (
    # SQL
    SceneBlock,
    CharacterBiosBlock,
    WriterNotesBlock,
    ProjectMetadataBlock,
    AllScenesBlock,
    PreviousSceneBlock,
    NextSceneBlock,
    # RAG
    BooksQueryBlock,
    PlaysQueryBlock,
    ScriptsQueryBlock,
    MultiExpertQueryBlock,
    # Static
    TextBlock,
    TemplateBlock,
    SectionHeaderBlock,
)

# List all blocks
blocks = BlockRegistry.list_blocks()

# Get block info
info = BlockRegistry.get_block_info()

# Create block by name
block = BlockRegistry.create_block('scene', scene_number=5)
```

## Testing

```bash
# Quick test
python3 -c "from backend.prompt_studio import BlockRegistry; print(len(BlockRegistry.list_blocks()), 'blocks available')"

# Run examples
python3 example_prompt_studio.py

# Run CLI
python3 prompt_studio_cli.py
```
