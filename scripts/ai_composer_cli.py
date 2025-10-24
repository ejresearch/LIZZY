#!/usr/bin/env python3
"""
AI Block Composer CLI

Natural language to prompts - just type what you're thinking!

Examples:
- "Jenny in scene 4 dealing with disappointment, check scripts bucket"
- "Help me with the wedding scene where Mark confesses, what do plays say about dramatic confessions?"
- "I'm stuck on act 2 scene 12, need all three experts"
"""

import asyncio
import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.markdown import Markdown

# Add parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lizzy.prompt_studio import AIBlockComposer

console = Console()


async def interactive_mode(project_name: str):
    """Interactive AI composer session"""

    composer = AIBlockComposer(project_name)

    console.print("\n[bold cyan]╔═══════════════════════════════════════════════════════════╗[/bold cyan]")
    console.print("[bold cyan]║     AI BLOCK COMPOSER - Natural Language to Prompts      ║[/bold cyan]")
    console.print("[bold cyan]╚═══════════════════════════════════════════════════════════╝[/bold cyan]\n")

    console.print(f"[green]Project:[/green] {project_name}")
    console.print("\n[yellow]Just type what you're thinking about![/yellow]")
    console.print("[dim]Examples:[/dim]")
    console.print('[dim]  • "Jenny in scene 4 dealing with disappointment, check scripts"[/dim]')
    console.print('[dim]  • "Help with the wedding scene, need plays expert"[/dim]')
    console.print('[dim]  • "Stuck on act 2 scene 12, get all three experts"[/dim]')
    console.print('\n[dim]Type "quit" or "exit" to leave[/dim]\n')

    while True:
        # Get user input
        user_input = Prompt.ask("\n[bold magenta]What are you working on?[/bold magenta]")

        if user_input.lower() in ["quit", "exit", "q"]:
            console.print("\n[green]Goodbye![/green]\n")
            break

        if not user_input.strip():
            continue

        # Compose prompt
        console.print("\n[yellow]🤖 Parsing your input...[/yellow]")

        try:
            result = await composer.compose(user_input)

            # Show what was parsed
            console.print("\n[bold cyan]Detected:[/bold cyan]")
            if hasattr(result, 'parsed_entities'):
                import json
                console.print(f"[dim]{json.dumps(result.parsed_entities, indent=2)}[/dim]")

            # Show blocks used
            console.print("\n[bold cyan]Blocks Used:[/bold cyan]")
            if hasattr(result, 'blocks_used'):
                for i, block_desc in enumerate(result.blocks_used, 1):
                    console.print(f"  {i}. {block_desc}")

            # Show assembled prompt
            console.print("\n[bold cyan]Assembled Prompt:[/bold cyan]")

            # If prompt is very long, show preview
            if len(result.prompt) > 1500:
                preview = result.prompt[:1500] + "\n\n... [truncated]"
                console.print(Panel(preview, border_style="green", title="Preview (first 1500 chars)"))
                console.print(f"\n[dim]Total: {result.total_chars} chars, {result.total_execution_time_ms:.2f}ms[/dim]")

                if Prompt.ask("\nSave full prompt to file?", choices=["y", "n"], default="n") == "y":
                    import time
                    filename = f"prompt_{int(time.time())}.txt"
                    with open(filename, 'w') as f:
                        f.write(result.prompt)
                    console.print(f"[green]✓ Saved to {filename}[/green]")
            else:
                console.print(Panel(result.prompt, border_style="green", title="Assembled Prompt"))
                console.print(f"\n[dim]Total: {result.total_chars} chars, {result.total_execution_time_ms:.2f}ms[/dim]")

        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]")
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")


async def one_shot_mode(user_input: str, project_name: str):
    """Single query mode"""

    composer = AIBlockComposer(project_name)

    console.print("\n[yellow]🤖 Processing your request...[/yellow]\n")

    try:
        result = await composer.compose(user_input)

        # Show what was parsed
        console.print("[bold cyan]Detected:[/bold cyan]")
        if hasattr(result, 'parsed_entities'):
            import json
            console.print(f"{json.dumps(result.parsed_entities, indent=2)}\n")

        # Show blocks used
        console.print("[bold cyan]Blocks Used:[/bold cyan]")
        if hasattr(result, 'blocks_used'):
            for i, block_desc in enumerate(result.blocks_used, 1):
                console.print(f"  {i}. {block_desc}")

        # Show prompt
        console.print(f"\n[bold cyan]Assembled Prompt:[/bold cyan]")
        console.print(Panel(result.prompt, border_style="green"))
        console.print(f"\n[dim]Total: {result.total_chars} chars, {result.total_execution_time_ms:.2f}ms[/dim]\n")

    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")


async def example_queries(project_name: str):
    """Run example queries to demonstrate the system"""

    composer = AIBlockComposer(project_name)

    examples = [
        "Jenny in scene 4 dealing with disappointment, check scripts bucket",
        "Help me with the wedding scene where Mark confesses, what do the plays say?",
        "I'm stuck on act 2 scene 12, need all three experts",
        "What do the books bucket say about romantic comedy structure?",
    ]

    console.print("\n[bold cyan]Running Example Queries[/bold cyan]\n")

    for i, example in enumerate(examples, 1):
        console.print(f"\n[bold yellow]Example {i}:[/bold yellow] {example}")
        console.print("=" * 80)

        try:
            result = await composer.compose(example)

            console.print("\n[bold cyan]Parsed:[/bold cyan]")
            if hasattr(result, 'parsed_entities'):
                import json
                console.print(f"[dim]{json.dumps(result.parsed_entities, indent=2)}[/dim]")

            console.print("\n[bold cyan]Blocks:[/bold cyan]")
            if hasattr(result, 'blocks_used'):
                for block_desc in result.blocks_used:
                    console.print(f"  • {block_desc}")

            console.print(f"\n[bold cyan]Result:[/bold cyan] {result.total_chars} chars assembled in {result.total_execution_time_ms:.2f}ms")

            if i < len(examples):
                input("\n[Press Enter for next example...]")

        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]")


def main():
    """Main entry point"""

    import argparse

    parser = argparse.ArgumentParser(
        description="AI Block Composer - Natural language to prompts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  python3 ai_composer_cli.py

  # One-shot query
  python3 ai_composer_cli.py -q "Jenny in scene 4, check scripts bucket"

  # Run examples
  python3 ai_composer_cli.py --examples

  # Specify project
  python3 ai_composer_cli.py -p "my_project"
        """
    )

    parser.add_argument(
        "-p", "--project",
        default="the_proposal_2_0",
        help="Project name (default: the_proposal_2_0)"
    )

    parser.add_argument(
        "-q", "--query",
        help="One-shot query (instead of interactive mode)"
    )

    parser.add_argument(
        "--examples",
        action="store_true",
        help="Run example queries"
    )

    args = parser.parse_args()

    try:
        if args.examples:
            asyncio.run(example_queries(args.project))
        elif args.query:
            asyncio.run(one_shot_mode(args.query, args.project))
        else:
            asyncio.run(interactive_mode(args.project))
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Interrupted[/yellow]\n")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]\n")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
