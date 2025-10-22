# Knowledge Graph Visualization Guide

Neo4j-style interactive visualization for your LightRAG knowledge graphs.

## Overview

The Graph Visualizer creates beautiful, interactive HTML visualizations of your RAG bucket knowledge graphs using force-directed layouts, similar to Neo4j's browser interface.

## Features

- **Interactive Force-Directed Layout** - Nodes repel and attract based on relationships
- **Color-Coded Entity Types** - Visual distinction between different entity types
- **Hover Tooltips** - Detailed information on hover
- **Zoom & Pan** - Explore large graphs easily
- **Node Size by Importance** - More connected nodes appear larger
- **Edge Thickness by Weight** - Stronger relationships shown with thicker edges
- **Filtering Options** - Filter by entity type, connections, or node limit
- **Search Highlighting** - Highlight specific entities in gold

## Installation

```bash
# Install visualization dependencies
pip install pyvis networkx

# pyvis is the only new dependency needed
```

## Quick Start

### Command Line Interface

```bash
# Interactive CLI with menu
python -m lizzy.graph_visualizer

# Or via bucket analyzer (option 5)
python -m lizzy.bucket_analyzer
```

### Programmatic Usage

```python
from pathlib import Path
from lizzy.graph_visualizer import GraphVisualizer

# Initialize visualizer for a bucket
bucket_path = Path('rag_buckets/books')
visualizer = GraphVisualizer(bucket_path)

# Create basic visualization
visualizer.create_visualization(
    output_path='my_graph.html',
    physics_enabled=True
)
```

## Advanced Usage

### Limit Nodes for Performance

For large graphs (>1000 nodes), limit to most connected entities:

```python
visualizer.create_visualization(
    output_path='top_nodes.html',
    max_nodes=200,  # Show only top 200 most connected
    min_connections=2  # Filter nodes with <2 connections
)
```

### Filter by Entity Type

Focus on specific types of entities:

```python
visualizer.create_visualization(
    output_path='characters_only.html',
    entity_types=['character', 'person'],  # Only show these types
)
```

### Highlight Specific Entities

Draw attention to particular entities:

```python
visualizer.create_visualization(
    output_path='highlighted.html',
    highlight_entities=['hero', 'protagonist', 'love interest']
)
```

### Custom Appearance

```python
visualizer.create_visualization(
    output_path='custom.html',
    width='1920px',  # Full HD width
    height='1080px',  # Full HD height
    physics_enabled=False  # Static layout (faster)
)
```

## Understanding the Visualization

### Node Colors

The visualizer uses distinct colors for different entity types:

- **Red** (#FF6B6B) - Person
- **Teal** (#4ECDC4) - Organization
- **Blue** (#45B7D1) - Location
- **Light Salmon** (#FFA07A) - Concept
- **Mint** (#98D8C8) - Event
- **Yellow** (#F7DC6F) - Technique
- **Purple** (#BB8FCE) - Theme
- **Pink** (#FF6B9D) - Character
- **Gray** (#95A5A6) - Default/Unknown
- **Gold** (#FFD700) - Highlighted

### Node Size

Node size indicates importance (number of connections):
- Larger nodes = more connected entities
- Size range: 10-50 pixels
- Formula: `size = min(10 + (connections * 2), 50)`

### Edge Thickness

Edge thickness represents relationship strength:
- Thicker edges = stronger relationships
- Thickness based on LightRAG's relationship weight
- Range: 0.5-5 pixels

### Tooltips

Hover over any node to see:
- Entity name
- Entity type
- Number of connections
- Description (first 200 chars)

Hover over edges to see:
- Relationship weight
- Relationship description
- Keywords

## Interactive Controls

### Mouse Controls

- **Left Click + Drag** - Move individual nodes
- **Scroll** - Zoom in/out
- **Right Click + Drag** - Pan the canvas

### Keyboard Shortcuts

- **Arrow Keys** - Pan the canvas
- **+/-** - Zoom in/out
- **Spacebar** - Reset camera position

### Navigation Buttons

Built-in navigation buttons appear in the bottom-right:
- **↑↓←→** - Pan controls
- **+/-** - Zoom controls
- **⊙** - Fit to screen

## Performance Tips

### For Large Graphs (>1000 nodes)

1. **Limit nodes**: Use `max_nodes` parameter
   ```python
   max_nodes=300  # Show top 300 most connected
   ```

2. **Filter by connections**: Remove isolated nodes
   ```python
   min_connections=3  # Only nodes with 3+ connections
   ```

3. **Filter by type**: Focus on relevant entity types
   ```python
   entity_types=['character', 'theme']
   ```

4. **Disable physics**: For very large graphs
   ```python
   physics_enabled=False
   ```

### Recommended Settings by Size

| Graph Size | max_nodes | min_connections | physics_enabled |
|------------|-----------|-----------------|-----------------|
| <500       | None      | 0               | True            |
| 500-2000   | 300       | 2               | True            |
| 2000-5000  | 200       | 3               | True            |
| >5000      | 150       | 5               | False           |

## Use Cases

### 1. Explore Thematic Connections

Visualize how themes connect in your source material:

```python
visualizer.create_visualization(
    output_path='themes.html',
    entity_types=['theme', 'concept'],
    min_connections=2
)
```

### 2. Character Relationship Mapping

See character connections in scripts:

```python
visualizer.create_visualization(
    output_path='characters.html',
    entity_types=['character', 'person'],
    highlight_entities=['protagonist', 'antagonist']
)
```

### 3. Identify Central Concepts

Find the most important concepts in your knowledge base:

```python
# Get statistics first
stats = visualizer.get_entity_statistics()
top_10 = [entity for entity, count in stats['most_connected'][:10]]

# Visualize with highlights
visualizer.create_visualization(
    output_path='central_concepts.html',
    highlight_entities=top_10,
    max_nodes=100
)
```

### 4. Compare Buckets

Create visualizations for each bucket to compare knowledge structures:

```python
from pathlib import Path

for bucket_name in ['books', 'plays', 'scripts']:
    bucket_path = Path(f'rag_buckets/{bucket_name}')
    visualizer = GraphVisualizer(bucket_path)

    visualizer.create_visualization(
        output_path=f'{bucket_name}_graph.html',
        max_nodes=200,
        min_connections=2
    )
```

## Troubleshooting

### Graph is too crowded

**Solution**: Increase filtering thresholds
```python
max_nodes=100,
min_connections=5
```

### Nodes are too small

**Solution**: The size is auto-calculated based on connections. If all nodes are similar size, your graph has uniform connectivity. This is normal.

### Physics simulation is slow

**Solution**: Disable physics for large graphs
```python
physics_enabled=False
```

### Missing entity types in colors

**Solution**: Add custom colors to `type_colors` in `graph_visualizer.py`:
```python
self.type_colors = {
    'your_custom_type': '#HEX_COLOR',
    ...
}
```

### Can't see edge labels

**Solution**: Edge labels are shown in tooltips (hover over edges). For static labels, edges would become too cluttered.

## Examples Gallery

### Example 1: Full Books Bucket (Filtered)

```bash
python -m lizzy.graph_visualizer
# Select books bucket
# max_nodes: 200
# min_connections: 2
```

Result: Clean visualization of key screenwriting concepts and their relationships.

### Example 2: Character Network

```python
from lizzy.graph_visualizer import GraphVisualizer
from pathlib import Path

visualizer = GraphVisualizer(Path('rag_buckets/scripts'))
visualizer.create_visualization(
    output_path='character_network.html',
    entity_types=['character', 'person'],
    min_connections=1,
    height='1200px'
)
```

Result: Character relationship web from your script corpus.

### Example 3: Thematic Analysis

```python
visualizer = GraphVisualizer(Path('rag_buckets/books'))

# Get theme-related entities
stats = visualizer.get_entity_statistics()
theme_related = [
    ent for ent, _ in stats['most_connected']
    if 'theme' in ent.lower() or 'story' in ent.lower()
]

visualizer.create_visualization(
    output_path='themes.html',
    highlight_entities=theme_related[:20],
    max_nodes=150
)
```

Result: Thematic structure highlighted in gold.

## Integration with Brainstorming

You can use visualizations to inform your brainstorming sessions:

1. **Visualize** your bucket before brainstorming
2. **Identify** central concepts and themes
3. **Use** those insights to guide your queries

```python
# 1. Visualize and explore
visualizer = GraphVisualizer(Path('rag_buckets/books'))
stats = visualizer.get_entity_statistics()

# 2. Get top themes
top_themes = [e for e, _ in stats['most_connected'][:5]]
print(f"Focus on these themes: {', '.join(top_themes)}")

# 3. Use in brainstorm query
# e.g., "How do I incorporate {theme} into my romantic comedy?"
```

## Technical Details

### Graph Format

Reads from LightRAG's GraphML output:
- **Nodes**: Entities with properties (id, type, description)
- **Edges**: Relationships with weights and descriptions
- **Namespace**: Uses GraphML standard xmlns

### Physics Engine

Uses vis.js force-directed algorithm (forceAtlas2Based):
- **Gravitational constant**: -50 (nodes repel)
- **Spring length**: 200 (preferred distance)
- **Spring constant**: 0.08 (edge stiffness)
- **Damping**: 0.4 (motion smoothing)

### Output Format

Generates standalone HTML file with:
- Embedded vis.js library
- JSON graph data
- JavaScript for interactivity
- CSS styling

No external dependencies needed to view the visualization.

## API Reference

### GraphVisualizer

```python
class GraphVisualizer:
    def __init__(self, bucket_path: Path)

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
    ) -> str

    def get_entity_statistics(self) -> Dict
```

### Parameters

- **output_path**: Output HTML filename
- **max_nodes**: Limit to N most connected nodes
- **entity_types**: List of types to include (e.g., ['person', 'theme'])
- **min_connections**: Filter nodes with fewer connections
- **highlight_entities**: List of entity IDs to highlight in gold
- **width**: Canvas width (CSS format)
- **height**: Canvas height (CSS format)
- **physics_enabled**: Enable force-directed layout

### Returns

- **create_visualization()**: Absolute path to generated HTML file
- **get_entity_statistics()**: Dict with graph statistics

## Future Enhancements

Potential additions for future versions:

- [ ] Cluster detection and coloring
- [ ] Time-based filtering (if temporal data available)
- [ ] Export to Neo4j database format
- [ ] Subgraph extraction around selected nodes
- [ ] Path finding between entities
- [ ] Community detection visualization
- [ ] 3D graph rendering option
- [ ] Real-time collaboration features
- [ ] Custom node shapes by entity type

## Contributing

Found a bug or have a feature request? Please open an issue!

Want to add custom visualizations? The code is modular and easy to extend.

---

**Pro Tip**: Create visualizations for all your buckets, then compare them side-by-side in separate browser tabs to see how different source materials structure knowledge differently!
