"""Chunking strategy for failed validation regions."""

from typing import List, Dict, Tuple, Set
from dataclasses import dataclass

from .parser import ScreenplayElement, ElementType
from .validator import ValidationError, ErrorCode
from .llm_corrector import ChunkContext


@dataclass
class ChunkBoundary:
    """Represents natural boundaries for chunking."""
    start_line: int
    end_line: int
    element_type: ElementType
    description: str


class ValidationChunker:
    """Chunks validation errors into logical regions for LLM processing."""

    # Maximum lines per chunk to avoid overwhelming LLM
    MAX_CHUNK_SIZE = 60

    # Context lines to include around errors
    CONTEXT_LINES_BEFORE = 3
    CONTEXT_LINES_AFTER = 3

    def __init__(self):
        self.logger = None  # Will be set if needed

    def create_chunks(self,
                     elements: List[ScreenplayElement],
                     errors: List[ValidationError],
                     text_lines: List[str]) -> List[ChunkContext]:
        """
        Create chunks from validation errors.

        Args:
            elements: Parsed screenplay elements
            errors: List of validation errors
            text_lines: Original text lines

        Returns:
            List of chunk contexts for LLM processing
        """
        if not errors:
            return []

        # Group errors by proximity
        error_groups = self._group_errors_by_proximity(errors)

        # Create chunks for each error group
        chunks = []
        for group in error_groups:
            chunk = self._create_chunk_for_group(group, elements, text_lines)
            if chunk:
                chunks.append(chunk)

        return chunks

    def _group_errors_by_proximity(self, errors: List[ValidationError]) -> List[List[ValidationError]]:
        """Group errors that are close together."""
        if not errors:
            return []

        # Sort errors by line number
        sorted_errors = sorted(errors, key=lambda e: e.line_number)

        groups = []
        current_group = [sorted_errors[0]]

        for error in sorted_errors[1:]:
            # If error is within reasonable distance, add to current group
            last_error_line = current_group[-1].line_number
            if error.line_number - last_error_line <= 8:  # Within 8 lines
                current_group.append(error)
            else:
                # Start new group
                groups.append(current_group)
                current_group = [error]

        # Add the last group
        if current_group:
            groups.append(current_group)

        return groups

    def _create_chunk_for_group(self,
                               error_group: List[ValidationError],
                               elements: List[ScreenplayElement],
                               text_lines: List[str]) -> ChunkContext:
        """Create a chunk context for a group of errors."""
        if not error_group:
            return None

        # Find the range of lines affected
        min_line = min(e.line_number for e in error_group)
        max_line = max(e.line_number for e in error_group)

        # Extend to natural boundaries
        start_line, end_line = self._find_natural_boundaries(
            min_line, max_line, elements, text_lines
        )

        # Extract chunk content
        chunk_lines = text_lines[start_line:end_line + 1]

        # Find elements within this chunk
        chunk_elements = [
            elem for elem in elements
            if start_line <= elem.line_number - 1 <= end_line
        ]

        return ChunkContext(
            start_line=start_line,
            end_line=end_line,
            lines=chunk_lines,
            errors=error_group,
            elements=chunk_elements
        )

    def _find_natural_boundaries(self,
                                min_error_line: int,
                                max_error_line: int,
                                elements: List[ScreenplayElement],
                                text_lines: List[str]) -> Tuple[int, int]:
        """Find natural boundaries around the error region."""
        # Convert to 0-based indexing for text_lines
        min_line_idx = min_error_line - 1
        max_line_idx = max_error_line - 1

        # Add context lines
        start_line = max(0, min_line_idx - self.CONTEXT_LINES_BEFORE)
        end_line = min(len(text_lines) - 1, max_line_idx + self.CONTEXT_LINES_AFTER)

        # Extend to natural screenplay boundaries
        start_line = self._find_boundary_start(start_line, elements)
        end_line = self._find_boundary_end(end_line, elements, text_lines)

        # Ensure we don't exceed max chunk size
        if end_line - start_line + 1 > self.MAX_CHUNK_SIZE:
            # Trim to max size, keeping errors in center
            center = (min_line_idx + max_line_idx) // 2
            half_size = self.MAX_CHUNK_SIZE // 2
            start_line = max(0, center - half_size)
            end_line = min(len(text_lines) - 1, start_line + self.MAX_CHUNK_SIZE - 1)

        return start_line, end_line

    def _find_boundary_start(self, start_line: int, elements: List[ScreenplayElement]) -> int:
        """Find a natural start boundary (e.g., beginning of a scene or dialogue block)."""
        # Look backwards for natural boundaries
        for elem in reversed(elements):
            elem_line_idx = elem.line_number - 1  # Convert to 0-based

            if elem_line_idx >= start_line:
                continue  # Skip elements after our start

            if elem_line_idx < start_line - 5:
                break  # Don't look too far back

            # Natural start points
            if elem.type in [ElementType.SCENE_HEADING, ElementType.TRANSITION]:
                return elem_line_idx
            elif elem.type == ElementType.CHARACTER:
                # Start of dialogue block
                return elem_line_idx

        return start_line

    def _find_boundary_end(self, end_line: int, elements: List[ScreenplayElement], text_lines: List[str]) -> int:
        """Find a natural end boundary."""
        # Look forwards for natural boundaries
        for elem in elements:
            elem_line_idx = elem.line_number - 1  # Convert to 0-based

            if elem_line_idx <= end_line:
                continue  # Skip elements before our end

            if elem_line_idx > end_line + 5:
                break  # Don't look too far ahead

            # Natural end points
            if elem.type in [ElementType.SCENE_HEADING, ElementType.TRANSITION]:
                return elem_line_idx - 1  # End before the next scene/transition
            elif elem.type == ElementType.CHARACTER:
                # If we hit a new character, end the current chunk
                return elem_line_idx - 1

        return end_line

    def get_chunk_summary(self, chunk: ChunkContext) -> str:
        """Get a human-readable summary of the chunk."""
        error_codes = [e.error_code.value for e in chunk.errors]
        element_types = list(set(e.type.name for e in chunk.elements))

        return (f"Lines {chunk.start_line + 1}-{chunk.end_line + 1}: "
                f"{len(chunk.errors)} errors ({', '.join(error_codes)}), "
                f"elements: {', '.join(element_types)}")

    def validate_chunks(self, chunks: List[ChunkContext]) -> List[ChunkContext]:
        """Validate and filter chunks before sending to LLM."""
        valid_chunks = []

        for chunk in chunks:
            # Skip chunks that are too small or too large
            if len(chunk.lines) < 1:
                continue
            if len(chunk.lines) > self.MAX_CHUNK_SIZE:
                continue

            # Skip chunks with no actual errors
            if not chunk.errors:
                continue

            # Skip chunks that are mostly blank lines
            non_blank_lines = [line for line in chunk.lines if line.strip()]
            if len(non_blank_lines) < 1:
                continue

            valid_chunks.append(chunk)

        return valid_chunks

    def chunk_stats(self, chunks: List[ChunkContext]) -> Dict[str, any]:
        """Get statistics about the chunks."""
        if not chunks:
            return {
                'total_chunks': 0,
                'total_lines': 0,
                'total_errors': 0,
                'avg_chunk_size': 0,
                'error_types': {}
            }

        total_lines = sum(len(chunk.lines) for chunk in chunks)
        total_errors = sum(len(chunk.errors) for chunk in chunks)

        # Count error types
        error_types = {}
        for chunk in chunks:
            for error in chunk.errors:
                error_type = error.error_code.name
                error_types[error_type] = error_types.get(error_type, 0) + 1

        return {
            'total_chunks': len(chunks),
            'total_lines': total_lines,
            'total_errors': total_errors,
            'avg_chunk_size': total_lines / len(chunks) if chunks else 0,
            'error_types': error_types
        }