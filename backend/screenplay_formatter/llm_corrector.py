"""LLM-powered screenplay formatting corrector with anti-hallucination guardrails."""

import os
import json
import hashlib
import logging
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from pydantic import BaseModel, Field
import openai

from .parser import ScreenplayElement, ElementType
from .validator import ValidationError, ErrorCode


class FixSpan(BaseModel):
    """Represents a fix span from the LLM."""
    start_line: int = Field(description="Start line index (0-based within chunk)")
    end_line: int = Field(description="End line index (inclusive)")
    original: List[str] = Field(description="Original lines")
    revised: List[str] = Field(description="Revised lines")
    issues: List[str] = Field(description="Validator error codes (e.g., E1, E3)")
    confidence: float = Field(description="Confidence score 0.0-1.0", ge=0.0, le=1.0)


class CorrectionResponse(BaseModel):
    """Response schema from LLM correction."""
    version: str = Field(description="Schema version", default="1.0")
    model: str = Field(description="Model identifier")
    fixes: List[FixSpan] = Field(description="List of corrections")
    unchanged_lines: List[int] = Field(description="Line indices left unchanged")
    notes: Optional[str] = Field(description="Brief rationale (<=200 chars)", max_length=200)


@dataclass
class ChunkContext:
    """Context for a chunk being processed."""
    start_line: int
    end_line: int
    lines: List[str]
    errors: List[ValidationError]
    elements: List[ScreenplayElement]


class LLMCorrector:
    """LLM-powered screenplay formatting corrector."""

    # Allowed tokens that can be added during correction (per style guide)
    ALLOWED_ADDED_TOKENS = {
        'INT.', 'EXT.', 'INT./EXT.', 'EXT./INT.',
        'DAY', 'NIGHT', 'DAWN', 'DUSK', 'MORNING', 'AFTERNOON', 'EVENING',
        'CONTINUOUS', 'LATER', 'MOMENTS LATER', 'SAME',
        'FADE IN:', 'FADE OUT.', 'CUT TO:', 'DISSOLVE TO:', 'SMASH TO:',
        'BEGIN MONTAGE', 'END MONTAGE', 'CHYRON:', 'TITLE:',
        'O.S.', 'V.O.', 'CONT\'D', 'THE END'
    }

    def __init__(self,
                 api_key: Optional[str] = None,
                 model: str = "gpt-5.1",
                 temperature: float = 0.0,
                 top_p: float = 0.1,
                 min_confidence: float = 0.8,
                 max_edit_distance: int = 8):
        """
        Initialize LLM corrector.

        Args:
            api_key: OpenAI API key (or None to use environment)
            model: OpenAI model to use
            temperature: Generation temperature (0.0 for deterministic)
            top_p: Top-p sampling parameter
            min_confidence: Minimum confidence for auto-apply
            max_edit_distance: Maximum allowed edit distance per chunk
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY environment variable.")

        self.model = model
        self.temperature = temperature
        self.top_p = top_p
        self.min_confidence = min_confidence
        self.max_edit_distance = max_edit_distance

        # Initialize OpenAI client
        self.client = openai.OpenAI(api_key=self.api_key)

        # Setup logging
        self.logger = logging.getLogger(__name__)

    def correct_chunk(self, chunk: ChunkContext) -> Tuple[CorrectionResponse, bool]:
        """
        Correct a single chunk using LLM.

        Args:
            chunk: Chunk context with errors and content

        Returns:
            Tuple of (correction_response, applied_successfully)
        """
        # Generate prompt
        prompt = self._generate_prompt(chunk)
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:8]

        self.logger.info(f"Correcting chunk lines {chunk.start_line}-{chunk.end_line}, "
                        f"errors: {[e.error_code.value for e in chunk.errors]}, "
                        f"prompt_hash: {prompt_hash}")

        try:
            # Call LLM
            response = self._call_llm(prompt)
            correction = self._parse_response(response)
            correction.model = f"{self.model}@{prompt_hash}"

            # Validate and apply corrections
            if self._validate_correction(chunk, correction):
                applied = self._apply_correction(chunk, correction)
                self.logger.info(f"Correction applied: {applied}, "
                               f"fixes: {len(correction.fixes)}, "
                               f"avg_confidence: {self._avg_confidence(correction):.2f}")
                return correction, applied
            else:
                self.logger.warning(f"Correction rejected due to validation failure")
                return correction, False

        except Exception as e:
            self.logger.error(f"LLM correction failed: {e}")
            # Return empty correction on error
            return CorrectionResponse(
                model=self.model,
                fixes=[],
                unchanged_lines=list(range(len(chunk.lines))),
                notes=f"Error: {str(e)[:100]}"
            ), False

    def _generate_prompt(self, chunk: ChunkContext) -> str:
        """Generate the correction prompt for a chunk."""
        # Extract error codes
        error_codes = [e.error_code.value for e in chunk.errors]

        # Build input text
        input_text = '\n'.join(chunk.lines)

        system_prompt = """You are a screenplay formatting corrector. You must enforce industry formatting rules without inventing story content.

ALLOWED: capitalization, whitespace/indentation normalization; moving lines between blocks; adding missing INT./EXT./TIME only when unambiguous.
FORBIDDEN: adding words/lines/characters; rewriting dialogue; creative changes.

If uncertain, output a suggestion with low confidence rather than altering the text.
Output strictly as JSON matching the provided schema. No prose."""

        user_prompt = f"""STYLE_GUIDE (per industry standards):
- Scene headings: ALL CAPS: INT./EXT. + SPECIFIC LOCATION + TIME (DAY/NIGHT/EVENING/CONTINUOUS/LATER).
- Character names: ALL CAPS, centered (~3.7" from left margin).
- Dialogue: Standard capitalization, indented ~2.5" left, ~1.5" right margin.
- Parentheticals: Under character name, indented ~3.1", in parentheses (angrily), (O.S.), (V.O.).
- Transitions: ALL CAPS, flush right (FADE IN:, FADE OUT., CUT TO:, DISSOLVE TO:, SMASH TO:).
- Action lines: Present tense, first character mention in ALL CAPS, short paragraphs (3-4 lines max).
- Page timing: 1 page ≈ 1 minute screen time with Courier 12pt font.
- Page breaks: Character dialogue blocks must NEVER break across pages. Keep character names with their dialogue.

REMOVE THESE NON-SCREENPLAY ELEMENTS:
- File headers (PROJECT NAMES, export timestamps, version info)
- Metadata lines (Exported:, Generated:, Created:, Version:)
- Separator lines (======, ------, ******, ####)
- Scene/Act numbers that aren't part of screenplay format (ACT 1, SCENE 1)
- Date stamps and technical information

DETECTED_ISSUES: {', '.join(error_codes)}

INPUT_CHUNK:
<<<
{input_text}
>>>

TASK:
Identify formatting issues, propose minimal fixes, and return JSON with the following schema:
{{
  "version": "1.0",
  "model": "model_name",
  "fixes": [
    {{
      "start_line": 0,
      "end_line": 0,
      "original": ["original line"],
      "revised": ["corrected line"],
      "issues": ["E1", "E2"],
      "confidence": 0.9
    }}
  ],
  "unchanged_lines": [1, 2, 3],
  "notes": "Brief explanation"
}}"""

        return user_prompt  # We'll use system message in the API call

    def _call_llm(self, prompt: str) -> str:
        """Call the OpenAI API with the prompt."""
        messages = [
            {
                "role": "system",
                "content": """You are a screenplay formatting corrector. You must enforce industry formatting rules without inventing story content.

ALLOWED: capitalization, whitespace/indentation normalization; moving lines between blocks; adding missing INT./EXT./TIME only when unambiguous.
FORBIDDEN: adding words/lines/characters; rewriting dialogue; creative changes.

If uncertain, output a suggestion with low confidence rather than altering the text.
Output strictly as JSON matching the provided schema. No prose."""
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            top_p=self.top_p,
            max_tokens=2000,
            response_format={"type": "json_object"},
            stop=["\n\n", "```"]
        )

        return response.choices[0].message.content

    def _parse_response(self, response_text: str) -> CorrectionResponse:
        """Parse LLM response into structured format."""
        try:
            data = json.loads(response_text)
            return CorrectionResponse(**data)
        except (json.JSONDecodeError, ValueError) as e:
            self.logger.error(f"Failed to parse LLM response: {e}")
            # Return empty response on parse failure
            return CorrectionResponse(
                model=self.model,
                fixes=[],
                unchanged_lines=[],
                notes=f"Parse error: {str(e)[:100]}"
            )

    def _validate_correction(self, chunk: ChunkContext, correction: CorrectionResponse) -> bool:
        """Validate that the correction is safe to apply."""
        for fix in correction.fixes:
            # Check confidence threshold
            if fix.confidence < self.min_confidence:
                self.logger.debug(f"Fix rejected: confidence {fix.confidence} < {self.min_confidence}")
                continue

            # Check edit distance
            edit_distance = self._calculate_edit_distance(fix.original, fix.revised)
            if edit_distance > self.max_edit_distance:
                self.logger.warning(f"Fix rejected: edit distance {edit_distance} > {self.max_edit_distance}")
                return False

            # Check for forbidden additions
            if not self._check_allowed_additions(fix.original, fix.revised):
                self.logger.warning(f"Fix rejected: contains forbidden additions")
                return False

        return True

    def _calculate_edit_distance(self, original: List[str], revised: List[str]) -> int:
        """Calculate simple edit distance between line lists."""
        # Simple token-based edit distance
        orig_tokens = set(' '.join(original).split())
        rev_tokens = set(' '.join(revised).split())

        added = rev_tokens - orig_tokens
        removed = orig_tokens - rev_tokens

        return len(added) + len(removed)

    def _check_allowed_additions(self, original: List[str], revised: List[str]) -> bool:
        """Check that only allowed tokens were added."""
        orig_text = ' '.join(original).upper()
        rev_text = ' '.join(revised).upper()

        orig_tokens = set(orig_text.split())
        rev_tokens = set(rev_text.split())

        added_tokens = rev_tokens - orig_tokens

        # Check if all added tokens are in the allowed set
        for token in added_tokens:
            if token not in self.ALLOWED_ADDED_TOKENS:
                # Allow punctuation and common formatting characters
                if token not in {'-', '–', ':', '.', '(', ')', ',', "'", '"'}:
                    self.logger.warning(f"Forbidden token added: {token}")
                    return False

        return True

    def _apply_correction(self, chunk: ChunkContext, correction: CorrectionResponse) -> bool:
        """Apply the correction to the chunk (placeholder for now)."""
        # This would integrate with the main formatter to apply changes
        # For now, just log what would be applied

        applied_fixes = 0
        for fix in correction.fixes:
            if fix.confidence >= self.min_confidence:
                self.logger.info(f"Would apply fix: lines {fix.start_line}-{fix.end_line}, "
                               f"confidence: {fix.confidence}, issues: {fix.issues}")
                applied_fixes += 1

        return applied_fixes > 0

    def _avg_confidence(self, correction: CorrectionResponse) -> float:
        """Calculate average confidence of fixes."""
        if not correction.fixes:
            return 0.0
        return sum(fix.confidence for fix in correction.fixes) / len(correction.fixes)