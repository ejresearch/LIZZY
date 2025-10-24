"""Command-line interface for screenplay formatter."""

import os
import sys
import json
from pathlib import Path
from typing import Optional

import click

from .parser import ScreenplayParser
from .formatter import TextFormatter, DocxFormatter, PdfFormatter
from .validator import ScreenplayValidator
from .config import config_manager


@click.group()
@click.version_option(version="1.0.0", prog_name="screenplay-formatter")
def cli():
    """Screenplay Formatter - Convert text to industry-standard screenplay format."""
    pass


@cli.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.argument('output_file', type=click.Path())
@click.option('--format', '-f', type=click.Choice(['text', 'txt', 'docx', 'pdf'], case_sensitive=False),
              help='Output format (auto-detected from extension if not specified)')
@click.option('--validate', '-v', is_flag=True, help='Validate output after formatting')
@click.option('--strict', is_flag=True, help='Use strict validation mode')
def format(input_file: str, output_file: str, format: Optional[str], validate: bool, strict: bool):
    """Format a screenplay from input file to output file."""
    try:
        # Read input file
        with open(input_file, 'r') as f:
            content = f.read()

        # Parse content
        parser = ScreenplayParser()
        elements = parser.parse(content)
        click.echo(f"Parsed {len(elements)} elements from {input_file}")

        # Determine output format
        if not format:
            ext = Path(output_file).suffix.lower()
            if ext == '.docx':
                format = 'docx'
            elif ext == '.pdf':
                format = 'pdf'
            else:
                format = 'text'

        # Format based on type
        if format in ['text', 'txt']:
            formatter = TextFormatter()
            click.echo("Formatting as plain text...")
        elif format == 'docx':
            formatter = DocxFormatter()
            click.echo("Formatting as DOCX...")
        elif format == 'pdf':
            formatter = PdfFormatter()
            click.echo("Formatting as PDF...")
        else:
            click.echo(f"Unknown format: {format}", err=True)
            sys.exit(1)

        formatter.format(elements, output_file)
        click.echo(f"✓ Successfully formatted to {output_file}")

        # Optional validation
        if validate:
            validator = ScreenplayValidator(strict_mode=strict)
            report = validator.validate(elements)

            if report.passed:
                click.echo("✓ Validation passed!")
            else:
                click.echo(f"⚠ Validation found {report.total_errors} errors")
                if click.confirm("Show validation report?"):
                    click.echo(validator.export_text(report))

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='Output file for validation report')
@click.option('--format', '-f', type=click.Choice(['text', 'json']), default='text',
              help='Report format')
@click.option('--strict', is_flag=True, help='Use strict validation mode')
def validate(input_file: str, output: Optional[str], format: str, strict: bool):
    """Validate a screenplay file."""
    try:
        # Read and parse input
        with open(input_file, 'r') as f:
            content = f.read()

        parser = ScreenplayParser()
        elements = parser.parse(content)

        # Validate
        validator = ScreenplayValidator(strict_mode=strict)
        report = validator.validate(elements)

        # Output report
        if format == 'json':
            if output:
                validator.export_json(report, output)
                click.echo(f"Report saved to {output}")
            else:
                click.echo(json.dumps(report.model_dump(), indent=2))
        else:
            report_text = validator.export_text(report)
            if output:
                with open(output, 'w') as f:
                    f.write(report_text)
                click.echo(f"Report saved to {output}")
            else:
                click.echo(report_text)

        # Set exit code based on validation result
        sys.exit(0 if report.passed else 1)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.argument('reference_file', type=click.Path(exists=True))
@click.option('--show-all', is_flag=True, help='Show all differences, not just first 10')
def diff(input_file: str, reference_file: str, show_all: bool):
    """Compare two screenplay files for differences."""
    try:
        # Read both files
        with open(input_file, 'r') as f:
            input_content = f.read()
        with open(reference_file, 'r') as f:
            reference_content = f.read()

        # Parse both
        parser = ScreenplayParser()
        input_elements = parser.parse(input_content)
        reference_elements = parser.parse(reference_content)

        # Compare
        differences = []
        max_len = max(len(input_elements), len(reference_elements))

        for i in range(max_len):
            input_elem = input_elements[i] if i < len(input_elements) else None
            ref_elem = reference_elements[i] if i < len(reference_elements) else None

            if not input_elem and ref_elem:
                differences.append(f"Line {i+1}: Missing in input")
            elif input_elem and not ref_elem:
                differences.append(f"Line {i+1}: Extra in input")
            elif input_elem and ref_elem:
                if input_elem.type != ref_elem.type:
                    differences.append(f"Line {i+1}: Type mismatch ({input_elem.type.name} vs {ref_elem.type.name})")
                elif input_elem.content != ref_elem.content:
                    differences.append(f"Line {i+1}: Content mismatch")

        # Output differences
        if not differences:
            click.echo("✓ Files are identical in structure")
        else:
            click.echo(f"Found {len(differences)} differences:")
            limit = len(differences) if show_all else min(10, len(differences))
            for diff in differences[:limit]:
                click.echo(f"  {diff}")
            if not show_all and len(differences) > 10:
                click.echo(f"  ... and {len(differences) - 10} more")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='Output file for fixed screenplay')
@click.option('--dry-run', is_flag=True, help='Preview fixes without applying them')
@click.option('--model', default='gpt-4o-mini', help='OpenAI model to use')
@click.option('--confidence', type=float, default=0.8, help='Minimum confidence for auto-apply')
@click.option('--audit', type=click.Path(), help='Export audit log to JSON file')
@click.option('--strict', is_flag=True, help='Use strict validation mode')
def fix(input_file: str, output: Optional[str], dry_run: bool, model: str, confidence: float, audit: Optional[str], strict: bool):
    """Fix screenplay formatting using LLM assistance."""
    try:
        from .llm_corrector import LLMCorrector
        from .fix_engine import FixEngine

        # Read input file
        with open(input_file, 'r') as f:
            content = f.read()

        # Initialize LLM corrector
        try:
            api_key = config_manager.get_openai_api_key()
            corrector = LLMCorrector(
                api_key=api_key,
                model=model,
                min_confidence=confidence
            )
        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            click.echo("Set OPENAI_API_KEY environment variable", err=True)
            sys.exit(1)

        # Initialize fix engine
        engine = FixEngine(
            llm_corrector=corrector,
            strict_validation=strict,
            dry_run=dry_run
        )

        # Run fix process
        click.echo("Analyzing screenplay and identifying formatting issues...")
        result = engine.fix_screenplay(content)

        # Display summary
        summary = engine.get_fix_summary(result)
        click.echo(summary)

        # Save output if requested and not dry run
        if output and not dry_run and result.applied_fixes > 0:
            # Apply fixes would need to be implemented in fix_engine
            click.echo(f"Note: Output saving not yet implemented in this version")
            click.echo(f"Would save to: {output}")

        # Export audit log if requested
        if audit:
            engine.export_audit_log(result, audit)
            click.echo(f"Audit log exported to {audit}")

        # Show suggestions for manual review
        if result.suggested_fixes > 0:
            click.echo(f"\n{result.suggested_fixes} suggestions require manual review")
            if click.confirm("Show detailed correction suggestions?"):
                for correction in result.corrections:
                    if correction.fixes:
                        for fix in correction.fixes:
                            if fix.confidence < confidence:
                                click.echo(f"\nSuggestion (confidence: {fix.confidence:.2f}):")
                                click.echo(f"Lines {fix.start_line}-{fix.end_line}: {', '.join(fix.issues)}")
                                click.echo("Original:")
                                for line in fix.original:
                                    click.echo(f"  {line}")
                                click.echo("Suggested:")
                                for line in fix.revised:
                                    click.echo(f"  {line}")

    except ImportError:
        click.echo("Error: LLM fix functionality requires additional dependencies", err=True)
        click.echo("Run: pip install openai", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--set-api-key', help='Set OpenAI API key')
@click.option('--remove-api-key', is_flag=True, help='Remove stored API key')
@click.option('--model', help='Set default OpenAI model')
@click.option('--confidence', type=float, help='Set default confidence threshold (0.0-1.0)')
@click.option('--strict', type=bool, help='Set strict validation mode (true/false)')
@click.option('--show', is_flag=True, help='Show current configuration')
@click.option('--reset', is_flag=True, help='Reset configuration to defaults')
def config(set_api_key, remove_api_key, model, confidence, strict, show, reset):
    """Manage configuration settings."""
    if reset:
        if click.confirm("Reset all configuration to defaults?"):
            config_manager.reset_config()
        return

    if remove_api_key:
        config_manager.remove_openai_api_key()
        return

    if set_api_key:
        # Validate API key format (basic check)
        if not set_api_key.startswith('sk-'):
            click.echo("Warning: API key should start with 'sk-'", err=True)
        config_manager.set_openai_api_key(set_api_key)
        return

    if model:
        config_manager.set_default_model(model)
        click.echo(f"Default model set to: {model}")

    if confidence is not None:
        try:
            config_manager.set_default_confidence(confidence)
            click.echo(f"Default confidence set to: {confidence}")
        except ValueError as e:
            click.echo(f"Error: {e}", err=True)

    if strict is not None:
        config_manager.set_strict_validation(strict)
        click.echo(f"Strict validation set to: {strict}")

    if show or not any([set_api_key, remove_api_key, model, confidence is not None, strict is not None]):
        # Show config if no other action taken or explicitly requested
        click.echo(config_manager.show_config())


@cli.command()
def sample():
    """Generate a sample screenplay for testing."""
    sample_text = """FADE IN:

INT. COFFEE SHOP - DAY

A cozy neighborhood coffee shop buzzing with morning activity. Sunlight streams through large windows. SARAH (30s, professional attire) enters, scanning the crowded space.

She spots an empty table by the window and hurries over.

SARAH
(to herself)
Perfect.

She sets down her laptop bag and approaches the counter where JAKE (20s, barista apron) greets her with a smile.

JAKE
Morning! The usual?

SARAH
(smiling)
You know me too well. Large coffee, black.

JAKE
Coming right up!

Jake turns to prepare the coffee. Sarah glances at her watch, concerned.

SARAH
(urgent)
Actually, could you make that to go? I just remembered I have a meeting.

JAKE
(over his shoulder)
No problem!

He hands her the coffee in a to-go cup.

JAKE (CONT'D)
That'll be $3.50.

Sarah pays and rushes toward the door.

SARAH
Thanks, Jake! See you tomorrow!

CUT TO:

EXT. CITY STREET - CONTINUOUS

Sarah emerges from the coffee shop, coffee in hand, and hails a taxi.

FADE OUT.

THE END"""

    output_file = "sample_screenplay.txt"
    with open(output_file, 'w') as f:
        f.write(sample_text)

    click.echo(f"✓ Sample screenplay saved to {output_file}")
    click.echo("\nYou can now test the formatter with:")
    click.echo(f"  screenplay-format format {output_file} output.docx --format docx")
    click.echo(f"  screenplay-format validate {output_file}")


def main():
    """Main entry point for the CLI."""
    cli()


if __name__ == '__main__':
    main()