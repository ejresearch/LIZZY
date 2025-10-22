# Knowledge Graph Visualization - Quick Start

Get beautiful Neo4j-style visualizations of your RAG buckets in 3 steps.

## 1. Install

```bash
pip install pyvis
```

## 2. Run

```bash
# Interactive CLI
python -m lizzy.graph_visualizer

# Or via bucket analyzer
python -m lizzy.bucket_analyzer
# Then choose option 5
```

## 3. Explore

Open the generated `.html` file in your browser to:
- **Drag nodes** to rearrange
- **Zoom** with scroll wheel
- **Hover** for entity details
- **Pan** with arrow keys

## Quick Examples

### Visualize Top 200 Nodes

```python
from pathlib import Path
from lizzy.graph_visualizer import GraphVisualizer

visualizer = GraphVisualizer(Path('rag_buckets/books'))
visualizer.create_visualization(
    output_path='books_graph.html',
    max_nodes=200,
    min_connections=2
)
```

### Filter by Entity Type

```python
# Only show characters and themes
visualizer.create_visualization(
    output_path='characters_themes.html',
    entity_types=['character', 'theme']
)
```

### Highlight Important Entities

```python
# Highlight specific entities in gold
visualizer.create_visualization(
    output_path='highlighted.html',
    highlight_entities=['protagonist', 'hero', 'journey']
)
```

## What You'll See

- **Node colors** = Entity types (red=person, blue=location, etc.)
- **Node size** = Number of connections (bigger=more important)
- **Edge thickness** = Relationship strength
- **Tooltips** = Details on hover

## Performance Tips

| Graph Size | Recommended Settings |
|------------|---------------------|
| <500 nodes | Use defaults |
| 500-2000   | `max_nodes=300, min_connections=2` |
| >2000      | `max_nodes=200, min_connections=3` |

## See Full Guide

For advanced usage, see [VISUALIZATION_GUIDE.md](./VISUALIZATION_GUIDE.md)

---

**That's it!** You now have interactive knowledge graph visualizations like Neo4j, but without running a database server.
