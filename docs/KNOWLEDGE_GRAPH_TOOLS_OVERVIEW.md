# Complete Knowledge Graph & Vector Search Tools Overview

**All the ways you can search and explore your RAG buckets**

---

## 🗺️ The Complete Toolkit

You have **5 different tools** for working with your knowledge graphs:

### 1. **LightRAG Core** (Built-in)
### 2. **Bucket Manager** (CLI)
### 3. **Bucket Analyzer** (Text Exploration)
### 4. **Graph Visualizer** (Single Bucket)
### 5. **Multi-Bucket Explorer** (Cross-Bucket Search)

---

## 1. LightRAG Core - The Foundation

**File:** Built into LightRAG library
**What it does:** The underlying RAG system that powers everything

### How It Works

When you add documents to a bucket:

```python
# In manage_buckets.py
rag = LightRAG(
    working_dir=str(bucket_path),
    llm_model_name="gpt-4o-mini"
)

# Add documents
rag.insert(document_text)
```

**LightRAG creates:**
1. **Vector embeddings** - Semantic search via text-embedding-ada-002
2. **Knowledge graph** - Entities and relationships extracted by GPT-4o-mini
3. **GraphML file** - `graph_chunk_entity_relation.graphml`
4. **JSON stores** - Entities, relationships, documents

### Query Modes

LightRAG has 4 built-in search modes:

```python
# 1. Naive - Simple vector search
result = rag.query("character development", mode="naive")

# 2. Local - Entity-focused search
result = rag.query("protagonist arc", mode="local")

# 3. Global - Community-level search
result = rag.query("story themes", mode="global")

# 4. Hybrid - Combines all modes
result = rag.query("scene structure", mode="hybrid")
```

**Used by:** Automated & Interactive Brainstorm modules

---

## 2. Bucket Manager - RAG CRUD Operations

**File:** `manage_buckets.py`
**Interface:** Interactive CLI
**What it does:** Create, query, manage RAG buckets

### Features

```bash
python3 manage_buckets.py
```

**Menu:**
1. **Create bucket** - Initialize new RAG bucket
2. **Add documents** - Ingest PDFs/text files
3. **Query bucket** - Test RAG retrieval (4 modes)
4. **List buckets** - See what exists
5. **Delete bucket** - Remove bucket

### When You Use It

- **One-time setup** - Create your knowledge bases
- **Add new material** - Expand existing buckets
- **Test retrieval** - Verify RAG is working

### Under the Hood

```python
# Creating a bucket
bucket_path = Path(f"rag_buckets/{bucket_name}")
bucket_path.mkdir(parents=True, exist_ok=True)

# Adding documents
for file_path in document_files:
    with open(file_path) as f:
        content = f.read()
    rag.insert(content)  # LightRAG indexes it

# Querying
result = rag.query(
    "your query",
    mode="hybrid",  # or naive/local/global
    only_need_context=False
)
```

**Output:** Natural language answers powered by vector + graph search

---

## 3. Bucket Analyzer - Text-Based Exploration

**File:** `lizzy/bucket_analyzer.py`
**Interface:** Interactive CLI
**What it does:** Explore the knowledge graph without visualization

### Features

```bash
python -m lizzy.bucket_analyzer
```

**Menu:**
1. **View statistics** - Entity counts, types, relationships
2. **View top entities** - Most connected concepts
3. **Search entities** - Find by keyword
4. **View entity details** - Deep dive on one entity
5. **Create visualization** - Launch graph visualizer

### When You Use It

- **Quick stats** - How many entities in each bucket?
- **Find entities** - "What concepts mention 'dialogue'?"
- **Explore connections** - What connects to "protagonist"?
- **Launch visualizer** - Jump to visual exploration

### What You See

```bash
Bucket Statistics:
  Entities: 5,927
  Relationships: 6,032
  Avg Connections: 2.0

Entity Type Distribution:
  concept: 1,842
  person: 1,245
  technique: 893

Top 10 Most Connected:
  1. Story Structure (142 connections)
  2. Character Arc (98 connections)
  3. Three Act Structure (87 connections)
```

### Under the Hood

Parses the GraphML file LightRAG created:

```python
# Load entities
tree = ET.parse('graph_chunk_entity_relation.graphml')
for node in tree.findall('.//node'):
    entity_id = node.get('id')
    entity_type = node.find('data[@key="d1"]').text
    description = node.find('data[@key="d2"]').text

# Count connections
for edge in tree.findall('.//edge'):
    source = edge.get('source')
    target = edge.get('target')
    connection_counts[source] += 1
    connection_counts[target] += 1
```

**Output:** Text tables and summaries

---

## 4. Graph Visualizer - Single Bucket Visualization

**File:** `lizzy/graph_visualizer.py`
**Interface:** CLI → HTML output
**What it does:** Create Neo4j-style interactive graph of ONE bucket

### Features

```bash
python -m lizzy.graph_visualizer
```

**Then:**
1. Choose a bucket (books, plays, or scripts)
2. Configure filters (max nodes, min connections, entity types)
3. Get interactive HTML visualization

### When You Use It

- **Explore one source** - Deep dive into books, plays, OR scripts
- **See structure** - Visual understanding of knowledge organization
- **Find clusters** - Related concepts group together
- **Identify hubs** - Central concepts are biggest nodes

### What You See

**Interactive graph in browser:**
- **Nodes** (circles) = Entities
- **Edges** (lines) = Relationships
- **Colors** = Entity types (red=person, orange=concept, etc.)
- **Size** = Importance (connection count)
- **Hover** = Details tooltip

**You can:**
- Drag nodes around
- Zoom in/out
- Pan with mouse
- Click to highlight
- Search for specific entities

### Under the Hood

```python
from pyvis.network import Network

# Create network
net = Network(height='900px', width='100%', bgcolor='#1a1a1a')

# Add nodes
for entity_id, data in entities.items():
    color = type_colors[data['entity_type']]
    size = connection_count * 2
    net.add_node(entity_id, color=color, size=size)

# Add edges
for relationship in relationships:
    net.add_edge(relationship['source'], relationship['target'])

# Save HTML
net.save_graph('output.html')
```

**Output:** Standalone HTML file with embedded JavaScript (vis.js)

### Example Use

```python
from pathlib import Path
from lizzy.graph_visualizer import GraphVisualizer

viz = GraphVisualizer(Path('rag_buckets/books'))
viz.create_visualization(
    output_path='books_graph.html',
    max_nodes=200,
    min_connections=2
)
```

---

## 5. Multi-Bucket Explorer - Cross-Bucket Search

**File:** `lizzy/multi_bucket_explorer.py`
**Interface:** CLI → HTML output
**What it does:** Combine and search across ALL buckets simultaneously

### Features

```bash
python -m lizzy.multi_bucket_explorer
# or
python explore_all_buckets.py
```

**Menu:**
1. **Combined statistics** - Totals across all buckets
2. **Search across buckets** - Query books + plays + scripts
3. **Find cross-bucket entities** - Concepts appearing everywhere
4. **Create combined visualization** - Unified graph view

### When You Use It

- **Find universal concepts** - What appears in all sources?
- **Cross-reference** - How do different sources connect?
- **Compare sources** - Books vs plays vs scripts
- **Big picture view** - See entire knowledge base at once

### What You See

**Statistics:**
```
Total entities: 17,514
  books: 5,927
  plays: 4,253
  scripts: 7,334

Cross-bucket entities: 863 (5%)
```

**Search results:**
```
Found 868 matches for "character":
  ⭐ Character Arc (books, scripts) - CROSS-BUCKET
     Protagonist (books, plays, scripts) - CROSS-BUCKET
     Character Development (books)
```

**Visualization:**
- 🔴 **Red nodes** = Books
- 🔵 **Teal nodes** = Plays
- 🟡 **Yellow nodes** = Scripts
- 🪙 **Gold nodes** = Cross-bucket entities!

### Under the Hood

```python
class MultiBucketExplorer:
    def __init__(self, bucket_paths: List[Path]):
        # Load all buckets
        for bucket in bucket_paths:
            # Parse each GraphML
            # Track which buckets each entity appears in

    def search_across_buckets(self, query: str):
        # Search in all loaded buckets
        # Mark entities appearing in multiple buckets

    def find_cross_bucket_entities(self):
        # Return entities in 2+ buckets
        # These are universal concepts!

    def create_combined_visualization(self):
        # Merge all graphs
        # Color by source bucket
        # Highlight cross-bucket in gold
```

### Example Use

```python
from pathlib import Path
from lizzy.multi_bucket_explorer import MultiBucketExplorer

explorer = MultiBucketExplorer([
    Path('rag_buckets/books'),
    Path('rag_buckets/plays'),
    Path('rag_buckets/scripts')
])

# Search across all
results = explorer.search_across_buckets('dialogue')

# Find universal concepts
cross_bucket = explorer.find_cross_bucket_entities(min_buckets=3)
# Returns: Protagonist, Conflict, Character Arc...

# Visualize everything
explorer.create_combined_visualization(
    output_path='all_buckets.html',
    highlight_cross_bucket=True
)
```

---

## 📊 Comparison Matrix

| Feature | LightRAG | Manager | Analyzer | Visualizer | Multi-Explorer |
|---------|----------|---------|----------|------------|----------------|
| **Purpose** | RAG engine | CRUD ops | Text exploration | Visual single | Visual multi |
| **Interface** | API | CLI | CLI | CLI → HTML | CLI → HTML |
| **Output** | Text answers | Text results | Text tables | Interactive graph | Interactive graph |
| **Buckets** | One at a time | One at a time | One at a time | One at a time | All together |
| **Search** | Vector + graph | Yes | Keyword | Visual | Keyword + visual |
| **Cross-bucket** | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Visualization** | ❌ | ❌ | ❌ | ✅ | ✅ |
| **Used by** | Brainstorm | You | You | You | You |
| **Files** | LightRAG lib | manage_buckets.py | bucket_analyzer.py | graph_visualizer.py | multi_bucket_explorer.py |

---

## 🔄 How They Work Together

### The Data Flow

```
1. INGEST (Bucket Manager)
   └─> Add PDFs/text to bucket
       └─> LightRAG creates:
           ├─> Vector embeddings
           ├─> Knowledge graph (GraphML)
           ├─> Entity/relationship JSON
           └─> Document chunks

2. QUERY (Brainstorm Modules)
   └─> LightRAG vector search
       └─> Returns relevant context
           └─> Used in prompts

3. EXPLORE (Bucket Analyzer)
   └─> Parse GraphML
       └─> Show statistics
           └─> Search entities

4. VISUALIZE (Graph Visualizer)
   └─> Parse GraphML
       └─> Create interactive graph
           └─> Open in browser

5. COMPARE (Multi-Bucket Explorer)
   └─> Parse ALL GraphML files
       └─> Merge graphs
           └─> Find cross-bucket patterns
               └─> Create unified visualization
```

### Usage Patterns

**Setup Phase (Once):**
```bash
# 1. Create buckets
python3 manage_buckets.py
# Choose: Create bucket

# 2. Add documents
python3 manage_buckets.py
# Choose: Add documents

# 3. Test queries
python3 manage_buckets.py
# Choose: Query bucket
```

**Exploration Phase (Anytime):**
```bash
# Quick stats
python -m lizzy.bucket_analyzer

# Visual exploration
python -m lizzy.graph_visualizer

# Cross-bucket analysis
python -m lizzy.multi_bucket_explorer
```

**Writing Phase (Daily):**
```bash
# Use LightRAG via brainstorm modules
python3 -m lizzy.automated_brainstorm
# or
python3 -m lizzy.interactive_brainstorm
```

---

## 🎯 When to Use Each Tool

### Use **Bucket Manager** when:
- ✅ Setting up new RAG buckets
- ✅ Adding new source documents
- ✅ Testing if RAG retrieval works
- ✅ Quick natural language queries

### Use **Bucket Analyzer** when:
- ✅ Need quick statistics
- ✅ Want to search entity names
- ✅ Exploring what's in a bucket
- ✅ Don't need visualization

### Use **Graph Visualizer** when:
- ✅ Deep diving into ONE source type
- ✅ Want to see knowledge structure
- ✅ Need to identify central concepts
- ✅ Finding related concept clusters

### Use **Multi-Bucket Explorer** when:
- ✅ Finding universal concepts
- ✅ Comparing different sources
- ✅ Searching across all knowledge
- ✅ Creating comprehensive views
- ✅ Identifying cross-cutting patterns

### Use **LightRAG Core** (automatically) when:
- ✅ Running brainstorm modules
- ✅ Need RAG-augmented responses
- ✅ Building AI writing pipelines

---

## 🔍 Search Capabilities Breakdown

### 1. Vector Search (LightRAG)

**What:** Semantic similarity search in embedding space
**How:** text-embedding-ada-002 converts text to vectors, cosine similarity finds matches
**Best for:** "Find concepts similar to..."

```python
# Finds semantically similar content
result = rag.query("character development techniques", mode="naive")
```

### 2. Graph Search (LightRAG)

**What:** Entity and relationship traversal
**How:** Finds entities, walks graph to related concepts
**Best for:** "What connects to X?"

```python
# Finds related entities via graph
result = rag.query("protagonist", mode="local")
```

### 3. Keyword Search (Analyzer)

**What:** String matching in entity names/descriptions
**How:** Python string operations on GraphML data
**Best for:** "Find exact entity names"

```python
# Finds entities containing "dialogue"
results = analyzer.search_entities("dialogue")
```

### 4. Cross-Bucket Search (Multi-Explorer)

**What:** Query across multiple buckets simultaneously
**How:** Loads all GraphML files, searches each, aggregates results
**Best for:** "Where does this appear?"

```python
# Searches books + plays + scripts
results = explorer.search_across_buckets("three act structure")
```

### 5. Visual Search (Visualizers)

**What:** Interactive exploration by clicking/hovering
**How:** HTML graph with JavaScript interactivity
**Best for:** "What's near this concept?"

```
Click node → See connections
Hover → Read description
Zoom → Explore clusters
```

---

## 📁 File Structure

```
LIZZY_ROMCOM/
├── manage_buckets.py              # Bucket Manager CLI
├── explore_all_buckets.py         # Multi-explorer launcher
│
├── lizzy/
│   ├── bucket_analyzer.py         # Text exploration
│   ├── graph_visualizer.py        # Single bucket viz
│   ├── multi_bucket_explorer.py   # Multi-bucket viz
│   ├── automated_brainstorm.py    # Uses LightRAG
│   └── interactive_brainstorm.py  # Uses LightRAG
│
├── rag_buckets/                   # Data created by LightRAG
│   ├── books/
│   │   ├── graph_chunk_entity_relation.graphml  # The graph!
│   │   ├── kv_store_full_entities.json
│   │   ├── kv_store_full_relations.json
│   │   ├── vdb_entities.json       # Vector embeddings
│   │   └── vdb_relationships.json
│   ├── plays/
│   │   └── [same structure]
│   └── scripts/
│       └── [same structure]
│
└── docs/
    ├── KNOWLEDGE_GRAPH_TOOLS_OVERVIEW.md  # This file
    ├── VISUALIZATION_GUIDE.md
    ├── MULTI_BUCKET_GUIDE.md
    └── HOW_IT_WORKS_SIMPLE.md
```

---

## 🧠 Technical Deep Dive

### LightRAG's Hybrid Approach

LightRAG combines **3 search methods**:

**1. Vector Search (Naive Mode)**
```python
# Embeds query → Find similar document chunks
query_embedding = embed(query)
similar_chunks = cosine_similarity(query_embedding, all_chunk_embeddings)
```

**2. Entity Search (Local Mode)**
```python
# Extract entities from query → Find in graph → Get connected entities
query_entities = extract_entities(query)
related_entities = graph.neighbors(query_entities)
context = get_entity_descriptions(related_entities)
```

**3. Community Search (Global Mode)**
```python
# Find high-level communities in graph → Match to query
communities = detect_communities(graph)
relevant_communities = rank_by_query(communities, query)
context = summarize_communities(relevant_communities)
```

**4. Hybrid Mode**
```
Combines all three approaches for comprehensive results
```

### Why Multiple Tools?

**Different use cases:**
- **Writing** → LightRAG (automatic, integrated)
- **Setup** → Bucket Manager (CRUD operations)
- **Quick check** → Bucket Analyzer (fast stats)
- **Understanding** → Graph Visualizer (see structure)
- **Discovery** → Multi-Bucket Explorer (find patterns)

**Different interfaces:**
- CLI for automation/scripting
- Interactive menus for exploration
- HTML visualizations for understanding
- APIs for integration

**Different scopes:**
- Single bucket (deep dive)
- All buckets (big picture)
- Entity-level (details)
- Graph-level (structure)

---

## 💡 Pro Tips

### 1. Start with Multi-Bucket Explorer

See the big picture first:
```bash
python -m lizzy.multi_bucket_explorer
# Choose: Find cross-bucket entities
```

This shows you the **universal concepts** - your foundation.

### 2. Then Dive Into Single Buckets

```bash
python -m lizzy.graph_visualizer
# Select: books
```

Explore each source's unique structure.

### 3. Use Analyzer for Quick Checks

```bash
python -m lizzy.bucket_analyzer
# Search: "dialogue"
```

Fast entity lookup without visualization overhead.

### 4. Test Queries Before Brainstorming

```bash
python3 manage_buckets.py
# Query bucket with different modes
```

Verify you're getting good RAG results.

### 5. Create Multiple Visualizations

```bash
# Color by bucket
explorer.create_combined_visualization(color_by='bucket')

# Color by type
explorer.create_combined_visualization(color_by='type')
```

Open both in browser tabs, compare views!

---

## 🎓 Learning Path

**Day 1: Setup**
1. Create buckets with Bucket Manager
2. Add documents
3. Test queries

**Day 2: Explore**
1. Run Bucket Analyzer - see stats
2. Search for entities
3. Understand what's in each bucket

**Day 3: Visualize**
1. Run Graph Visualizer on each bucket
2. Explore the interactive graphs
3. Identify central concepts

**Day 4: Compare**
1. Run Multi-Bucket Explorer
2. Find cross-bucket entities
3. Create combined visualization

**Day 5: Write**
1. Use brainstorm modules (powered by LightRAG)
2. Reference visualizations for inspiration
3. Create your screenplay!

---

## 📊 Statistics from Your Buckets

**Current status (as tested):**

```
Books Bucket:
  - 5,927 entities
  - 6,032 relationships
  - Top: Story Structure, Character Arc, Three Act Structure

Plays Bucket:
  - 4,253 entities
  - 5,685 relationships
  - Top: Dialogue, Dramatic Structure, Aristotelian Theory

Scripts Bucket:
  - 7,334 entities
  - 7,787 relationships
  - Top: Visual Storytelling, Scene Structure, Character Dynamics

Combined:
  - 17,514 total entities
  - 863 cross-bucket entities (5%)
  - Universal concepts: Protagonist, Conflict, Character Arc, Theme, etc.
```

**Insight:** Only 5% of concepts appear across all sources - these are your **core storytelling fundamentals**!

---

## 🚀 Quick Command Reference

```bash
# Setup
python3 manage_buckets.py         # Create buckets, add docs

# Text exploration
python -m lizzy.bucket_analyzer   # Stats and search

# Single bucket visualization
python -m lizzy.graph_visualizer  # Interactive graph

# Multi-bucket exploration
python -m lizzy.multi_bucket_explorer  # Cross-bucket search
# or
python explore_all_buckets.py     # Shortcut

# Visualization examples
python examples_visualize.py      # 7 example scenarios

# Use in writing (automatic)
python3 -m lizzy.automated_brainstorm  # Uses LightRAG
python3 -m lizzy.interactive_brainstorm  # Uses LightRAG
```

---

## ❓ FAQ

**Q: Which tool do I use most often?**
A: Multi-Bucket Explorer for discovery, then brainstorm modules for writing.

**Q: Do I need to visualize to write?**
A: No! Brainstorm modules use LightRAG automatically. Visualization is for exploration and understanding.

**Q: Can I search while writing?**
A: Yes! Interactive Brainstorm lets you query buckets during your session.

**Q: What's the difference between Bucket Manager queries and Multi-Explorer search?**
A: Manager uses LightRAG's semantic search (vector + graph). Explorer uses keyword matching in entity names. Both useful!

**Q: Which is faster?**
A: Analyzer (text) > Visualizer (single) > Multi-Explorer (all buckets). But speed vs insight tradeoff.

**Q: Can I add more buckets?**
A: Yes! Create new buckets in Bucket Manager, then all tools will see them.

---

## 🎯 Summary

**You have 5 tools working together:**

1. **LightRAG** - The engine (automatic)
2. **Manager** - Setup and testing (CLI)
3. **Analyzer** - Quick exploration (CLI)
4. **Visualizer** - Deep understanding (HTML)
5. **Multi-Explorer** - Pattern discovery (HTML)

**They all read the same data:**
- GraphML files (knowledge graph)
- JSON files (entities/relationships)
- Vector stores (embeddings)

**Created by LightRAG when you ingest documents.**

**Best workflow:**
1. Setup with Manager
2. Explore with Multi-Explorer
3. Understand with Visualizer
4. Search with Analyzer
5. Write with Brainstorm (uses LightRAG)

---

**Now you understand the complete knowledge graph toolkit! 🎉**

Want to try it? Run:
```bash
python -m lizzy.multi_bucket_explorer
```

Choose "Find cross-bucket entities" to see what concepts appear everywhere!
