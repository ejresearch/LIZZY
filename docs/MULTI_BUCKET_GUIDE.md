# Multi-Bucket Knowledge Graph Explorer

**Query and visualize ALL your RAG buckets together!**

## What This Does

Instead of visualizing one bucket at a time, you can:

1. **Combine all buckets** into one unified graph
2. **Search across** books, plays, AND scripts simultaneously  
3. **Find cross-bucket entities** (concepts that appear everywhere)
4. **Color-code by source** to see which bucket each concept comes from
5. **Explore connections** between different source materials

## Quick Start

```bash
# Interactive CLI
python -m lizzy.multi_bucket_explorer
```

Then:
1. Select which buckets to combine (or type "all")
2. Choose what you want to do (search, stats, visualize)
3. Explore!

## Main Features

### 1. Combined Statistics

See totals across all buckets:
- How many entities in each bucket
- How many appear in multiple buckets
- Entity type distribution

### 2. Cross-Bucket Search

Search for concepts across ALL your sources:

```python
from pathlib import Path
from lizzy.multi_bucket_explorer import MultiBucketExplorer

# Load all buckets
buckets = [
    Path('rag_buckets/books'),
    Path('rag_buckets/plays'),
    Path('rag_buckets/scripts')
]

explorer = MultiBucketExplorer(buckets)

# Search for "character" across all buckets
results = explorer.search_across_buckets('character')

# See where it appears
for result in results[:10]:
    print(f"{result['entity_id']} - from {result['source_bucket']}")
    if result['cross_bucket']:
        print(f"  ⭐ Also in: {result['appears_in']}")
```

### 3. Find Cross-Bucket Entities

Discover concepts that appear in multiple sources:

```python
# Find entities in at least 2 buckets
cross_bucket = explorer.find_cross_bucket_entities(min_buckets=2)

# Top results:
# - "Protagonist" (in books, plays, scripts)
# - "Character Arc" (in books, scripts)
# - "Conflict" (in books, plays)
```

### 4. Combined Visualization

Create ONE graph showing all buckets together:

```python
explorer.create_combined_visualization(
    output_path='all_together.html',
    max_nodes_per_bucket=75,  # Top 75 from each = 225 total
    highlight_cross_bucket=True,  # Gold = multiple buckets
    color_by='bucket'  # Color by source
)
```

**Color Scheme:**
- 🔴 **Red** = From books bucket
- 🔵 **Teal** = From plays bucket  
- 🟡 **Yellow** = From scripts bucket
- 🪙 **Gold** = Appears in multiple buckets!

## Use Cases

### 1. Find Universal Concepts

**Question:** What storytelling concepts appear everywhere?

**Action:**
```python
cross_bucket = explorer.find_cross_bucket_entities(min_buckets=3)
# Returns concepts in ALL three buckets
```

**Result:** "Protagonist", "Conflict", "Character Arc" - the fundamentals!

### 2. Compare Source Types

**Question:** How do books explain concepts vs. scripts showing them?

**Action:**
```python
# Search for "hero's journey" across all buckets
results = explorer.search_across_buckets("hero's journey")

# See descriptions from each source
for r in results:
    print(f"{r['source_bucket']}: {r['description'][:100]}...")
```

### 3. Build Cross-Reference Network

**Question:** How do concepts from different sources connect?

**Action:**
```python
explorer.create_combined_visualization(
    output_path='cross_reference.html',
    color_by='type',  # Color by entity type instead
    max_nodes_per_bucket=100
)
```

**Result:** See how "Character Arc" (from books) connects to "Hamlet" (from plays) and "Little Miss Sunshine" (from scripts)

### 4. Find Unique Content

**Question:** What concepts ONLY appear in scripts, not books or plays?

**Action:**
```python
# Get all script entities
results = explorer.search_across_buckets('', buckets=['scripts'])

# Filter to non-cross-bucket only
unique_to_scripts = [r for r in results if not r['cross_bucket']]
```

## Example Session

```bash
$ python -m lizzy.multi_bucket_explorer

┌─────────────────────────────────────────┐
│ Multi-Bucket Knowledge Graph Explorer  │
│                                         │
│ Combine and explore multiple RAG       │
│ buckets simultaneously                  │
└─────────────────────────────────────────┘

Available Buckets:
  [1] books
  [2] plays
  [3] scripts

Select buckets to combine: all

Selected: books, plays, scripts

What would you like to do?
[1] View combined statistics
[2] Search across all buckets
[3] Find cross-bucket entities
[4] Create combined visualization
[5] Exit

Choose an option: 3

Found 863 entities appearing in multiple buckets:

#  Entity       Buckets                Count
1  Richard      books, plays, scripts  3
2  Protagonist  books, plays, scripts  3
3  Money        books, plays, scripts  3
4  Conflict     books, scripts         2
5  Theme        plays, scripts         2
...

What would you like to do?
[1] View combined statistics
[2] Search across all buckets
[3] Find cross-bucket entities
[4] Create combined visualization
[5] Exit

Choose an option: 4

Color by:
[1] Source bucket (red=books, teal=plays, gold=scripts)
[2] Entity type (red=person, orange=concept, etc.)

Choose: 1

Limit nodes per bucket? (Y/n): y
Max nodes per bucket (100): 75

Highlight cross-bucket entities in gold? (Y/n): y

Output filename (combined_graph.html): 

Creating combined visualization with 225 nodes and 530 edges...
  Adding nodes... ━━━━━━━━━━━━━━━━ 100%
  Adding edges... ━━━━━━━━━━━━━━━━ 100%

✓ Visualization saved to: combined_graph.html

Open in browser? (Y/n): y
```

Browser opens with interactive graph showing:
- Red cluster = concepts from screenwriting books
- Teal cluster = dramatic structure from plays
- Yellow cluster = practical examples from scripts
- Gold nodes = universal concepts connecting all three!

## API Reference

```python
class MultiBucketExplorer:
    def __init__(self, bucket_paths: List[Path])
    
    def search_across_buckets(
        query: str,
        entity_types: Optional[List[str]] = None,
        buckets: Optional[List[str]] = None
    ) -> List[Dict]
    
    def find_cross_bucket_entities(
        min_buckets: int = 2
    ) -> List[Dict]
    
    def get_statistics() -> Dict
    
    def create_combined_visualization(
        output_path: str = "combined_knowledge_graph.html",
        max_nodes_per_bucket: Optional[int] = None,
        entity_types: Optional[List[str]] = None,
        highlight_cross_bucket: bool = True,
        color_by: str = "bucket",  # or "type"
        width: str = "100%",
        height: str = "900px"
    ) -> str
```

## Statistics Example

When you load all buckets, you get:

```python
stats = explorer.get_statistics()

# Returns:
{
    'total_entities': 17514,
    'total_relationships': 19504,
    'bucket_stats': {
        'books': {'entities': 5927, 'relationships': 6032},
        'plays': {'entities': 4253, 'relationships': 5685},
        'scripts': {'entities': 7334, 'relationships': 7787}
    },
    'cross_bucket_entities': 863,  # Appear in 2+ buckets
    'unique_base_entities': 16651  # Deduplicated count
}
```

**Insight:** 863 concepts (5%) appear in multiple buckets - these are your **core storytelling fundamentals**!

## Tips

### For Best Visualization

```python
# Recommended settings for 3 buckets:
explorer.create_combined_visualization(
    max_nodes_per_bucket=75,  # 225 total nodes
    highlight_cross_bucket=True,
    color_by='bucket'
)
```

### For Deep Analysis

```python
# Show all cross-bucket entities
cross = explorer.find_cross_bucket_entities(min_buckets=2)

# Export to file for analysis
import json
with open('cross_bucket_analysis.json', 'w') as f:
    json.dump(cross, f, indent=2)
```

### For Focused Search

```python
# Only search in specific buckets
results = explorer.search_across_buckets(
    'character development',
    buckets=['books'],  # Only books
    entity_types=['concept', 'technique']  # Only these types
)
```

## What You'll Discover

Running this on the LIZZY_ROMCOM buckets revealed:

1. **863 cross-bucket entities** (concepts appearing everywhere)
2. **"Protagonist"** appears in all 3 buckets with different descriptions
3. **Books focus on structure**, plays on dialogue, scripts on practical examples
4. **Universal concepts cluster** in the center of combined graphs
5. **Source-specific concepts** form separate clusters

## Comparison to Single-Bucket

| Feature | Single Bucket | Multi-Bucket |
|---------|---------------|--------------|
| Scope | One source | All sources |
| Search | Within one bucket | Across all buckets |
| Insights | Source-specific | Cross-cutting patterns |
| Visualization | One color scheme | Color by source |
| Use case | Deep dive | Big picture |

Use **single-bucket** for: Detailed exploration of one source type

Use **multi-bucket** for: Finding universal patterns and cross-references

## Next Steps

1. Run `python -m lizzy.multi_bucket_explorer`
2. Choose "all" buckets
3. Select option 4 (create visualization)
4. Open the HTML file
5. Look for **gold nodes** - these are your universal concepts!

---

**Pro Tip:** Create both a "color by bucket" and "color by type" visualization, then open them side-by-side in browser tabs to see different patterns!
