"""
Multi-Bucket Knowledge Graph Explorer

Combine and explore knowledge graphs from multiple RAG buckets simultaneously.
Query across books, plays, and scripts to find cross-cutting concepts and patterns.
"""

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from collections import Counter, defaultdict
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

try:
    from pyvis.network import Network
    PYVIS_AVAILABLE = True
except ImportError:
    PYVIS_AVAILABLE = False

console = Console()


class MultiBucketExplorer:
    """
    Explore and visualize multiple RAG buckets as a unified knowledge graph.

    Features:
    - Combine graphs from multiple buckets
    - Color-code by source bucket
    - Cross-bucket entity search
    - Find entities that appear in multiple buckets
    - Query by entity type across all sources
    """

    def __init__(self, bucket_paths: List[Path]):
        """
        Initialize explorer with multiple buckets.

        Args:
            bucket_paths: List of paths to RAG bucket directories
        """
        self.bucket_paths = bucket_paths
        self.bucket_names = [p.name for p in bucket_paths]

        # Color scheme for buckets
        self.bucket_colors = {
            'books': '#FF6B6B',      # Red
            'plays': '#4ECDC4',      # Teal
            'scripts': '#FFD93D',    # Gold
            'default': '#95A5A6'     # Gray
        }

        # Entity type colors (secondary)
        self.type_colors = {
            'person': '#E74C3C',
            'character': '#E91E63',
            'concept': '#FF9800',
            'theme': '#9C27B0',
            'technique': '#FFC107',
            'location': '#2196F3',
            'organization': '#00BCD4',
            'event': '#4CAF50',
            'default': '#607D8B'
        }

        # Cache
        self._all_entities = None
        self._all_relationships = None
        self._entity_sources = None

    def load_all_graphs(self) -> Tuple[Dict, List, Dict]:
        """
        Load and combine graphs from all buckets.

        Returns:
            Tuple of (entities_dict, relationships_list, entity_sources_dict)
        """
        if self._all_entities and self._all_relationships:
            return self._all_entities, self._all_relationships, self._entity_sources

        all_entities = {}
        all_relationships = []
        entity_sources = defaultdict(set)  # Track which buckets each entity appears in

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Loading all buckets...", total=len(self.bucket_paths))

            for bucket_path in self.bucket_paths:
                bucket_name = bucket_path.name
                graphml_path = bucket_path / "graph_chunk_entity_relation.graphml"

                if not graphml_path.exists():
                    console.print(f"[yellow]Skipping {bucket_name} (no GraphML file)[/yellow]")
                    progress.update(task, advance=1)
                    continue

                progress.update(task, description=f"Loading {bucket_name}...")

                try:
                    tree = ET.parse(graphml_path)
                    root = tree.getroot()
                    ns = {'graphml': 'http://graphml.graphdrawing.org/xmlns'}

                    # Load entities
                    for node in root.findall('.//graphml:node', ns):
                        entity_id = node.get('id')
                        entity_data = {
                            'id': entity_id,
                            'source_bucket': bucket_name
                        }

                        for data in node.findall('graphml:data', ns):
                            key = data.get('key')
                            value = data.text or ""

                            if key == 'd0':
                                entity_data['entity_id'] = value
                            elif key == 'd1':
                                entity_data['entity_type'] = value.lower()
                            elif key == 'd2':
                                entity_data['description'] = value
                            elif key == 'd3':
                                entity_data['source_id'] = value

                        # Create unique ID with bucket prefix
                        unique_id = f"{bucket_name}::{entity_id}"
                        all_entities[unique_id] = entity_data

                        # Track original entity ID across buckets
                        entity_sources[entity_id].add(bucket_name)

                    # Load relationships
                    for edge in root.findall('.//graphml:edge', ns):
                        source = edge.get('source')
                        target = edge.get('target')

                        rel_data = {
                            'source': f"{bucket_name}::{source}",
                            'target': f"{bucket_name}::{target}",
                            'source_bucket': bucket_name,
                            'weight': 1.0
                        }

                        for data in edge.findall('graphml:data', ns):
                            key = data.get('key')
                            value = data.text or ""

                            if key == 'd6':
                                try:
                                    rel_data['weight'] = float(value) if value else 1.0
                                except ValueError:
                                    rel_data['weight'] = 1.0
                            elif key == 'd7':
                                rel_data['description'] = value
                            elif key == 'd8':
                                rel_data['keywords'] = value

                        all_relationships.append(rel_data)

                except Exception as e:
                    console.print(f"[red]Error loading {bucket_name}: {e}[/red]")

                progress.update(task, advance=1)

        self._all_entities = all_entities
        self._all_relationships = all_relationships
        self._entity_sources = dict(entity_sources)

        console.print(f"[green]✓[/green] Loaded {len(all_entities):,} total entities from {len(self.bucket_paths)} buckets")

        return all_entities, all_relationships, entity_sources

    def search_across_buckets(
        self,
        query: str,
        entity_types: Optional[List[str]] = None,
        buckets: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Search for entities across all buckets.

        Args:
            query: Search term (case-insensitive)
            entity_types: Filter by entity types
            buckets: Filter by specific buckets

        Returns:
            List of matching entities with source information
        """
        entities, _, entity_sources = self.load_all_graphs()
        query_lower = query.lower()

        matches = []
        for unique_id, data in entities.items():
            # Filter by bucket
            if buckets and data['source_bucket'] not in buckets:
                continue

            # Filter by type
            if entity_types:
                entity_type = data.get('entity_type', '').lower()
                if entity_type not in [t.lower() for t in entity_types]:
                    continue

            # Search in ID and description
            entity_id = data.get('entity_id', unique_id)
            description = data.get('description', '')

            if query_lower in entity_id.lower() or query_lower in description.lower():
                # Get cross-bucket info
                base_id = unique_id.split('::')[1] if '::' in unique_id else unique_id
                appears_in = entity_sources.get(base_id, {data['source_bucket']})

                matches.append({
                    'unique_id': unique_id,
                    'entity_id': entity_id,
                    'type': data.get('entity_type', 'unknown'),
                    'description': description[:200],
                    'source_bucket': data['source_bucket'],
                    'appears_in': list(appears_in),
                    'cross_bucket': len(appears_in) > 1
                })

        return matches

    def find_cross_bucket_entities(self, min_buckets: int = 2) -> List[Dict]:
        """
        Find entities that appear in multiple buckets.

        Args:
            min_buckets: Minimum number of buckets entity must appear in

        Returns:
            List of entities with their bucket appearances
        """
        _, _, entity_sources = self.load_all_graphs()

        cross_bucket = []
        for entity_id, buckets in entity_sources.items():
            if len(buckets) >= min_buckets:
                cross_bucket.append({
                    'entity_id': entity_id,
                    'buckets': list(buckets),
                    'count': len(buckets)
                })

        # Sort by count
        cross_bucket.sort(key=lambda x: x['count'], reverse=True)
        return cross_bucket

    def get_statistics(self) -> Dict:
        """Get combined statistics across all buckets."""
        entities, relationships, entity_sources = self.load_all_graphs()

        # Per-bucket stats
        bucket_stats = defaultdict(lambda: {'entities': 0, 'relationships': 0})
        for entity_data in entities.values():
            bucket = entity_data['source_bucket']
            bucket_stats[bucket]['entities'] += 1

        for rel in relationships:
            bucket = rel['source_bucket']
            bucket_stats[bucket]['relationships'] += 1

        # Entity type distribution
        type_counts = Counter()
        for entity in entities.values():
            etype = entity.get('entity_type', 'unknown')
            type_counts[etype] += 1

        # Cross-bucket entities
        cross_bucket_count = sum(1 for buckets in entity_sources.values() if len(buckets) > 1)

        return {
            'total_entities': len(entities),
            'total_relationships': len(relationships),
            'bucket_stats': dict(bucket_stats),
            'entity_types': dict(type_counts),
            'cross_bucket_entities': cross_bucket_count,
            'unique_base_entities': len(entity_sources)
        }

    def create_combined_visualization(
        self,
        output_path: str = "combined_knowledge_graph.html",
        max_nodes_per_bucket: Optional[int] = None,
        entity_types: Optional[List[str]] = None,
        highlight_cross_bucket: bool = True,
        color_by: str = "bucket",  # "bucket" or "type"
        width: str = "100%",
        height: str = "900px"
    ) -> str:
        """
        Create unified visualization combining all buckets.

        Args:
            output_path: Output HTML filename
            max_nodes_per_bucket: Limit nodes per bucket
            entity_types: Filter by entity types
            highlight_cross_bucket: Highlight entities appearing in multiple buckets
            color_by: Color scheme ("bucket" or "type")
            width: Visualization width
            height: Visualization height

        Returns:
            Path to generated HTML file
        """
        if not PYVIS_AVAILABLE:
            console.print("[red]Error: pyvis not installed[/red]")
            console.print("Install with: [cyan]pip install pyvis[/cyan]")
            return None

        entities, relationships, entity_sources = self.load_all_graphs()

        # Filter by entity type
        if entity_types:
            entity_types_lower = [et.lower() for et in entity_types]
            entities = {
                uid: data for uid, data in entities.items()
                if data.get('entity_type', '').lower() in entity_types_lower
            }

        # Limit per bucket
        if max_nodes_per_bucket:
            # Count connections per entity
            connection_counts = Counter()
            for rel in relationships:
                connection_counts[rel['source']] += 1
                connection_counts[rel['target']] += 1

            # Get top N per bucket
            filtered_entities = {}
            for bucket_name in self.bucket_names:
                bucket_entities = {
                    uid: data for uid, data in entities.items()
                    if data['source_bucket'] == bucket_name
                }

                # Sort by connections and take top N
                top_entities = sorted(
                    bucket_entities.keys(),
                    key=lambda uid: connection_counts[uid],
                    reverse=True
                )[:max_nodes_per_bucket]

                for uid in top_entities:
                    filtered_entities[uid] = entities[uid]

            entities = filtered_entities

        # Filter relationships to only include filtered entities
        entity_ids = set(entities.keys())
        relationships = [
            r for r in relationships
            if r['source'] in entity_ids and r['target'] in entity_ids
        ]

        console.print(f"\n[cyan]Creating combined visualization with {len(entities):,} nodes and {len(relationships):,} edges...[/cyan]")

        # Create network
        net = Network(
            width=width,
            height=height,
            bgcolor='#1a1a1a',
            font_color='#ffffff',
            directed=False
        )

        # Configure physics
        net.set_options("""
        {
          "physics": {
            "forceAtlas2Based": {
              "gravitationalConstant": -50,
              "centralGravity": 0.01,
              "springLength": 200,
              "springConstant": 0.08,
              "damping": 0.4,
              "avoidOverlap": 0.5
            },
            "maxVelocity": 50,
            "solver": "forceAtlas2Based",
            "timestep": 0.35,
            "stabilization": {"enabled": true, "iterations": 100}
          },
          "interaction": {
            "hover": true,
            "tooltipDelay": 100,
            "navigationButtons": true,
            "keyboard": true
          }
        }
        """)

        # Add nodes
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Adding nodes...", total=len(entities))

            for unique_id, data in entities.items():
                entity_id = data.get('entity_id', unique_id)
                entity_type = data.get('entity_type', 'default')
                bucket = data['source_bucket']

                # Determine color
                if color_by == "bucket":
                    color = self.bucket_colors.get(bucket, self.bucket_colors['default'])
                else:  # color by type
                    color = self.type_colors.get(entity_type, self.type_colors['default'])

                # Highlight cross-bucket entities
                base_id = unique_id.split('::')[1] if '::' in unique_id else unique_id
                is_cross_bucket = len(entity_sources.get(base_id, {bucket})) > 1

                if highlight_cross_bucket and is_cross_bucket:
                    color = '#FFD700'  # Gold
                    border_width = 4
                else:
                    border_width = 2

                # Size based on connections
                connection_count = sum(
                    1 for r in relationships
                    if r['source'] == unique_id or r['target'] == unique_id
                )
                size = min(10 + (connection_count * 2), 50)

                # Tooltip
                desc = data.get('description', '')
                if desc:
                    desc_parts = desc.split('<SEP>')
                    desc = desc_parts[0][:200] + ('...' if len(desc_parts[0]) > 200 else '')

                appears_in = entity_sources.get(base_id, {bucket})

                title = f"""
                <b>{entity_id}</b><br>
                Type: {entity_type}<br>
                Source: {bucket}<br>
                Appears in: {', '.join(appears_in)}<br>
                Connections: {connection_count}<br>
                <hr>
                {desc}
                """

                net.add_node(
                    unique_id,
                    label=entity_id[:30] + ('...' if len(entity_id) > 30 else ''),
                    title=title,
                    color=color,
                    size=size,
                    borderWidth=border_width
                )

                progress.update(task, advance=1)

        # Add edges
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Adding edges...", total=len(relationships))

            for rel in relationships:
                weight = rel.get('weight', 1.0)
                edge_width = min(0.5 + (weight / 2), 5)

                # Color edges by source bucket
                bucket = rel['source_bucket']
                edge_color = self.bucket_colors.get(bucket, '#666666')

                desc = rel.get('description', '')
                title = f"Weight: {weight:.2f}<br>Source: {bucket}"
                if desc:
                    title += f"<br>{desc[:150]}"

                net.add_edge(
                    rel['source'],
                    rel['target'],
                    value=edge_width,
                    title=title,
                    color={'color': edge_color, 'opacity': 0.5}
                )

                progress.update(task, advance=1)

        # Save
        output_path = Path(output_path)
        net.save_graph(str(output_path))

        console.print(f"\n[green]✓ Visualization saved to:[/green] [cyan]{output_path.absolute()}[/cyan]")

        return str(output_path.absolute())


def main():
    """Interactive CLI for multi-bucket exploration."""
    from rich.prompt import Prompt, Confirm
    import webbrowser

    # Find buckets
    bucket_dir = Path("./rag_buckets")

    if not bucket_dir.exists():
        console.print("[red]No rag_buckets directory found[/red]")
        return

    available_buckets = [
        d for d in bucket_dir.iterdir()
        if d.is_dir() and not d.name.startswith('.')
    ]

    if not available_buckets:
        console.print("[yellow]No buckets found[/yellow]")
        return

    console.print(Panel.fit(
        "[bold cyan]Multi-Bucket Knowledge Graph Explorer[/bold cyan]\n\n"
        "Combine and explore multiple RAG buckets simultaneously",
        border_style="cyan"
    ))

    # Show available buckets
    table = Table(title="Available Buckets", show_header=True, header_style="bold cyan")
    table.add_column("#", style="dim")
    table.add_column("Bucket Name", style="green")

    for idx, bucket in enumerate(available_buckets, 1):
        table.add_row(str(idx), bucket.name)

    console.print("\n")
    console.print(table)

    # Select buckets
    console.print("\n[bold]Select buckets to combine:[/bold]")
    console.print("[dim]Enter numbers separated by commas (e.g., 1,2,3) or 'all'[/dim]")

    choice = Prompt.ask("Bucket selection", default="all")

    if choice.lower() == 'all':
        selected_buckets = available_buckets
    else:
        indices = [int(i.strip()) - 1 for i in choice.split(',')]
        selected_buckets = [available_buckets[i] for i in indices]

    console.print(f"\n[green]Selected:[/green] {', '.join(b.name for b in selected_buckets)}")

    # Initialize explorer
    explorer = MultiBucketExplorer(selected_buckets)

    # Interactive menu
    while True:
        console.print("\n[bold]What would you like to do?[/bold]")
        console.print("[1] View combined statistics")
        console.print("[2] Search across all buckets")
        console.print("[3] Find cross-bucket entities")
        console.print("[4] Create combined visualization")
        console.print("[5] Exit")

        choice = Prompt.ask("\nChoose an option", choices=["1", "2", "3", "4", "5"], default="1")

        if choice == "1":
            stats = explorer.get_statistics()

            console.print(Panel.fit(
                f"Total Entities: {stats['total_entities']:,}\n"
                f"Total Relationships: {stats['total_relationships']:,}\n"
                f"Unique Base Entities: {stats['unique_base_entities']:,}\n"
                f"Cross-Bucket Entities: {stats['cross_bucket_entities']:,}",
                title="Combined Statistics",
                border_style="cyan"
            ))

            # Per-bucket breakdown
            console.print("\n[bold]Per-Bucket Breakdown:[/bold]")
            bucket_table = Table(show_header=True, header_style="bold cyan")
            bucket_table.add_column("Bucket", style="green")
            bucket_table.add_column("Entities", justify="right")
            bucket_table.add_column("Relationships", justify="right")

            for bucket, data in stats['bucket_stats'].items():
                bucket_table.add_row(
                    bucket,
                    f"{data['entities']:,}",
                    f"{data['relationships']:,}"
                )

            console.print(bucket_table)

        elif choice == "2":
            query = Prompt.ask("\nSearch query")

            # Optional filters
            filter_type = Confirm.ask("Filter by entity type?", default=False)
            entity_types = None
            if filter_type:
                types_input = Prompt.ask("Entity types (comma-separated)")
                entity_types = [t.strip() for t in types_input.split(',')]

            results = explorer.search_across_buckets(query, entity_types=entity_types)

            if not results:
                console.print("[yellow]No matches found[/yellow]")
            else:
                console.print(f"\n[green]Found {len(results)} matches:[/green]")

                for i, result in enumerate(results[:20], 1):
                    cross_label = " [gold]⭐ CROSS-BUCKET[/gold]" if result['cross_bucket'] else ""
                    console.print(f"\n{i}. [bold]{result['entity_id']}[/bold] ({result['type']}){cross_label}")
                    console.print(f"   Source: {result['source_bucket']}")
                    if result['cross_bucket']:
                        console.print(f"   Also in: {', '.join(result['appears_in'])}")
                    console.print(f"   [dim]{result['description'][:150]}...[/dim]")

                if len(results) > 20:
                    console.print(f"\n[dim]... and {len(results) - 20} more[/dim]")

        elif choice == "3":
            cross_bucket = explorer.find_cross_bucket_entities()

            if not cross_bucket:
                console.print("[yellow]No cross-bucket entities found[/yellow]")
            else:
                console.print(f"\n[green]Found {len(cross_bucket)} entities appearing in multiple buckets:[/green]")

                table = Table(show_header=True, header_style="bold cyan")
                table.add_column("#", style="dim", width=4)
                table.add_column("Entity", style="green")
                table.add_column("Buckets", style="cyan")
                table.add_column("Count", justify="right")

                for i, entity in enumerate(cross_bucket[:30], 1):
                    table.add_row(
                        str(i),
                        entity['entity_id'],
                        ', '.join(entity['buckets']),
                        str(entity['count'])
                    )

                console.print(table)

                if len(cross_bucket) > 30:
                    console.print(f"\n[dim]... and {len(cross_bucket) - 30} more[/dim]")

        elif choice == "4":
            console.print("\n[cyan]Combined Visualization Options[/cyan]")

            # Max nodes per bucket
            max_nodes = None
            if Confirm.ask("Limit nodes per bucket?", default=True):
                max_nodes = int(Prompt.ask("Max nodes per bucket", default="100"))

            # Color scheme
            console.print("\nColor by:")
            console.print("[1] Source bucket (red=books, teal=plays, gold=scripts)")
            console.print("[2] Entity type (red=person, orange=concept, etc.)")
            color_choice = Prompt.ask("Choose", choices=["1", "2"], default="1")
            color_by = "bucket" if color_choice == "1" else "type"

            # Highlight cross-bucket
            highlight = Confirm.ask("Highlight cross-bucket entities in gold?", default=True)

            output_path = Prompt.ask("Output filename", default="combined_graph.html")

            # Create
            result = explorer.create_combined_visualization(
                output_path=output_path,
                max_nodes_per_bucket=max_nodes,
                highlight_cross_bucket=highlight,
                color_by=color_by
            )

            if result and Confirm.ask("\nOpen in browser?", default=True):
                webbrowser.open(f"file://{result}")

        elif choice == "5":
            console.print("\n[dim]Goodbye![/dim]")
            break


if __name__ == "__main__":
    main()
