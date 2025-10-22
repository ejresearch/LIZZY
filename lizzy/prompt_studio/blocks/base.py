"""
Base Block class for Prompt Studio

All block types inherit from this base class.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class BlockMetadata:
    """Metadata about a block's execution"""
    block_type: str
    block_id: str
    execution_time_ms: float
    data_size_chars: int
    error: Optional[str] = None


class Block(ABC):
    """
    Base class for all Prompt Studio blocks.

    Each block represents a data source or transformation that can be
    composed into a final prompt.
    """

    def __init__(self, block_id: str = None):
        """
        Initialize block.

        Args:
            block_id: Optional unique identifier for this block instance
        """
        self.block_id = block_id or f"{self.__class__.__name__}_{id(self)}"
        self.metadata: Optional[BlockMetadata] = None

    @abstractmethod
    def execute(self, project_name: str, **kwargs) -> str:
        """
        Execute the block and return formatted string data.

        Args:
            project_name: Name of the current project
            **kwargs: Additional context (scene_number, etc.)

        Returns:
            Formatted string to be included in the prompt
        """
        pass

    @abstractmethod
    def get_description(self) -> str:
        """
        Return human-readable description of what this block does.

        Returns:
            Description string
        """
        pass

    def get_type(self) -> str:
        """
        Get the block type name.

        Returns:
            Block type as string
        """
        return self.__class__.__name__

    def validate(self) -> tuple[bool, Optional[str]]:
        """
        Validate block configuration.

        Returns:
            (is_valid, error_message)
        """
        return (True, None)

    def __repr__(self) -> str:
        return f"<{self.get_type()} id={self.block_id}>"
