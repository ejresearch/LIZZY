"""
Prompt Studio Blocks

Available block types:
- SQL Blocks: SceneBlock, CharacterBiosBlock, WriterNotesBlock, ProjectMetadataBlock
- RAG Blocks: BooksQueryBlock, PlaysQueryBlock, ScriptsQueryBlock
- Static Blocks: TextBlock, TemplateBlock
"""

from .base import Block, BlockMetadata
from .sql_blocks import (
    SceneBlock,
    CharacterBiosBlock,
    WriterNotesBlock,
    ProjectMetadataBlock,
    AllScenesBlock,
    PreviousSceneBlock,
    NextSceneBlock,
)
from .rag_blocks import (
    BooksQueryBlock,
    PlaysQueryBlock,
    ScriptsQueryBlock,
    MultiExpertQueryBlock,
)
from .static_blocks import (
    TextBlock,
    TemplateBlock,
    SectionHeaderBlock,
)

__all__ = [
    'Block',
    'BlockMetadata',
    # SQL Blocks
    'SceneBlock',
    'CharacterBiosBlock',
    'WriterNotesBlock',
    'ProjectMetadataBlock',
    'AllScenesBlock',
    'PreviousSceneBlock',
    'NextSceneBlock',
    # RAG Blocks
    'BooksQueryBlock',
    'PlaysQueryBlock',
    'ScriptsQueryBlock',
    'MultiExpertQueryBlock',
    # Static Blocks
    'TextBlock',
    'TemplateBlock',
    'SectionHeaderBlock',
]
