"""
Lizzy Prompt Studio - Block-based prompt composition system

This module provides a visual/composable way to build prompts from data sources.
Blocks can be combined like Scratch blocks to create custom prompts that draw
from SQL tables, RAG buckets, and other data sources.

NEW: AI Block Composer - Natural language to blocks!
"""

from .engine import PromptEngine, assemble_prompt
from .blocks.base import Block
from .registry import BlockRegistry
from .ai_composer import AIBlockComposer

__all__ = ['PromptEngine', 'assemble_prompt', 'Block', 'BlockRegistry', 'AIBlockComposer']
