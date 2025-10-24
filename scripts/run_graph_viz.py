#!/usr/bin/env python3
"""
Non-interactive wrapper for graph_visualizer.py
Generates visualizations for all buckets automatically.
"""

from pathlib import Path
import sys
import webbrowser

# Add parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lizzy.graph_visualizer import GraphVisualizer
from lizzy.config import config
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def visualize_all_buckets():
    """Generate visualizations for all buckets."""

    bucket_dir = config.rag_buckets_dir

    if not bucket_dir.exists():
        console.print("[red]No rag_buckets directory found[/red]")
        return

    buckets = [d for d in bucket_dir.iterdir()
               if d.is_dir() and not d.name.startswith('.')]

    if not buckets:
        console.print("[yellow]No buckets found[/yellow]")
        return

    console.print(Panel.fit(
        "[bold cyan]LightRAG Knowledge Graph Visualizer[/bold cyan]\n\n"
        "Generating visualizations for all buckets",
        border_style="cyan"
    ))

    # Create visualizations directory
    viz_dir = Path("./visualizations")
    viz_dir.mkdir(exist_ok=True)

    results = []

    for bucket in sorted(buckets):
        console.print(f"\n[bold]Processing bucket: {bucket.name}[/bold]")

        visualizer = GraphVisualizer(bucket)

        # Get statistics
        stats = visualizer.get_entity_statistics()

        if not stats or stats['total_entities'] == 0:
            console.print(f"[yellow]  Skipping - no data found[/yellow]")
            continue

        console.print(Panel.fit(
            f"Entities: {stats['total_entities']:,}\n"
            f"Relationships: {stats['total_relationships']:,}\n"
            f"Avg Connections: {stats['avg_connections']:.1f}",
            title=f"Bucket: {bucket.name}",
            border_style="cyan"
        ))

        # Auto-limit large graphs for performance
        max_nodes = None
        if stats['total_entities'] > 500:
            max_nodes = 200
            console.print(f"[dim]  Large graph detected - limiting to {max_nodes} most connected nodes[/dim]")

        # Generate visualization
        output_path = viz_dir / f"{bucket.name}_graph.html"

        result = visualizer.create_visualization(
            output_path=str(output_path),
            max_nodes=max_nodes,
            physics_enabled=True
        )

        if result:
            results.append((bucket.name, result))

    # Summary
    if results:
        console.print("\n[bold green]✓ Visualizations generated:[/bold green]")

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Bucket", style="green")
        table.add_column("Output File", style="cyan")

        for bucket_name, path in results:
            table.add_row(bucket_name, path)

        console.print(table)

        # Ask to open first one
        console.print(f"\n[dim]To view, open these HTML files in your browser[/dim]")
        console.print(f"[dim]Example: open {results[0][1]}[/dim]")

        return results
    else:
        console.print("[yellow]No visualizations generated[/yellow]")
        return []


def visualize_single_bucket(bucket_name: str, max_nodes: int = None):
    """Generate visualization for a single bucket."""

    bucket_dir = Path("./rag_buckets")
    bucket_path = bucket_dir / bucket_name

    if not bucket_path.exists():
        console.print(f"[red]Bucket not found: {bucket_name}[/red]")
        return None

    console.print(Panel.fit(
        f"[bold cyan]Visualizing: {bucket_name}[/bold cyan]",
        border_style="cyan"
    ))

    visualizer = GraphVisualizer(bucket_path)

    # Get statistics
    stats = visualizer.get_entity_statistics()

    if not stats or stats['total_entities'] == 0:
        console.print(f"[yellow]No data found in bucket[/yellow]")
        return None

    console.print(Panel.fit(
        f"Entities: {stats['total_entities']:,}\n"
        f"Relationships: {stats['total_relationships']:,}\n"
        f"Avg Connections: {stats['avg_connections']:.1f}\n"
        f"Max Connections: {stats['max_connections']:,}",
        title=f"Bucket: {bucket_name}",
        border_style="cyan"
    ))

    # Show top entity types
    if stats['entity_types']:
        console.print("\n[bold]Entity Types:[/bold]")
        for etype, count in sorted(stats['entity_types'].items(),
                                   key=lambda x: x[1], reverse=True)[:10]:
            console.print(f"  • {etype}: {count:,}")

    # Auto-limit if not specified
    if max_nodes is None and stats['total_entities'] > 500:
        max_nodes = 200
        console.print(f"\n[dim]Large graph - limiting to {max_nodes} most connected nodes[/dim]")

    # Create visualizations directory
    viz_dir = Path("./visualizations")
    viz_dir.mkdir(exist_ok=True)

    output_path = viz_dir / f"{bucket_name}_graph.html"

    result = visualizer.create_visualization(
        output_path=str(output_path),
        max_nodes=max_nodes,
        physics_enabled=True
    )

    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate Neo4j-style knowledge graph visualizations"
    )
    parser.add_argument(
        'bucket',
        nargs='?',
        help='Specific bucket name (e.g., "scripts", "books"). If omitted, visualizes all buckets.'
    )
    parser.add_argument(
        '--max-nodes',
        type=int,
        help='Maximum number of nodes to display (default: auto-limit for large graphs)'
    )
    parser.add_argument(
        '--open',
        action='store_true',
        help='Open visualization in browser after generation'
    )

    args = parser.parse_args()

    if args.bucket:
        # Single bucket
        result = visualize_single_bucket(args.bucket, max_nodes=args.max_nodes)
        if result and args.open:
            webbrowser.open(f"file://{result}")
    else:
        # All buckets
        results = visualize_all_buckets()
        if results and args.open:
            # Open first one
            webbrowser.open(f"file://{results[0][1]}")
