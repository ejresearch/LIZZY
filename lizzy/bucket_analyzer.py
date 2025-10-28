"""
Bucket Analyzer - Explore and visualize LightRAG bucket contents.

Provides tools to:
- Query entities and relationships from GraphML
- Analyze graph structure and statistics
- Search for specific entities/concepts
- Visualize knowledge graph structure
"""

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import Counter
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree

console = Console()


class BucketAnalyzer:
    """
    Analyze LightRAG bucket contents without Neo4j.

    Parses GraphML and JSON files to provide insights into:
    - Entities (nodes)
    - Relationships (edges)
    - Document sources
    - Graph statistics
    """

    def __init__(self, bucket_path: Path):
        """
        Initialize analyzer for a bucket.

        Args:
            bucket_path: Path to LightRAG bucket directory
        """
        self.bucket_path = bucket_path
        self.graphml_path = bucket_path / "graph_chunk_entity_relation.graphml"
        self.entities_path = bucket_path / "kv_store_full_entities.json"
        self.relations_path = bucket_path / "kv_store_full_relations.json"
        self.docs_path = bucket_path / "kv_store_full_docs.json"

        # Cache
        self._entities = None
        self._relationships = None
        self._documents = None

    def validate_bucket(self) -> bool:
        """Check if bucket has required files."""
        required = [self.graphml_path, self.docs_path]
        return all(f.exists() for f in required)

    def load_entities(self) -> Dict:
        """Load entity data from GraphML."""
        if self._entities is not None:
            return self._entities

        if not self.graphml_path.exists():
            return {}

        entities = {}

        try:
            tree = ET.parse(self.graphml_path)
            root = tree.getroot()

            # Define namespace
            ns = {'graphml': 'http://graphml.graphdrawing.org/xmlns'}

            for node in root.findall('.//graphml:node', ns):
                entity_id = node.get('id')
                entity_data = {}

                for data in node.findall('graphml:data', ns):
                    key = data.get('key')
                    value = data.text or ""

                    # Map key IDs to meaningful names
                    if key == 'd0':
                        entity_data['entity_id'] = value
                    elif key == 'd1':
                        entity_data['entity_type'] = value
                    elif key == 'd2':
                        entity_data['description'] = value
                    elif key == 'd3':
                        entity_data['source_id'] = value
                    elif key == 'd4':
                        entity_data['file_path'] = value

                entities[entity_id] = entity_data

        except Exception as e:
            console.print(f"[red]Error parsing GraphML: {e}[/red]")
            return {}

        self._entities = entities
        return entities

    def load_relationships(self) -> List[Dict]:
        """Load relationship data from GraphML."""
        if self._relationships is not None:
            return self._relationships

        if not self.graphml_path.exists():
            return []

        relationships = []

        try:
            tree = ET.parse(self.graphml_path)
            root = tree.getroot()

            ns = {'graphml': 'http://graphml.graphdrawing.org/xmlns'}

            for edge in root.findall('.//graphml:edge', ns):
                rel_data = {
                    'source': edge.get('source'),
                    'target': edge.get('target')
                }

                for data in edge.findall('graphml:data', ns):
                    key = data.get('key')
                    value = data.text or ""

                    # Map edge attributes
                    if key == 'd6':
                        rel_data['weight'] = float(value) if value else 0.0
                    elif key == 'd7':
                        rel_data['description'] = value
                    elif key == 'd8':
                        rel_data['keywords'] = value
                    elif key == 'd9':
                        rel_data['source_id'] = value

                relationships.append(rel_data)

        except Exception as e:
            console.print(f"[red]Error parsing relationships: {e}[/red]")
            return []

        self._relationships = relationships
        return relationships

    def load_documents(self) -> Dict:
        """Load document metadata."""
        if self._documents is not None:
            return self._documents

        if not self.docs_path.exists():
            return {}

        try:
            with open(self.docs_path, 'r') as f:
                self._documents = json.load(f)
            return self._documents
        except Exception as e:
            console.print(f"[red]Error loading documents: {e}[/red]")
            return {}

    def get_statistics(self) -> Dict:
        """Get bucket statistics."""
        entities = self.load_entities()
        relationships = self.load_relationships()
        documents = self.load_documents()

        # Entity type distribution
        entity_types = Counter()
        for entity in entities.values():
            etype = entity.get('entity_type', 'unknown')
            entity_types[etype] += 1

        # Relationship statistics
        total_weight = sum(r.get('weight', 0) for r in relationships)
        avg_weight = total_weight / len(relationships) if relationships else 0

        return {
            'total_entities': len(entities),
            'total_relationships': len(relationships),
            'total_documents': len(documents),
            'entity_types': dict(entity_types),
            'avg_relationship_weight': avg_weight,
            'total_relationship_weight': total_weight
        }

    def search_entities(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Search for entities by name or description.

        Args:
            query: Search term
            limit: Maximum results

        Returns:
            List of matching entities
        """
        entities = self.load_entities()
        query_lower = query.lower()

        matches = []
        for entity_id, data in entities.items():
            # Search in ID and description
            if (query_lower in entity_id.lower() or
                query_lower in data.get('description', '').lower()):
                matches.append({
                    'id': entity_id,
                    **data
                })

                if len(matches) >= limit:
                    break

        return matches

    def get_entity_relationships(self, entity_id: str) -> Tuple[List[Dict], List[Dict]]:
        """
        Get all relationships for an entity.

        Args:
            entity_id: Entity to query

        Returns:
            Tuple of (outgoing_relationships, incoming_relationships)
        """
        relationships = self.load_relationships()

        outgoing = [r for r in relationships if r['source'] == entity_id]
        incoming = [r for r in relationships if r['target'] == entity_id]

        return outgoing, incoming

    def get_top_entities(self, limit: int = 10) -> List[Tuple[str, int]]:
        """
        Get most connected entities.

        Args:
            limit: Number of results

        Returns:
            List of (entity_id, connection_count) tuples
        """
        relationships = self.load_relationships()

        # Count connections
        connections = Counter()
        for rel in relationships:
            connections[rel['source']] += 1
            connections[rel['target']] += 1

        return connections.most_common(limit)

    def display_statistics(self) -> None:
        """Display bucket statistics in a nice table."""
        stats = self.get_statistics()

        # Main stats panel
        console.print(Panel.fit(
            f"[bold cyan]{self.bucket_path.name}[/bold cyan]\n\n"
            f"Entities: {stats['total_entities']:,}\n"
            f"Relationships: {stats['total_relationships']:,}\n"
            f"Documents: {stats['total_documents']:,}\n"
            f"Avg Relationship Weight: {stats['avg_relationship_weight']:.2f}",
            title="Bucket Statistics",
            border_style="cyan"
        ))

        # Entity types table
        if stats['entity_types']:
            console.print("\n[bold]Entity Type Distribution:[/bold]")
            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("Type", style="yellow")
            table.add_column("Count", style="green", justify="right")
            table.add_column("Percentage", style="cyan", justify="right")

            total = stats['total_entities']
            for etype, count in sorted(stats['entity_types'].items(),
                                      key=lambda x: x[1], reverse=True):
                pct = (count / total * 100) if total > 0 else 0
                table.add_row(etype, f"{count:,}", f"{pct:.1f}%")

            console.print(table)

    def display_top_entities(self, limit: int = 15) -> None:
        """Display most connected entities."""
        top = self.get_top_entities(limit)

        if not top:
            console.print("[yellow]No entities found[/yellow]")
            return

        console.print(f"\n[bold]Top {limit} Most Connected Entities:[/bold]")
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("#", style="dim", width=4)
        table.add_column("Entity", style="green")
        table.add_column("Connections", style="cyan", justify="right")

        for idx, (entity_id, count) in enumerate(top, 1):
            table.add_row(str(idx), entity_id, str(count))

        console.print(table)

    def display_entity_details(self, entity_id: str) -> None:
        """Display detailed information about an entity."""
        entities = self.load_entities()

        if entity_id not in entities:
            console.print(f"[red]Entity '{entity_id}' not found[/red]")
            return

        entity = entities[entity_id]

        # Entity info
        console.print(f"\n[bold cyan]{entity_id}[/bold cyan]")
        console.print(f"Type: [yellow]{entity.get('entity_type', 'unknown')}[/yellow]")

        # Description
        desc = entity.get('description', '')
        if desc:
            # Split by <SEP> if present
            descriptions = desc.split('<SEP>')
            console.print(f"\n[bold]Description:[/bold]")
            for i, d in enumerate(descriptions[:5], 1):  # Show first 5
                console.print(f"  {i}. {d.strip()}")
            if len(descriptions) > 5:
                console.print(f"  [dim]... and {len(descriptions) - 5} more[/dim]")

        # Relationships
        outgoing, incoming = self.get_entity_relationships(entity_id)

        console.print(f"\n[bold]Relationships:[/bold]")
        console.print(f"  Outgoing: {len(outgoing)}")
        console.print(f"  Incoming: {len(incoming)}")

        # Show some relationships
        if outgoing:
            console.print(f"\n[bold]Connected to:[/bold]")
            for rel in outgoing[:10]:
                console.print(f"  → {rel['target']}")
                if rel.get('description'):
                    console.print(f"    [dim]{rel['description'][:100]}...[/dim]")


def main():
    """CLI for bucket analyzer."""
    from rich.prompt import Prompt, Confirm
    import sys
    import webbrowser

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
        "[bold cyan]LightRAG Bucket Analyzer[/bold cyan]\n\n"
        "Explore entities, relationships, and knowledge graphs",
        border_style="cyan"
    ))

    table = Table(title="Available Buckets", show_header=True, header_style="bold cyan")
    table.add_column("#", style="dim")
    table.add_column("Bucket Name", style="green")
    table.add_column("Location")

    for idx, bucket in enumerate(buckets, 1):
        table.add_row(str(idx), bucket.name, str(bucket))

    console.print("\n")
    console.print(table)

    # Select bucket
    bucket_idx = int(Prompt.ask(
        "\nChoose bucket number",
        choices=[str(i) for i in range(1, len(buckets) + 1)]
    ))

    bucket = buckets[bucket_idx - 1]
    analyzer = BucketAnalyzer(bucket)

    if not analyzer.validate_bucket():
        console.print(f"[red]Bucket '{bucket.name}' is missing required files[/red]")
        sys.exit(1)

    # Interactive menu
    while True:
        console.print("\n[bold]What would you like to do?[/bold]")
        console.print("[1] View statistics")
        console.print("[2] View top entities")
        console.print("[3] Search entities")
        console.print("[4] View entity details")
        console.print("[5] Create interactive visualization")
        console.print("[6] Exit")

        choice = Prompt.ask("\nChoose an option", choices=["1", "2", "3", "4", "5", "6"], default="1")

        if choice == "1":
            analyzer.display_statistics()

        elif choice == "2":
            limit = int(Prompt.ask("How many entities to show", default="15"))
            analyzer.display_top_entities(limit)

        elif choice == "3":
            query = Prompt.ask("Search query")
            results = analyzer.search_entities(query)

            if not results:
                console.print("[yellow]No matches found[/yellow]")
            else:
                console.print(f"\n[green]Found {len(results)} matches:[/green]")
                for i, entity in enumerate(results, 1):
                    console.print(f"\n{i}. [bold]{entity['id']}[/bold] ({entity.get('entity_type', 'unknown')})")
                    desc = entity.get('description', '')[:150]
                    console.print(f"   [dim]{desc}...[/dim]")

        elif choice == "4":
            entity_id = Prompt.ask("Entity ID")
            analyzer.display_entity_details(entity_id)

        elif choice == "5":
            try:
                from lizzy.graph_visualizer import GraphVisualizer

                console.print("\n[cyan]Creating interactive visualization...[/cyan]")

                # Get visualization options
                max_nodes = None
                entities = analyzer.load_entities()
                if len(entities) > 500:
                    if Confirm.ask(f"Graph has {len(entities):,} nodes. Limit for performance?", default=True):
                        max_nodes = int(Prompt.ask("Max nodes to display", default="200"))

                min_connections = 0
                if Confirm.ask("Filter by minimum connections?", default=False):
                    min_connections = int(Prompt.ask("Minimum connections", default="2"))

                output_path = Prompt.ask("Output filename", default=f"{bucket.name}_graph.html")

                # Create visualization
                visualizer = GraphVisualizer(bucket)
                result = visualizer.create_visualization(
                    output_path=output_path,
                    max_nodes=max_nodes,
                    min_connections=min_connections,
                    physics_enabled=True
                )

                if result and Confirm.ask("\nOpen in browser?", default=True):
                    webbrowser.open(f"file://{result}")

            except ImportError:
                console.print("[red]Error: pyvis not installed[/red]")
                console.print("Install with: [cyan]pip install pyvis[/cyan]")

        elif choice == "6":
            console.print("\n[dim]Goodbye![/dim]")
            break


if __name__ == "__main__":
    main()
