#!/usr/bin/env python3
"""
Prompt Studio CLI

Simple command-line interface for composing and testing prompts.
"""

import os
import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich import print as rprint

# Add lizzy to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lizzy.prompt_studio import PromptEngine, BlockRegistry
from lizzy.prompt_studio.blocks import (
    SceneBlock,
    CharacterBiosBlock,
    BooksQueryBlock,
    MultiExpertQueryBlock,
    TextBlock,
    SectionHeaderBlock,
)

console = Console()


def list_available_blocks():
    """Display all available block types"""
    console.print("\n[bold cyan]Available Block Types[/bold cyan]\n")

    categories = BlockRegistry.get_blocks_by_category()

    for category, block_types in categories.items():
        console.print(f"\n[bold yellow]{category}[/bold yellow]")
        for block_type in block_types:
            console.print(f"  • {block_type}")

    console.print("\n")


def show_block_info():
    """Display detailed info about all blocks"""
    console.print("\n[bold cyan]Block Information[/bold cyan]\n")

    info = BlockRegistry.get_block_info()

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Block Type", style="cyan")
    table.add_column("Class", style="green")
    table.add_column("Description", style="white")

    for block_type, details in info.items():
        table.add_row(
            block_type,
            details['class_name'],
            details['description']
        )

    console.print(table)
    console.print("\n")


def example_basic_prompt():
    """Example: Build a basic prompt with scene + characters"""
    console.print("\n[bold cyan]Example 1: Basic Prompt (Scene + Characters)[/bold cyan]\n")

    project_name = "The Proposal 2.0"
    scene_number = 1

    # Build blocks
    blocks = [
        SectionHeaderBlock(title="SCENE CONTEXT"),
        SceneBlock(scene_number=scene_number),
        SectionHeaderBlock(title="CHARACTERS"),
        CharacterBiosBlock(),
    ]

    # Assemble
    engine = PromptEngine()
    result = engine.assemble(blocks, project_name)

    # Display
    console.print(Panel(result.prompt, title="Assembled Prompt", border_style="green"))

    # Show metadata
    console.print(f"\n[dim]Total chars: {result.total_chars}[/dim]")
    console.print(f"[dim]Execution time: {result.total_execution_time_ms:.2f}ms[/dim]")
    console.print(f"[dim]Blocks executed: {len(result.metadata)}[/dim]\n")


def example_rag_query():
    """Example: Query RAG buckets"""
    console.print("\n[bold cyan]Example 2: RAG Query (Books Expert)[/bold cyan]\n")

    project_name = "The Proposal 2.0"

    query = Prompt.ask("Enter query for books expert", default="romantic tension techniques")

    blocks = [
        TextBlock("Please provide expert guidance on the following:"),
        BooksQueryBlock(query=query, mode="hybrid"),
    ]

    console.print("\n[yellow]Querying books bucket...[/yellow]\n")

    engine = PromptEngine()
    result = engine.assemble(blocks, project_name)

    console.print(Panel(result.prompt, title="Query Result", border_style="green"))
    console.print(f"\n[dim]Execution time: {result.total_execution_time_ms:.2f}ms[/dim]\n")


def example_multi_expert():
    """Example: Query all three experts"""
    console.print("\n[bold cyan]Example 3: Multi-Expert Query (All 3 Buckets)[/bold cyan]\n")

    project_name = "The Proposal 2.0"

    query = Prompt.ask("Enter query for all experts", default="how to write compelling dialogue")

    blocks = [
        SectionHeaderBlock(title="EXPERT CONSULTATION"),
        TextBlock(f"Question: {query}"),
        MultiExpertQueryBlock(query=query, mode="hybrid"),
    ]

    console.print("\n[yellow]Querying all three expert buckets...[/yellow]\n")

    engine = PromptEngine()
    result = engine.assemble(blocks, project_name)

    # This will be very long, so show preview
    preview = result.prompt[:2000] + "\n\n... [truncated]" if len(result.prompt) > 2000 else result.prompt

    console.print(Panel(preview, title="Multi-Expert Result (Preview)", border_style="green"))
    console.print(f"\n[dim]Total chars: {result.total_chars}[/dim]")
    console.print(f"[dim]Execution time: {result.total_execution_time_ms:.2f}ms[/dim]\n")

    if Confirm.ask("Save full result to file?"):
        filename = f"prompt_output_{int(time.time())}.txt"
        with open(filename, 'w') as f:
            f.write(result.prompt)
        console.print(f"[green]Saved to {filename}[/green]\n")


def custom_composition():
    """Interactive custom prompt composition"""
    console.print("\n[bold cyan]Custom Prompt Composition[/bold cyan]\n")
    console.print("[yellow]Build a custom prompt by selecting blocks[/yellow]\n")

    project_name = Prompt.ask("Project name", default="The Proposal 2.0")
    blocks = []

    while True:
        console.print("\n[bold]Available block types:[/bold]")
        console.print("1. Scene (specific scene data)")
        console.print("2. Character Bios (all characters)")
        console.print("3. Books Query (structure expert)")
        console.print("4. Plays Query (dialogue expert)")
        console.print("5. Scripts Query (visual expert)")
        console.print("6. Multi-Expert Query (all 3 experts)")
        console.print("7. Text (static text)")
        console.print("8. Section Header (formatted header)")
        console.print("9. Done - assemble prompt")

        choice = Prompt.ask("Add block", choices=["1", "2", "3", "4", "5", "6", "7", "8", "9"])

        if choice == "1":
            scene_num = int(Prompt.ask("Scene number", default="1"))
            blocks.append(SceneBlock(scene_number=scene_num))
            console.print(f"[green]Added SceneBlock ({scene_num})[/green]")

        elif choice == "2":
            blocks.append(CharacterBiosBlock())
            console.print("[green]Added CharacterBiosBlock[/green]")

        elif choice == "3":
            query = Prompt.ask("Query")
            blocks.append(BooksQueryBlock(query=query))
            console.print(f"[green]Added BooksQueryBlock[/green]")

        elif choice == "4":
            query = Prompt.ask("Query")
            blocks.append(PlaysQueryBlock(query=query))
            console.print(f"[green]Added PlaysQueryBlock[/green]")

        elif choice == "5":
            query = Prompt.ask("Query")
            blocks.append(ScriptsQueryBlock(query=query))
            console.print(f"[green]Added ScriptsQueryBlock[/green]")

        elif choice == "6":
            query = Prompt.ask("Query")
            blocks.append(MultiExpertQueryBlock(query=query))
            console.print(f"[green]Added MultiExpertQueryBlock[/green]")

        elif choice == "7":
            text = Prompt.ask("Text")
            blocks.append(TextBlock(text=text))
            console.print(f"[green]Added TextBlock[/green]")

        elif choice == "8":
            title = Prompt.ask("Header title")
            blocks.append(SectionHeaderBlock(title=title))
            console.print(f"[green]Added SectionHeaderBlock[/green]")

        elif choice == "9":
            break

    if not blocks:
        console.print("[red]No blocks added![/red]\n")
        return

    console.print(f"\n[yellow]Assembling {len(blocks)} blocks...[/yellow]\n")

    engine = PromptEngine()
    result = engine.assemble(blocks, project_name)

    console.print(Panel(result.prompt, title="Assembled Prompt", border_style="green"))
    console.print(f"\n[dim]Total chars: {result.total_chars}[/dim]")
    console.print(f"[dim]Execution time: {result.total_execution_time_ms:.2f}ms[/dim]\n")


def main():
    """Main menu"""
    console.print("\n[bold magenta]╔═══════════════════════════════════════╗[/bold magenta]")
    console.print("[bold magenta]║     LIZZY PROMPT STUDIO CLI v1.0      ║[/bold magenta]")
    console.print("[bold magenta]╚═══════════════════════════════════════╝[/bold magenta]\n")

    while True:
        console.print("\n[bold cyan]Main Menu[/bold cyan]\n")
        console.print("1. List available block types")
        console.print("2. Show detailed block info")
        console.print("3. Example: Basic prompt (Scene + Characters)")
        console.print("4. Example: RAG query (Books expert)")
        console.print("5. Example: Multi-expert query (All 3 buckets)")
        console.print("6. Custom composition (build your own)")
        console.print("7. Exit")

        choice = Prompt.ask("\nSelect option", choices=["1", "2", "3", "4", "5", "6", "7"], default="1")

        if choice == "1":
            list_available_blocks()
        elif choice == "2":
            show_block_info()
        elif choice == "3":
            example_basic_prompt()
        elif choice == "4":
            example_rag_query()
        elif choice == "5":
            example_multi_expert()
        elif choice == "6":
            custom_composition()
        elif choice == "7":
            console.print("\n[green]Goodbye![/green]\n")
            break


if __name__ == "__main__":
    import time
    from lizzy.prompt_studio.blocks import PlaysQueryBlock, ScriptsQueryBlock
    main()
