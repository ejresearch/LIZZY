"""Fix engine that orchestrates LLM correction with apply/reject logic."""

import json
import logging
import difflib
from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime

from .parser import ScreenplayParser, ScreenplayElement
from .validator import ScreenplayValidator, ValidationReport
from .llm_corrector import LLMCorrector, CorrectionResponse, ChunkContext
from .chunker import ValidationChunker


@dataclass
class FixResult:
    """Result of a fix operation."""
    success: bool
    original_errors: int
    remaining_errors: int
    applied_fixes: int
    suggested_fixes: int
    chunks_processed: int
    corrections: List[CorrectionResponse]
    final_validation: Optional[ValidationReport]
    audit_log: Dict[str, Any]


@dataclass
class AppliedFix:
    """Record of an applied fix."""
    chunk_start: int
    chunk_end: int
    original_lines: List[str]
    revised_lines: List[str]
    confidence: float
    issues: List[str]
    diff: str
    timestamp: str


class FixEngine:
    """Orchestrates the LLM-powered screenplay correction process."""

    def __init__(self,
                 llm_corrector: LLMCorrector,
                 strict_validation: bool = False,
                 dry_run: bool = False):
        """
        Initialize fix engine.

        Args:
            llm_corrector: LLM corrector instance
            strict_validation: Use strict validation mode
            dry_run: Preview fixes without applying them
        """
        self.corrector = llm_corrector
        self.strict_validation = strict_validation
        self.dry_run = dry_run

        self.parser = ScreenplayParser()
        self.validator = ScreenplayValidator(strict_mode=strict_validation)
        self.chunker = ValidationChunker()

        # Setup logging
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def fix_screenplay(self, input_text: str) -> FixResult:
        """
        Fix screenplay formatting issues using LLM.

        Args:
            input_text: Original screenplay text

        Returns:
            FixResult with details of the fixing process
        """
        self.logger.info("Starting screenplay fix process")

        # Parse and validate
        elements = self.parser.parse(input_text)
        initial_report = self.validator.validate(elements)

        if initial_report.passed:
            self.logger.info("Screenplay already passes validation")
            return FixResult(
                success=True,
                original_errors=0,
                remaining_errors=0,
                applied_fixes=0,
                suggested_fixes=0,
                chunks_processed=0,
                corrections=[],
                final_validation=initial_report,
                audit_log=self._create_audit_log("no_fixes_needed", {})
            )

        self.logger.info(f"Found {initial_report.total_errors} validation errors")

        # Create chunks for LLM processing
        text_lines = input_text.split('\n')
        error_list = [self._validation_error_from_dict(err) for err in initial_report.errors]
        chunks = self.chunker.create_chunks(elements, error_list, text_lines)
        chunks = self.chunker.validate_chunks(chunks)

        self.logger.info(f"Created {len(chunks)} chunks for processing")

        # Process chunks with LLM
        corrections = []
        applied_fixes = []
        suggested_fixes = []

        for i, chunk in enumerate(chunks):
            self.logger.info(f"Processing chunk {i+1}/{len(chunks)}: {self.chunker.get_chunk_summary(chunk)}")

            try:
                correction, applied = self.corrector.correct_chunk(chunk)
                corrections.append(correction)

                if applied and not self.dry_run:
                    # Apply high-confidence fixes
                    for fix in correction.fixes:
                        if fix.confidence >= self.corrector.min_confidence:
                            applied_fix = self._create_applied_fix(chunk, fix)
                            applied_fixes.append(applied_fix)
                        else:
                            suggested_fixes.append(fix)
                elif self.dry_run:
                    # In dry run, count what would be applied
                    for fix in correction.fixes:
                        if fix.confidence >= self.corrector.min_confidence:
                            applied_fixes.append(self._create_applied_fix(chunk, fix))
                        else:
                            suggested_fixes.append(fix)

            except Exception as e:
                self.logger.error(f"Failed to process chunk {i+1}: {e}")
                continue

        # Apply fixes to create corrected text (if not dry run)
        if applied_fixes and not self.dry_run:
            corrected_text = self._apply_fixes_to_text(input_text, applied_fixes)

            # Re-validate
            corrected_elements = self.parser.parse(corrected_text)
            final_report = self.validator.validate(corrected_elements)
        else:
            final_report = initial_report
            corrected_text = input_text

        # Create result
        result = FixResult(
            success=len(applied_fixes) > 0 or len(suggested_fixes) > 0,
            original_errors=initial_report.total_errors,
            remaining_errors=final_report.total_errors,
            applied_fixes=len(applied_fixes),
            suggested_fixes=len(suggested_fixes),
            chunks_processed=len(chunks),
            corrections=corrections,
            final_validation=final_report,
            audit_log=self._create_audit_log("fix_complete", {
                'dry_run': self.dry_run,
                'chunks_processed': len(chunks),
                'applied_fixes': len(applied_fixes),
                'suggested_fixes': len(suggested_fixes)
            })
        )

        self.logger.info(f"Fix process complete: {len(applied_fixes)} applied, "
                        f"{len(suggested_fixes)} suggested, "
                        f"{final_report.total_errors} errors remaining")

        return result

    def _validation_error_from_dict(self, error_dict: Dict) -> Any:
        """Convert validation error dict back to ValidationError object."""
        # This is a simplified conversion - in practice you'd need proper deserialization
        from .validator import ValidationError, ErrorCode, ElementType

        class MockError:
            def __init__(self, data):
                self.line_number = data['line_number']
                self.error_code = ErrorCode(data['error_code'])
                self.message = data['message']
                self.element_type = ElementType[data['element_type']]
                self.content = data['content']
                self.suggestion = data.get('suggestion')
                self.confidence = data.get('confidence', 0.0)

        return MockError(error_dict)

    def _create_applied_fix(self, chunk: ChunkContext, fix) -> AppliedFix:
        """Create an AppliedFix record."""
        diff = '\n'.join(difflib.unified_diff(
            fix.original,
            fix.revised,
            lineterm='',
            n=1
        ))

        return AppliedFix(
            chunk_start=chunk.start_line + fix.start_line,
            chunk_end=chunk.start_line + fix.end_line,
            original_lines=fix.original,
            revised_lines=fix.revised,
            confidence=fix.confidence,
            issues=fix.issues,
            diff=diff,
            timestamp=datetime.now().isoformat()
        )

    def _apply_fixes_to_text(self, original_text: str, applied_fixes: List[AppliedFix]) -> str:
        """Apply fixes to the original text."""
        lines = original_text.split('\n')

        # Sort fixes by start line (descending) to apply from bottom up
        fixes_sorted = sorted(applied_fixes, key=lambda f: f.chunk_start, reverse=True)

        for fix in fixes_sorted:
            # Replace lines in the range
            lines[fix.chunk_start:fix.chunk_end + 1] = fix.revised_lines

        return '\n'.join(lines)

    def _create_audit_log(self, operation: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create audit log entry."""
        return {
            'operation': operation,
            'timestamp': datetime.now().isoformat(),
            'model': getattr(self.corrector, 'model', 'unknown'),
            'dry_run': self.dry_run,
            'strict_validation': self.strict_validation,
            'data': data
        }

    def export_audit_log(self, result: FixResult, output_path: str):
        """Export detailed audit log to JSON file."""
        # Create summary dict manually to avoid issues with complex objects
        summary_dict = {
            'success': result.success,
            'original_errors': result.original_errors,
            'remaining_errors': result.remaining_errors,
            'applied_fixes': result.applied_fixes,
            'suggested_fixes': result.suggested_fixes,
            'chunks_processed': result.chunks_processed
        }

        audit_data = {
            'summary': summary_dict,
            'detailed_log': result.audit_log,
            'corrections': [correction.model_dump() for correction in result.corrections]
        }

        with open(output_path, 'w') as f:
            json.dump(audit_data, f, indent=2, default=str)

        self.logger.info(f"Audit log exported to {output_path}")

    def get_fix_summary(self, result: FixResult) -> str:
        """Get human-readable summary of fix results."""
        lines = []
        lines.append("=" * 60)
        lines.append("SCREENPLAY FIX SUMMARY")
        lines.append("=" * 60)

        if result.dry_run:
            lines.append("MODE: Dry Run (preview only)")
            lines.append("")

        lines.append(f"Original errors: {result.original_errors}")
        lines.append(f"Remaining errors: {result.remaining_errors}")
        lines.append(f"Applied fixes: {result.applied_fixes}")
        lines.append(f"Suggested fixes: {result.suggested_fixes}")
        lines.append(f"Chunks processed: {result.chunks_processed}")

        improvement = result.original_errors - result.remaining_errors
        if result.original_errors > 0:
            pct = (improvement / result.original_errors) * 100
            lines.append(f"Improvement: {improvement} errors fixed ({pct:.1f}%)")

        lines.append("")
        lines.append("Status: " + ("SUCCESS" if result.success else "FAILED"))

        if result.final_validation and not result.final_validation.passed:
            lines.append("")
            lines.append("Remaining Issues:")
            for error_type, count in result.final_validation.errors_by_type.items():
                lines.append(f"  {error_type}: {count}")

        return '\n'.join(lines)