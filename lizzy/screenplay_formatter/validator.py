"""Validator module for screenplay formatting rules."""

import re
import json
from enum import Enum
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from pydantic import BaseModel, Field

from .parser import ScreenplayElement, ElementType


class ErrorCode(Enum):
    """Error codes for validation issues."""
    E1_INVALID_SCENE_HEADING = "E1"
    E2_INCORRECT_CHARACTER_FORMAT = "E2"
    E3_INCORRECT_DIALOGUE_FORMAT = "E3"
    E4_INCORRECT_PARENTHETICAL = "E4"
    E5_INCORRECT_TRANSITION = "E5"
    E6_INVALID_BLOCK_SEQUENCE = "E6"
    E7_INCORRECT_INDENTATION = "E7"
    E8_MISSING_ELEMENT = "E8"


@dataclass
class ValidationError:
    """Represents a validation error."""
    line_number: int
    error_code: ErrorCode
    message: str
    element_type: ElementType
    content: str
    suggestion: Optional[str] = None
    confidence: float = 0.0


class ValidationReport(BaseModel):
    """Validation report with all errors and statistics."""
    total_lines: int = Field(description="Total lines in screenplay")
    total_errors: int = Field(description="Total validation errors")
    errors_by_type: Dict[str, int] = Field(default_factory=dict)
    errors: List[Dict] = Field(default_factory=list)
    passed: bool = Field(description="Whether validation passed")


class ScreenplayValidator:
    """Validate screenplay formatting according to industry standards."""

    def __init__(self, strict_mode: bool = False):
        """
        Initialize validator.

        Args:
            strict_mode: If True, enforce stricter validation rules
        """
        self.strict_mode = strict_mode
        self.errors: List[ValidationError] = []

    def validate(self, elements: List[ScreenplayElement]) -> ValidationReport:
        """
        Validate screenplay elements.

        Args:
            elements: List of screenplay elements to validate

        Returns:
            ValidationReport with all errors and statistics
        """
        self.errors = []

        # Run all validation checks
        self._validate_scene_headings(elements)
        self._validate_character_formatting(elements)
        self._validate_dialogue_formatting(elements)
        self._validate_parentheticals(elements)
        self._validate_transitions(elements)
        self._validate_block_sequencing(elements)
        self._validate_indentation(elements)

        # Create report
        report = self._create_report(elements)
        return report

    def _validate_scene_headings(self, elements: List[ScreenplayElement]):
        """Validate scene heading format per style guide."""
        # Updated pattern to match your guide's requirements
        scene_pattern = re.compile(
            r"^(INT\.|EXT\.|INT\./EXT\.|EXT\./INT\.)\s+[A-Z0-9\s\-,.'\"&()]+\s*(-\s*(DAY|NIGHT|DAWN|DUSK|MORNING|AFTERNOON|EVENING|CONTINUOUS|LATER|MOMENTS LATER|SAME)(\s*\([^)]+\))?)?$"
        )

        for element in elements:
            if element.type == ElementType.SCENE_HEADING:
                if not scene_pattern.match(element.content.upper()):
                    # Try to suggest a fix
                    suggestion = self._suggest_scene_heading_fix(element.content)
                    self.errors.append(ValidationError(
                        line_number=element.line_number,
                        error_code=ErrorCode.E1_INVALID_SCENE_HEADING,
                        message=f"Invalid scene heading format: {element.content}",
                        element_type=element.type,
                        content=element.content,
                        suggestion=suggestion,
                        confidence=0.8 if suggestion else 0.3
                    ))

    def _suggest_scene_heading_fix(self, text: str) -> Optional[str]:
        """Suggest a fix for invalid scene heading."""
        upper_text = text.upper()

        # Check if it starts with a variant of INT/EXT
        if any(upper_text.startswith(prefix) for prefix in ["INT ", "EXT ", "INT.", "EXT."]):
            # Ensure proper format
            if "INT " in upper_text:
                upper_text = upper_text.replace("INT ", "INT. ")
            if "EXT " in upper_text:
                upper_text = upper_text.replace("EXT ", "EXT. ")

            # Add time of day if missing
            if not any(tod in upper_text for tod in ["DAY", "NIGHT", "DAWN", "DUSK", "MORNING", "EVENING"]):
                upper_text += " - DAY"

            return upper_text

        return None

    def _validate_character_formatting(self, elements: List[ScreenplayElement]):
        """Validate character name formatting."""
        for element in elements:
            if element.type == ElementType.CHARACTER:
                # Character names should be ALL CAPS
                if not element.content.isupper():
                    self.errors.append(ValidationError(
                        line_number=element.line_number,
                        error_code=ErrorCode.E2_INCORRECT_CHARACTER_FORMAT,
                        message=f"Character name should be in ALL CAPS: {element.content}",
                        element_type=element.type,
                        content=element.content,
                        suggestion=element.content.upper(),
                        confidence=0.95
                    ))

    def _validate_dialogue_formatting(self, elements: List[ScreenplayElement]):
        """Validate dialogue formatting and placement."""
        for i, element in enumerate(elements):
            if element.type == ElementType.DIALOGUE:
                # Check if preceded by character or parenthetical
                prev_element = elements[i-1] if i > 0 else None
                if prev_element and prev_element.type not in [ElementType.CHARACTER, ElementType.PARENTHETICAL, ElementType.DIALOGUE]:
                    self.errors.append(ValidationError(
                        line_number=element.line_number,
                        error_code=ErrorCode.E6_INVALID_BLOCK_SEQUENCE,
                        message="Dialogue must follow character name or parenthetical",
                        element_type=element.type,
                        content=element.content,
                        confidence=0.9
                    ))

    def _validate_parentheticals(self, elements: List[ScreenplayElement]):
        """Validate parenthetical formatting."""
        paren_pattern = re.compile(r"^\([^)]+\)$")

        for i, element in enumerate(elements):
            if element.type == ElementType.PARENTHETICAL:
                # Check format
                if not paren_pattern.match(element.content):
                    suggestion = f"({element.content.strip('()')})"
                    self.errors.append(ValidationError(
                        line_number=element.line_number,
                        error_code=ErrorCode.E4_INCORRECT_PARENTHETICAL,
                        message="Parenthetical must be enclosed in parentheses",
                        element_type=element.type,
                        content=element.content,
                        suggestion=suggestion,
                        confidence=0.9
                    ))

                # Check placement
                prev_element = elements[i-1] if i > 0 else None
                if prev_element and prev_element.type not in [ElementType.CHARACTER, ElementType.DIALOGUE]:
                    self.errors.append(ValidationError(
                        line_number=element.line_number,
                        error_code=ErrorCode.E6_INVALID_BLOCK_SEQUENCE,
                        message="Parenthetical must follow character name or be within dialogue",
                        element_type=element.type,
                        content=element.content,
                        confidence=0.85
                    ))

    def _validate_transitions(self, elements: List[ScreenplayElement]):
        """Validate transition formatting."""
        valid_transitions = [
            "FADE IN:", "FADE OUT.", "FADE TO:", "CUT TO:",
            "DISSOLVE TO:", "MATCH CUT TO:", "JUMP CUT TO:",
            "SMASH CUT TO:", "TIME CUT:", "FADE TO BLACK.", "THE END"
        ]

        for element in elements:
            if element.type == ElementType.TRANSITION:
                upper_content = element.content.upper()
                if upper_content not in valid_transitions:
                    # Try to find closest match
                    suggestion = self._find_closest_transition(upper_content, valid_transitions)
                    self.errors.append(ValidationError(
                        line_number=element.line_number,
                        error_code=ErrorCode.E5_INCORRECT_TRANSITION,
                        message=f"Non-standard transition: {element.content}",
                        element_type=element.type,
                        content=element.content,
                        suggestion=suggestion,
                        confidence=0.7 if suggestion else 0.4
                    ))

    def _find_closest_transition(self, text: str, valid_transitions: List[str]) -> Optional[str]:
        """Find the closest valid transition."""
        upper_text = text.upper()

        # Check for common patterns
        if "FADE" in upper_text:
            if "IN" in upper_text:
                return "FADE IN:"
            elif "OUT" in upper_text:
                return "FADE OUT."
            else:
                return "FADE TO:"
        elif "CUT" in upper_text:
            if "MATCH" in upper_text:
                return "MATCH CUT TO:"
            elif "JUMP" in upper_text:
                return "JUMP CUT TO:"
            elif "SMASH" in upper_text:
                return "SMASH CUT TO:"
            else:
                return "CUT TO:"
        elif "DISSOLVE" in upper_text:
            return "DISSOLVE TO:"
        elif "END" in upper_text:
            return "THE END"

        return None

    def _validate_block_sequencing(self, elements: List[ScreenplayElement]):
        """Validate the sequence of screenplay blocks."""
        for i in range(1, len(elements)):
            current = elements[i]
            previous = elements[i-1]

            # Skip blank lines
            if current.type == ElementType.BLANK or previous.type == ElementType.BLANK:
                continue

            # Check for orphaned dialogue
            if current.type == ElementType.DIALOGUE:
                if previous.type not in [ElementType.CHARACTER, ElementType.PARENTHETICAL, ElementType.DIALOGUE]:
                    self.errors.append(ValidationError(
                        line_number=current.line_number,
                        error_code=ErrorCode.E6_INVALID_BLOCK_SEQUENCE,
                        message="Dialogue without character name",
                        element_type=current.type,
                        content=current.content,
                        confidence=0.9
                    ))

            # Check for orphaned parentheticals
            if current.type == ElementType.PARENTHETICAL:
                if previous.type not in [ElementType.CHARACTER, ElementType.DIALOGUE]:
                    self.errors.append(ValidationError(
                        line_number=current.line_number,
                        error_code=ErrorCode.E6_INVALID_BLOCK_SEQUENCE,
                        message="Parenthetical without character or dialogue context",
                        element_type=current.type,
                        content=current.content,
                        confidence=0.85
                    ))

    def _validate_indentation(self, elements: List[ScreenplayElement]):
        """Validate indentation of elements (for text format)."""
        # This would check actual indentation in the raw text
        # For now, we'll skip detailed indentation validation
        pass

    def _create_report(self, elements: List[ScreenplayElement]) -> ValidationReport:
        """Create validation report."""
        errors_by_type = {}
        for error in self.errors:
            error_type = error.error_code.name
            errors_by_type[error_type] = errors_by_type.get(error_type, 0) + 1

        # Convert errors to dict format
        error_dicts = []
        for error in self.errors:
            error_dict = {
                "line_number": error.line_number,
                "error_code": error.error_code.value,
                "message": error.message,
                "element_type": error.element_type.name,
                "content": error.content,
                "suggestion": error.suggestion,
                "confidence": error.confidence
            }
            error_dicts.append(error_dict)

        report = ValidationReport(
            total_lines=len(elements),
            total_errors=len(self.errors),
            errors_by_type=errors_by_type,
            errors=error_dicts,
            passed=(len(self.errors) == 0)
        )

        return report

    def export_json(self, report: ValidationReport, output_path: str):
        """Export validation report as JSON."""
        with open(output_path, 'w') as f:
            json.dump(report.model_dump(), f, indent=2)

    def export_text(self, report: ValidationReport) -> str:
        """Export validation report as formatted text."""
        lines = []
        lines.append("=" * 60)
        lines.append("SCREENPLAY VALIDATION REPORT")
        lines.append("=" * 60)
        lines.append(f"Total Lines: {report.total_lines}")
        lines.append(f"Total Errors: {report.total_errors}")
        lines.append(f"Status: {'PASSED' if report.passed else 'FAILED'}")
        lines.append("")

        if report.errors_by_type:
            lines.append("Errors by Type:")
            for error_type, count in report.errors_by_type.items():
                lines.append(f"  {error_type}: {count}")
            lines.append("")

        if report.errors:
            lines.append("Detailed Errors:")
            lines.append("-" * 60)
            for error in report.errors:
                lines.append(f"Line {error['line_number']}: {error['error_code']} - {error['message']}")
                if error['suggestion']:
                    lines.append(f"  Suggestion: {error['suggestion']}")
                lines.append("")

        return "\n".join(lines)