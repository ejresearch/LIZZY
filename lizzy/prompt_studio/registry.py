"""
Block Registry

Provides discovery and instantiation of available block types.
"""

from typing import Dict, Type, List, Any
from .blocks.base import Block
from .blocks import (
    # SQL Blocks
    SceneBlock,
    CharacterBiosBlock,
    WriterNotesBlock,
    ProjectMetadataBlock,
    AllScenesBlock,
    PreviousSceneBlock,
    NextSceneBlock,
    # RAG Blocks
    BooksQueryBlock,
    PlaysQueryBlock,
    ScriptsQueryBlock,
    MultiExpertQueryBlock,
    # Static Blocks
    TextBlock,
    TemplateBlock,
    SectionHeaderBlock,
)


class BlockRegistry:
    """
    Registry of all available block types.

    Provides discovery, documentation, and instantiation.
    """

    # Registry of all block classes
    BLOCKS: Dict[str, Type[Block]] = {
        # SQL Blocks
        'scene': SceneBlock,
        'character_bios': CharacterBiosBlock,
        'writer_notes': WriterNotesBlock,
        'project_metadata': ProjectMetadataBlock,
        'all_scenes': AllScenesBlock,
        'previous_scene': PreviousSceneBlock,
        'next_scene': NextSceneBlock,
        # RAG Blocks
        'books_query': BooksQueryBlock,
        'plays_query': PlaysQueryBlock,
        'scripts_query': ScriptsQueryBlock,
        'multi_expert_query': MultiExpertQueryBlock,
        # Static Blocks
        'text': TextBlock,
        'template': TemplateBlock,
        'section_header': SectionHeaderBlock,
    }

    @classmethod
    def list_blocks(cls) -> List[str]:
        """Get list of all registered block type names"""
        return list(cls.BLOCKS.keys())

    @classmethod
    def get_block_class(cls, block_type: str) -> Type[Block]:
        """
        Get the block class for a given type name.

        Args:
            block_type: Name of the block type (e.g., 'scene', 'books_query')

        Returns:
            Block class

        Raises:
            KeyError: If block type not found
        """
        if block_type not in cls.BLOCKS:
            raise KeyError(f"Unknown block type: {block_type}")
        return cls.BLOCKS[block_type]

    @classmethod
    def create_block(cls, block_type: str, **kwargs) -> Block:
        """
        Create a block instance.

        Args:
            block_type: Name of the block type
            **kwargs: Arguments to pass to block constructor

        Returns:
            Block instance

        Raises:
            KeyError: If block type not found
        """
        block_class = cls.get_block_class(block_type)
        return block_class(**kwargs)

    @classmethod
    def get_block_info(cls) -> Dict[str, Dict[str, Any]]:
        """
        Get information about all registered blocks.

        Returns:
            Dictionary mapping block type to info dict
        """
        info = {}

        for block_type, block_class in cls.BLOCKS.items():
            # Create a temporary instance to get description
            # (This is a bit hacky but works for now)
            try:
                if block_type == 'scene':
                    temp = block_class(scene_number=1)
                elif block_type in ['previous_scene', 'next_scene']:
                    temp = block_class(scene_number=1)
                elif block_type in ['books_query', 'plays_query', 'scripts_query', 'multi_expert_query']:
                    temp = block_class(query="example query")
                elif block_type == 'text':
                    temp = block_class(text="example")
                elif block_type == 'template':
                    temp = block_class(template="example")
                elif block_type == 'section_header':
                    temp = block_class(title="example")
                elif block_type == 'writer_notes':
                    temp = block_class(category=None)
                else:
                    temp = block_class()

                info[block_type] = {
                    'class_name': block_class.__name__,
                    'description': temp.get_description(),
                    'module': block_class.__module__,
                }
            except Exception as e:
                info[block_type] = {
                    'class_name': block_class.__name__,
                    'description': f"Error: {e}",
                    'module': block_class.__module__,
                }

        return info

    @classmethod
    def get_blocks_by_category(cls) -> Dict[str, List[str]]:
        """
        Get blocks organized by category.

        Returns:
            Dictionary mapping category to list of block types
        """
        return {
            'SQL Blocks': [
                'scene',
                'character_bios',
                'writer_notes',
                'project_metadata',
                'all_scenes',
                'previous_scene',
                'next_scene',
            ],
            'RAG Blocks': [
                'books_query',
                'plays_query',
                'scripts_query',
                'multi_expert_query',
            ],
            'Static Blocks': [
                'text',
                'template',
                'section_header',
            ],
        }
