#!/usr/bin/env python3
"""
Example visualizations for LightRAG knowledge graphs.

Run different visualization scenarios to explore your RAG buckets.
"""

from pathlib import Path
from lizzy.graph_visualizer import GraphVisualizer


def example_1_full_overview():
    """Create overview visualization of entire bucket (filtered)."""
    print("Example 1: Full Overview (Top 200 nodes)")
    print("-" * 50)

    visualizer = GraphVisualizer(Path('rag_buckets/books'))

    visualizer.create_visualization(
        output_path='example_1_overview.html',
        max_nodes=200,
        min_connections=2,
        physics_enabled=True
    )

    print("✓ Created example_1_overview.html\n")


def example_2_entity_type_filter():
    """Focus on specific entity types."""
    print("Example 2: Entity Type Filter (Concepts & Themes)")
    print("-" * 50)

    visualizer = GraphVisualizer(Path('rag_buckets/books'))

    visualizer.create_visualization(
        output_path='example_2_concepts_themes.html',
        entity_types=['concept', 'theme', 'technique'],
        max_nodes=150,
        physics_enabled=True
    )

    print("✓ Created example_2_concepts_themes.html\n")


def example_3_character_network():
    """Character relationship network from scripts."""
    print("Example 3: Character Network")
    print("-" * 50)

    visualizer = GraphVisualizer(Path('rag_buckets/scripts'))

    visualizer.create_visualization(
        output_path='example_3_character_network.html',
        entity_types=['person', 'character'],
        max_nodes=100,
        min_connections=1,
        height='1200px',
        physics_enabled=True
    )

    print("✓ Created example_3_character_network.html\n")


def example_4_highly_connected():
    """Show only highly connected entities."""
    print("Example 4: Highly Connected Entities Only")
    print("-" * 50)

    visualizer = GraphVisualizer(Path('rag_buckets/books'))

    visualizer.create_visualization(
        output_path='example_4_highly_connected.html',
        min_connections=5,  # Only entities with 5+ connections
        max_nodes=100,
        physics_enabled=True
    )

    print("✓ Created example_4_highly_connected.html\n")


def example_5_highlighted_entities():
    """Highlight specific entities of interest."""
    print("Example 5: Highlighted Entities")
    print("-" * 50)

    visualizer = GraphVisualizer(Path('rag_buckets/books'))

    # Get statistics to find top entities
    stats = visualizer.get_entity_statistics()
    top_10 = [entity for entity, count in stats['most_connected'][:10]]

    print(f"Highlighting top 10 entities: {', '.join(top_10[:3])}...")

    visualizer.create_visualization(
        output_path='example_5_highlighted.html',
        max_nodes=150,
        highlight_entities=top_10,
        physics_enabled=True
    )

    print("✓ Created example_5_highlighted.html (gold nodes are top 10)\n")


def example_6_compare_buckets():
    """Create visualizations for all buckets to compare."""
    print("Example 6: Compare All Buckets")
    print("-" * 50)

    bucket_names = ['books', 'plays', 'scripts']

    for bucket_name in bucket_names:
        bucket_path = Path(f'rag_buckets/{bucket_name}')

        if not bucket_path.exists():
            print(f"⚠ Skipping {bucket_name} (not found)")
            continue

        print(f"  Processing {bucket_name}...")

        visualizer = GraphVisualizer(bucket_path)

        visualizer.create_visualization(
            output_path=f'example_6_{bucket_name}.html',
            max_nodes=150,
            min_connections=2,
            physics_enabled=True
        )

    print("✓ Created comparison visualizations for all buckets")
    print("  Open them side-by-side to compare knowledge structures\n")


def example_7_static_layout():
    """Create static layout (no physics) for large graphs."""
    print("Example 7: Static Layout (No Physics)")
    print("-" * 50)

    visualizer = GraphVisualizer(Path('rag_buckets/scripts'))

    visualizer.create_visualization(
        output_path='example_7_static.html',
        max_nodes=200,
        min_connections=2,
        physics_enabled=False  # Static for faster rendering
    )

    print("✓ Created example_7_static.html (static layout)\n")


def main():
    """Run all examples or selected ones."""
    print("\n" + "=" * 50)
    print("LightRAG Knowledge Graph Visualization Examples")
    print("=" * 50 + "\n")

    examples = {
        '1': ('Full Overview', example_1_full_overview),
        '2': ('Entity Type Filter', example_2_entity_type_filter),
        '3': ('Character Network', example_3_character_network),
        '4': ('Highly Connected', example_4_highly_connected),
        '5': ('Highlighted Entities', example_5_highlighted_entities),
        '6': ('Compare Buckets', example_6_compare_buckets),
        '7': ('Static Layout', example_7_static_layout),
        'all': ('Run All Examples', None)
    }

    print("Available examples:")
    for key, (name, _) in examples.items():
        print(f"  [{key}] {name}")

    print()
    choice = input("Select example (1-7, 'all', or Enter to run all): ").strip().lower()

    if not choice or choice == 'all':
        # Run all examples
        for key, (name, func) in examples.items():
            if func:  # Skip the 'all' entry
                try:
                    func()
                except Exception as e:
                    print(f"✗ Error in {name}: {e}\n")
    else:
        # Run selected example
        if choice in examples and examples[choice][1]:
            try:
                examples[choice][1]()
            except Exception as e:
                print(f"✗ Error: {e}\n")
        else:
            print("Invalid choice")

    print("\n" + "=" * 50)
    print("Done! Open the HTML files in your browser.")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    main()
