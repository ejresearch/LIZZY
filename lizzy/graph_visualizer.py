"""
Graph Visualizer - Neo4j-style interactive visualization for LightRAG buckets.

Creates interactive HTML visualizations using pyvis with:
- Force-directed graph layout
- Node clustering by entity type
- Interactive zoom, pan, and drag
- Hover tooltips with entity details
- Filtering by entity type and relationship strength
- Search highlighting
"""

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from collections import Counter
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

try:
    from pyvis.network import Network
    PYVIS_AVAILABLE = True
except ImportError:
    PYVIS_AVAILABLE = False

console = Console()


class GraphVisualizer:
    """
    Create Neo4j-style interactive visualizations of LightRAG knowledge graphs.

    Features:
    - Interactive force-directed layout
    - Color-coded nodes by entity type
    - Edge thickness by relationship weight
    - Filtering and search
    - Export to HTML
    """

    def __init__(self, bucket_path: Path):
        """
        Initialize visualizer for a bucket.

        Args:
            bucket_path: Path to LightRAG bucket directory
        """
        self.bucket_path = bucket_path
        self.graphml_path = bucket_path / "graph_chunk_entity_relation.graphml"

        # Color scheme for entity types (Neo4j-inspired)
        self.type_colors = {
            'person': '#FF6B6B',      # Red
            'organization': '#4ECDC4', # Teal
            'location': '#45B7D1',     # Blue
            'concept': '#FFA07A',      # Light salmon
            'event': '#98D8C8',        # Mint
            'technique': '#F7DC6F',    # Yellow
            'theme': '#BB8FCE',        # Purple
            'character': '#FF6B9D',    # Pink
            'default': '#95A5A6'       # Gray
        }

        # Cache
        self._entities = None
        self._relationships = None

    def check_dependencies(self) -> bool:
        """Check if required dependencies are installed."""
        if not PYVIS_AVAILABLE:
            console.print("[red]Error: pyvis not installed[/red]")
            console.print("\nInstall with: [cyan]pip install pyvis[/cyan]")
            return False
        return True

    def load_graph_data(self) -> Tuple[Dict, List]:
        """
        Load entities and relationships from GraphML.

        Returns:
            Tuple of (entities_dict, relationships_list)
        """
        if self._entities and self._relationships:
            return self._entities, self._relationships

        if not self.graphml_path.exists():
            console.print(f"[red]GraphML file not found: {self.graphml_path}[/red]")
            return {}, []

        entities = {}
        relationships = []

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Loading graph data...", total=None)

                tree = ET.parse(self.graphml_path)
                root = tree.getroot()
                ns = {'graphml': 'http://graphml.graphdrawing.org/xmlns'}

                # Load entities (nodes)
                progress.update(task, description="Loading entities...")
                for node in root.findall('.//graphml:node', ns):
                    entity_id = node.get('id')
                    entity_data = {'id': entity_id}

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
                        elif key == 'd4':
                            entity_data['file_path'] = value

                    entities[entity_id] = entity_data

                # Load relationships (edges)
                progress.update(task, description="Loading relationships...")
                for edge in root.findall('.//graphml:edge', ns):
                    rel_data = {
                        'source': edge.get('source'),
                        'target': edge.get('target'),
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

                    relationships.append(rel_data)

                progress.update(task, description="Done!")

        except Exception as e:
            console.print(f"[red]Error loading graph data: {e}[/red]")
            return {}, []

        self._entities = entities
        self._relationships = relationships

        console.print(f"[green]✓[/green] Loaded {len(entities):,} entities and {len(relationships):,} relationships")
        return entities, relationships

    def create_visualization(
        self,
        output_path: str = "knowledge_graph.html",
        max_nodes: Optional[int] = None,
        entity_types: Optional[List[str]] = None,
        min_connections: int = 0,
        highlight_entities: Optional[List[str]] = None,
        width: str = "100%",
        height: str = "900px",
        physics_enabled: bool = True
    ) -> str:
        """
        Create interactive graph visualization.

        Args:
            output_path: Output HTML file path
            max_nodes: Maximum number of nodes to display (most connected)
            entity_types: Filter to specific entity types
            min_connections: Minimum connections required for a node
            highlight_entities: List of entity IDs to highlight
            width: Visualization width
            height: Visualization height
            physics_enabled: Enable force-directed physics simulation

        Returns:
            Path to generated HTML file
        """
        if not self.check_dependencies():
            return None

        entities, relationships = self.load_graph_data()

        if not entities or not relationships:
            console.print("[yellow]No graph data to visualize[/yellow]")
            return None

        # Filter entities by type if specified
        if entity_types:
            entity_types_lower = [et.lower() for et in entity_types]
            entities = {
                eid: data for eid, data in entities.items()
                if data.get('entity_type', '').lower() in entity_types_lower
            }
            # Filter relationships to only include filtered entities
            entity_ids = set(entities.keys())
            relationships = [
                r for r in relationships
                if r['source'] in entity_ids and r['target'] in entity_ids
            ]

        # Count connections per entity
        connection_counts = Counter()
        for rel in relationships:
            connection_counts[rel['source']] += 1
            connection_counts[rel['target']] += 1

        # Filter by minimum connections
        if min_connections > 0:
            entities = {
                eid: data for eid, data in entities.items()
                if connection_counts[eid] >= min_connections
            }
            entity_ids = set(entities.keys())
            relationships = [
                r for r in relationships
                if r['source'] in entity_ids and r['target'] in entity_ids
            ]

        # Limit to top N most connected nodes if specified
        if max_nodes and len(entities) > max_nodes:
            top_entities = [eid for eid, _ in connection_counts.most_common(max_nodes)]
            entities = {eid: entities[eid] for eid in top_entities if eid in entities}
            entity_ids = set(entities.keys())
            relationships = [
                r for r in relationships
                if r['source'] in entity_ids and r['target'] in entity_ids
            ]

        console.print(f"\n[cyan]Creating visualization with {len(entities):,} nodes and {len(relationships):,} edges...[/cyan]")

        # Create network
        net = Network(
            width=width,
            height=height,
            bgcolor='#1a1a1a',
            font_color='#ffffff',
            directed=False
        )

        # Configure physics
        if physics_enabled:
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
                "stabilization": {
                  "enabled": true,
                  "iterations": 100
                }
              },
              "interaction": {
                "hover": true,
                "tooltipDelay": 100,
                "navigationButtons": true,
                "keyboard": true
              },
              "nodes": {
                "font": {
                  "size": 14,
                  "face": "arial"
                },
                "borderWidth": 2,
                "borderWidthSelected": 4
              },
              "edges": {
                "smooth": {
                  "type": "continuous"
                }
              }
            }
            """)
        else:
            net.toggle_physics(False)

        # Add nodes
        highlight_set = set(highlight_entities or [])

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Adding nodes...", total=len(entities))

            for entity_id, data in entities.items():
                entity_type = data.get('entity_type', 'default').lower()
                color = self.type_colors.get(entity_type, self.type_colors['default'])

                # Highlight searched/specified entities
                if entity_id in highlight_set:
                    color = '#FFD700'  # Gold for highlighted
                    border_color = '#FFA500'
                    border_width = 4
                else:
                    border_color = color
                    border_width = 2

                # Node size based on connections
                connections = connection_counts[entity_id]
                size = min(10 + (connections * 2), 50)

                # Tooltip
                desc = data.get('description', '')
                if desc:
                    # Take first description if multiple
                    desc_parts = desc.split('<SEP>')
                    desc = desc_parts[0][:200] + ('...' if len(desc_parts[0]) > 200 else '')

                title = f"""
                <b>{entity_id}</b><br>
                Type: {entity_type}<br>
                Connections: {connections}<br>
                <hr>
                {desc}
                """

                net.add_node(
                    entity_id,
                    label=entity_id[:30] + ('...' if len(entity_id) > 30 else ''),
                    title=title,
                    color=color,
                    size=size,
                    borderWidth=border_width,
                    borderWidthSelected=border_width + 2
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
                source = rel['source']
                target = rel['target']
                weight = rel.get('weight', 1.0)

                # Edge width based on weight
                edge_width = min(0.5 + (weight / 2), 5)

                # Tooltip
                desc = rel.get('description', '')
                keywords = rel.get('keywords', '')

                title = f"Weight: {weight:.2f}"
                if desc:
                    title += f"<br>{desc[:150]}"
                if keywords:
                    title += f"<br>Keywords: {keywords}"

                net.add_edge(
                    source,
                    target,
                    value=edge_width,
                    title=title,
                    color={'color': '#666666', 'highlight': '#00ff00'}
                )

                progress.update(task, advance=1)

        # Save
        output_path = Path(output_path)
        net.save_graph(str(output_path))

        console.print(f"\n[green]✓ Visualization saved to:[/green] [cyan]{output_path.absolute()}[/cyan]")
        console.print(f"[dim]Open in browser to explore the knowledge graph[/dim]")

        return str(output_path.absolute())

    def get_entity_statistics(self) -> Dict:
        """Get statistics about entities in the graph."""
        entities, relationships = self.load_graph_data()

        if not entities:
            return {}

        # Count by type
        type_counts = Counter()
        for entity in entities.values():
            entity_type = entity.get('entity_type', 'unknown')
            type_counts[entity_type] += 1

        # Connection statistics
        connection_counts = Counter()
        for rel in relationships:
            connection_counts[rel['source']] += 1
            connection_counts[rel['target']] += 1

        avg_connections = sum(connection_counts.values()) / len(entities) if entities else 0

        return {
            'total_entities': len(entities),
            'total_relationships': len(relationships),
            'entity_types': dict(type_counts),
            'avg_connections': avg_connections,
            'max_connections': max(connection_counts.values()) if connection_counts else 0,
            'most_connected': connection_counts.most_common(10)
        }


def main():
    """CLI for graph visualizer."""
    from rich.prompt import Prompt, Confirm
    from rich.table import Table
    import sys
    import webbrowser

    # Check dependencies first
    if not PYVIS_AVAILABLE:
        console.print("[red]Error: pyvis is not installed[/red]")
        console.print("\nInstall with: [cyan]pip install pyvis[/cyan]")
        sys.exit(1)

    # List available buckets
    bucket_dir = Path("./rag_buckets")

    if not bucket_dir.exists():
        console.print("[red]No rag_buckets directory found[/red]")
        sys.exit(1)

    buckets = [d for d in bucket_dir.iterdir()
               if d.is_dir() and not d.name.startswith('.')]

    if not buckets:
        console.print("[yellow]No buckets found[/yellow]")
        sys.exit(1)

    # Show bucket selection
    console.print(Panel.fit(
        "[bold cyan]LightRAG Knowledge Graph Visualizer[/bold cyan]\n\n"
        "Create Neo4j-style interactive visualizations",
        border_style="cyan"
    ))

    table = Table(title="Available Buckets", show_header=True, header_style="bold cyan")
    table.add_column("#", style="dim")
    table.add_column("Bucket Name", style="green")

    for idx, bucket in enumerate(buckets, 1):
        table.add_row(str(idx), bucket.name)

    console.print("\n")
    console.print(table)

    # Select bucket
    bucket_idx = int(Prompt.ask(
        "\nChoose bucket number",
        choices=[str(i) for i in range(1, len(buckets) + 1)]
    ))

    bucket = buckets[bucket_idx - 1]
    visualizer = GraphVisualizer(bucket)

    # Show statistics
    console.print("\n[bold]Analyzing bucket...[/bold]")
    stats = visualizer.get_entity_statistics()

    if stats:
        console.print(Panel.fit(
            f"Entities: {stats['total_entities']:,}\n"
            f"Relationships: {stats['total_relationships']:,}\n"
            f"Avg Connections: {stats['avg_connections']:.1f}\n"
            f"Max Connections: {stats['max_connections']:,}",
            title=f"Bucket: {bucket.name}",
            border_style="cyan"
        ))

        # Show entity types
        if stats['entity_types']:
            console.print("\n[bold]Entity Types:[/bold]")
            for etype, count in sorted(stats['entity_types'].items(),
                                       key=lambda x: x[1], reverse=True)[:10]:
                console.print(f"  • {etype}: {count:,}")

    # Visualization options
    console.print("\n[bold]Visualization Options[/bold]")

    # Max nodes
    max_nodes = None
    if stats['total_entities'] > 500:
        limit = Confirm.ask(
            f"Graph has {stats['total_entities']:,} nodes. Limit for performance?",
            default=True
        )
        if limit:
            max_nodes = int(Prompt.ask(
                "Max nodes to display",
                default="200"
            ))

    # Entity type filter
    filter_types = Confirm.ask("Filter by entity type?", default=False)
    entity_types = None
    if filter_types and stats.get('entity_types'):
        console.print("\nAvailable types:", ", ".join(stats['entity_types'].keys()))
        types_input = Prompt.ask("Entity types (comma-separated)")
        entity_types = [t.strip() for t in types_input.split(',')]

    # Min connections
    min_connections = 0
    if Confirm.ask("Filter by minimum connections?", default=False):
        min_connections = int(Prompt.ask("Minimum connections", default="2"))

    # Output path
    output_path = Prompt.ask(
        "Output filename",
        default=f"{bucket.name}_graph.html"
    )

    # Create visualization
    console.print("\n")
    result = visualizer.create_visualization(
        output_path=output_path,
        max_nodes=max_nodes,
        entity_types=entity_types,
        min_connections=min_connections,
        physics_enabled=True
    )

    if result:
        # Ask to open in browser
        if Confirm.ask("\nOpen in browser?", default=True):
            webbrowser.open(f"file://{result}")


if __name__ == "__main__":
    main()
