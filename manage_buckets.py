#!/usr/bin/env python3
"""
Interactive Bucket Manager for Lizzy Romcom

Run this to:
A) Use an existing bucket
B) Create a new bucket and populate it with your files
"""

import os
import asyncio
from pathlib import Path
from lizzy.bucket_manager import create_and_populate_bucket
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table

console = Console()


def list_existing_buckets():
    """Show all existing buckets."""
    bucket_dir = Path("./rag_buckets")
    if not bucket_dir.exists():
        return []

    buckets = [d for d in bucket_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
    return buckets


def show_buckets_table(buckets):
    """Display buckets in a nice table."""
    if not buckets:
        console.print("[yellow]No existing buckets found[/yellow]\n")
        return

    table = Table(title="Existing Buckets", show_header=True, header_style="bold cyan")
    table.add_column("#", style="dim")
    table.add_column("Bucket Name", style="green")
    table.add_column("Location")
    table.add_column("Files")

    for idx, bucket in enumerate(buckets, 1):
        # Count files in bucket
        files = list(bucket.glob("*.json")) + list(bucket.glob("*.graphml"))
        file_count = len(files)
        status = "✅ Populated" if file_count > 0 else "⚠️ Empty"

        table.add_row(
            str(idx),
            bucket.name,
            str(bucket),
            status
        )

    console.print(table)


def get_files_from_user():
    """Prompt user for file paths."""
    console.print("\n[cyan]Enter file paths to upload:[/cyan]")
    console.print("[dim]You can enter:[/dim]")
    console.print("[dim]  - Single file: /path/to/file.docx[/dim]")
    console.print("[dim]  - Directory: /path/to/folder/[/dim]")
    console.print("[dim]  - Pattern: /path/to/folder/*.docx[/dim]")
    console.print("[dim]  - Multiple (comma-separated): file1.txt, file2.docx[/dim]\n")

    input_str = Prompt.ask("File path(s)")

    files = []

    # Split by comma if multiple paths
    paths = [p.strip() for p in input_str.split(',')]

    for path_str in paths:
        path = Path(path_str.strip()).expanduser()

        # If it's a directory, get all .txt and .docx files
        if path.is_dir():
            files.extend(path.glob("*.txt"))
            files.extend(path.glob("*.docx"))
            files.extend(path.glob("*.pdf"))
        # If it's a glob pattern
        elif '*' in str(path):
            parent = Path(str(path).split('*')[0]).parent
            pattern = path.name
            files.extend(parent.glob(pattern))
        # Single file
        elif path.exists():
            files.append(path)
        else:
            console.print(f"[yellow]⚠️  Path not found: {path}[/yellow]")

    # Remove duplicates and filter out LightRAG metadata
    files = list(set([
        f for f in files
        if f.is_file()
        and not f.name.startswith('kv_store')
        and not f.name.startswith('vdb_')
        and not f.name.endswith('.json')
        and not f.name.endswith('.xml')
        and not f.name.endswith('.graphml')
        and not f.name.endswith('.log')
    ]))

    return files


async def install_prebuilt_bucket():
    """Install a pre-built LightRAG bucket from another location."""
    console.print("\n[bold cyan]Install Pre-Built Bucket[/bold cyan]\n")
    console.print("[dim]This will copy an existing LightRAG bucket directory[/dim]")
    console.print("[dim]into your rag_buckets/ folder.[/dim]\n")

    # Get source path
    source_path = Prompt.ask("Path to pre-built bucket directory")
    source = Path(source_path.strip()).expanduser()

    if not source.exists():
        console.print(f"[red]❌ Error: Path not found: {source}[/red]")
        return

    if not source.is_dir():
        console.print(f"[red]❌ Error: Path is not a directory[/red]")
        return

    # Validate it's a LightRAG bucket
    required_files = [
        "graph_chunk_entity_relation.graphml",
        "kv_store_full_docs.json",
        "vdb_chunks.json"
    ]

    missing = [f for f in required_files if not (source / f).exists()]

    if missing:
        console.print(f"[yellow]⚠️  Warning: This doesn't look like a complete LightRAG bucket[/yellow]")
        console.print(f"[dim]Missing files: {', '.join(missing)}[/dim]\n")
        if not Confirm.ask("Install anyway?"):
            console.print("[yellow]Cancelled[/yellow]")
            return

    # Get bucket name
    default_name = source.name
    bucket_name = Prompt.ask("Bucket name", default=default_name)

    # Check if destination exists
    dest = Path(f"./rag_buckets/{bucket_name}")

    if dest.exists():
        console.print(f"[yellow]⚠️  Bucket '{bucket_name}' already exists[/yellow]")
        if not Confirm.ask("Overwrite?"):
            console.print("[yellow]Cancelled[/yellow]")
            return
        # Delete existing
        import shutil
        shutil.rmtree(dest)

    # Copy bucket
    console.print(f"\n[cyan]Copying bucket files...[/cyan]")
    import shutil
    shutil.copytree(source, dest)

    # Show what was copied
    files = list(dest.glob("*"))
    total_size = sum(f.stat().st_size for f in files if f.is_file())

    console.print(f"""
    ╔════════════════════════════════════════════════════════════╗
    ║                    🎉 Success! 🎉                         ║
    ╚════════════════════════════════════════════════════════════╝

    Bucket '{bucket_name}' installed!

    📊 Statistics:
       Files copied: {len(files)}
       Total size: {total_size / 1024 / 1024:.2f} MB
       Location: {dest}

    💡 This bucket is ready to use in BRAINSTORM!
    """)


async def main():
    """Main interactive flow."""
    console.print("""
    ╔════════════════════════════════════════════════════════════╗
    ║              Lizzy Romcom - Bucket Manager                ║
    ╚════════════════════════════════════════════════════════════╝
    """)

    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        console.print("[red]❌ Error: OPENAI_API_KEY environment variable not set[/red]")
        console.print("Please run: export OPENAI_API_KEY='your-key'")
        return

    # Show existing buckets
    existing_buckets = list_existing_buckets()
    show_buckets_table(existing_buckets)

    # Ask: Use existing or create new?
    console.print("\n[bold]What would you like to do?[/bold]")
    console.print("[1] Create a new bucket")
    console.print("[2] Add files to an existing bucket")
    console.print("[3] Install a pre-built bucket")
    console.print("[4] Exit")

    choice = Prompt.ask("Choose an option", choices=["1", "2", "3", "4"], default="1")

    if choice == "4":
        console.print("\n[dim]Goodbye![/dim]")
        return

    # Handle bucket installation
    if choice == "3":
        await install_prebuilt_bucket()
        return

    # Get bucket name
    if choice == "1":
        # Create new bucket
        bucket_name = Prompt.ask("\n[cyan]Enter new bucket name[/cyan]")
        bucket_dir = Path(f"./rag_buckets/{bucket_name}")

        if bucket_dir.exists():
            overwrite = Confirm.ask(f"Bucket '{bucket_name}' already exists. Overwrite?")
            if not overwrite:
                console.print("[yellow]Cancelled[/yellow]")
                return
            # Delete existing
            import shutil
            shutil.rmtree(bucket_dir)

    else:
        # Use existing bucket
        if not existing_buckets:
            console.print("[red]No existing buckets found. Please create a new one.[/red]")
            return

        bucket_idx = int(Prompt.ask(
            "Choose bucket number",
            choices=[str(i) for i in range(1, len(existing_buckets) + 1)]
        ))
        bucket = existing_buckets[bucket_idx - 1]
        bucket_name = bucket.name
        bucket_dir = bucket

    # Get files to upload
    files = get_files_from_user()

    if not files:
        console.print("[red]❌ No valid files found[/red]")
        return

    # Show files
    console.print(f"\n[green]Found {len(files)} files to process:[/green]")
    for f in files[:10]:  # Show first 10
        console.print(f"  • {f.name}")
    if len(files) > 10:
        console.print(f"  [dim]... and {len(files) - 10} more[/dim]")

    # Confirm
    if not Confirm.ask(f"\nPopulate '{bucket_name}' bucket with these files?"):
        console.print("[yellow]Cancelled[/yellow]")
        return

    # Create and populate
    console.print(f"\n[bold cyan]Processing...[/bold cyan]\n")

    rag, stats = await create_and_populate_bucket(
        bucket_name=bucket_name,
        bucket_dir=bucket_dir,
        source_files=files,
        verbose=True
    )

    await rag.finalize_storages()

    console.print(f"""
    ╔════════════════════════════════════════════════════════════╗
    ║                    🎉 Success! 🎉                         ║
    ╚════════════════════════════════════════════════════════════╝

    Bucket '{bucket_name}' ready to use!

    📊 Statistics:
       Total files: {stats['total']}
       Inserted: {stats['inserted']}
       Failed: {stats['failed']}
       Skipped: {stats['skipped']}

    💡 Next steps:
       1. Create more buckets if needed
       2. Start using Lizzy to write romcoms!
    """)


if __name__ == "__main__":
    asyncio.run(main())
