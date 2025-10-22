"""
Prompt Assembly Engine

Executes blocks and combines their outputs into a final prompt.
"""

import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from .blocks.base import Block, BlockMetadata


@dataclass
class PromptResult:
    """Result of assembling a prompt from blocks"""
    prompt: str
    metadata: List[BlockMetadata]
    total_execution_time_ms: float
    total_chars: int
    errors: List[str] = field(default_factory=list)


class PromptEngine:
    """
    Engine for executing blocks and assembling prompts.

    Takes a list of blocks, executes them in order, and combines
    their outputs into a final prompt string.
    """

    def __init__(self):
        self.last_result: Optional[PromptResult] = None

    def assemble(
        self,
        blocks: List[Block],
        project_name: str,
        separator: str = "\n\n",
        **kwargs
    ) -> PromptResult:
        """
        Execute all blocks and assemble into a prompt.

        Args:
            blocks: List of Block instances to execute
            project_name: Name of the project
            separator: String to join block outputs (default: two newlines)
            **kwargs: Additional context to pass to blocks

        Returns:
            PromptResult with assembled prompt and metadata
        """
        start_time = time.time()

        outputs = []
        metadata_list = []
        errors = []

        for block in blocks:
            # Validate block
            is_valid, error_msg = block.validate()
            if not is_valid:
                error = f"Block {block.block_id} validation failed: {error_msg}"
                errors.append(error)
                outputs.append(f"[ERROR: {error}]")
                continue

            # Execute block
            block_start = time.time()
            try:
                output = block.execute(project_name, **kwargs)
                block_end = time.time()

                # Create metadata
                metadata = BlockMetadata(
                    block_type=block.get_type(),
                    block_id=block.block_id,
                    execution_time_ms=(block_end - block_start) * 1000,
                    data_size_chars=len(output)
                )
                block.metadata = metadata
                metadata_list.append(metadata)

                outputs.append(output)

            except Exception as e:
                block_end = time.time()
                error = f"Block {block.block_id} execution failed: {str(e)}"
                errors.append(error)

                metadata = BlockMetadata(
                    block_type=block.get_type(),
                    block_id=block.block_id,
                    execution_time_ms=(block_end - block_start) * 1000,
                    data_size_chars=0,
                    error=str(e)
                )
                metadata_list.append(metadata)

                outputs.append(f"[ERROR: {error}]")

        # Combine outputs
        final_prompt = separator.join(outputs)
        end_time = time.time()

        # Create result
        result = PromptResult(
            prompt=final_prompt,
            metadata=metadata_list,
            total_execution_time_ms=(end_time - start_time) * 1000,
            total_chars=len(final_prompt),
            errors=errors
        )

        self.last_result = result
        return result

    def get_last_result(self) -> Optional[PromptResult]:
        """Get the result from the last assemble() call"""
        return self.last_result


# Convenience function for quick assembly
def assemble_prompt(
    blocks: List[Block],
    project_name: str,
    separator: str = "\n\n",
    **kwargs
) -> str:
    """
    Quick helper to assemble a prompt from blocks.

    Args:
        blocks: List of Block instances
        project_name: Name of the project
        separator: String to join blocks (default: two newlines)
        **kwargs: Additional context

    Returns:
        Assembled prompt string
    """
    engine = PromptEngine()
    result = engine.assemble(blocks, project_name, separator, **kwargs)
    return result.prompt
