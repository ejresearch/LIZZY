# Knowledge Graph & Search Tools - Visual Overview

## The Complete System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        YOUR SOURCE DOCUMENTS                        │
│              (PDFs, text files - screenwriting material)            │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────────┐
│                      1. BUCKET MANAGER (CLI)                        │
│                     manage_buckets.py                               │
│                                                                     │
│  • Create buckets                                                   │
│  • Add documents → LightRAG ingestion                               │
│  • Test queries (naive/local/global/hybrid)                        │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────────┐
│                     LIGHTRAG PROCESSING ENGINE                      │
│                                                                     │
│  OpenAI text-embedding-ada-002  ←→  GPT-4o-mini                     │
│         (vectors)                    (entities/relationships)       │
│                                                                     │
│  Creates:                                                           │
│  ├─ Vector embeddings (semantic search)                            │
│  ├─ Knowledge graph (entity relationships)                          │
│  ├─ GraphML file (graph_chunk_entity_relation.graphml)             │
│  └─ JSON stores (entities, relations, docs)                         │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────────┐
│                      RAG BUCKETS (Data Layer)                       │
│                                                                     │
│  rag_buckets/                                                       │
│  ├── books/                                                         │
│  │   ├── graph_chunk_entity_relation.graphml  ← The graph!         │
│  │   ├── kv_store_full_entities.json                               │
│  │   ├── kv_store_full_relations.json                              │
│  │   └── vdb_entities.json  ← Vector embeddings                    │
│  ├── plays/                                                         │
│  │   └── [same structure]                                           │
│  └── scripts/                                                       │
│      └── [same structure]                                           │
└─────────────────────────────────────────────────────────────────────┘
                             │
                             ↓
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ↓                   ↓                   ↓
┌─────────────────┐  ┌──────────────┐  ┌─────────────────┐
│  2. ANALYZER    │  │ 3. VISUALIZER│  │ 4. MULTI-EXPLORER│
│     (Text)      │  │   (Single)   │  │   (Combined)    │
└─────────────────┘  └──────────────┘  └─────────────────┘
         │                   │                   │
         ↓                   ↓                   ↓
┌─────────────────┐  ┌──────────────┐  ┌─────────────────┐
│ bucket_analyzer │  │graph_visualizer│ │multi_bucket_    │
│      .py        │  │      .py      │  │explorer.py      │
│                 │  │               │  │                 │
│ Features:       │  │ Features:     │  │ Features:       │
│ • Stats         │  │ • Interactive │  │ • Cross-search  │
│ • Search        │  │   graph       │  │ • Find universal│
│ • Top entities  │  │ • Force layout│  │   concepts      │
│ • Details       │  │ • Color coded │  │ • Unified graph │
│                 │  │ • Filters     │  │ • Compare       │
│ Output: CLI     │  │ Output: HTML  │  │ Output: HTML    │
└─────────────────┘  └──────────────┘  └─────────────────┘
```

---

## Tool Usage Paths

### Path A: Setup & Testing
```
User
  ↓
manage_buckets.py (create bucket)
  ↓
Add documents
  ↓
LightRAG ingests & processes
  ↓
Test query
  ↓
Get natural language answer
```

### Path B: Text Exploration
```
User
  ↓
bucket_analyzer.py
  ↓
Choose bucket
  ↓
View stats / Search / Explore
  ↓
See text results
```

### Path C: Visual Exploration (Single Bucket)
```
User
  ↓
graph_visualizer.py
  ↓
Choose bucket
  ↓
Set filters
  ↓
Get interactive HTML graph
  ↓
Explore in browser
```

### Path D: Cross-Bucket Analysis
```
User
  ↓
multi_bucket_explorer.py
  ↓
Select all buckets
  ↓
Search / Find cross-bucket / Visualize
  ↓
Get combined results + unified graph
```

### Path E: Writing (Automatic)
```
User writes screenplay
  ↓
automated_brainstorm.py
  ↓
LightRAG queries buckets (hybrid mode)
  ↓
Returns relevant context
  ↓
Used in GPT-4o prompt
  ↓
Blueprint generated
```

---

## Search Method Comparison

```
┌────────────────────────────────────────────────────────────┐
│                    SEARCH METHODS                          │
└────────────────────────────────────────────────────────────┘

1. VECTOR SEARCH (LightRAG - Naive Mode)
   ┌─────────────┐
   │   Query     │ "character development"
   └──────┬──────┘
          ↓
   ┌─────────────┐
   │  Embedding  │ → [0.234, -0.567, 0.891, ...]
   └──────┬──────┘
          ↓
   ┌─────────────┐
   │  Cosine     │ Compare to all document chunks
   │ Similarity  │
   └──────┬──────┘
          ↓
   Relevant chunks


2. GRAPH SEARCH (LightRAG - Local Mode)
   ┌─────────────┐
   │   Query     │ "protagonist"
   └──────┬──────┘
          ↓
   ┌─────────────┐
   │  Extract    │ Entity: "protagonist"
   │  Entities   │
   └──────┬──────┘
          ↓
   ┌─────────────┐
   │   Find in   │ Navigate graph
   │    Graph    │
   └──────┬──────┘
          ↓
   Connected entities: Hero, Arc, Journey...


3. KEYWORD SEARCH (Analyzer)
   ┌─────────────┐
   │   Query     │ "dialogue"
   └──────┬──────┘
          ↓
   ┌─────────────┐
   │  String     │ if "dialogue" in entity_name
   │  Matching   │
   └──────┬──────┘
          ↓
   Matching entities


4. CROSS-BUCKET SEARCH (Multi-Explorer)
   ┌─────────────┐
   │   Query     │ "theme"
   └──────┬──────┘
          ↓
   ┌─────────────┬─────────────┬─────────────┐
   │   Books     │   Plays     │  Scripts    │
   └──────┬──────┴──────┬──────┴──────┬──────┘
          │             │             │
          └─────────────┴─────────────┘
                       ↓
              Aggregated results
              + cross-bucket markers
```

---

## Data Flow Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                    COMPLETE DATA FLOW                        │
└──────────────────────────────────────────────────────────────┘

INGESTION:
  PDF/Text
     ↓
  LightRAG chunking
     ↓
  ┌──────────────┬──────────────┐
  ↓              ↓              ↓
Embed     Extract Entities  Store Docs
  ↓              ↓              ↓
Vectors     Build Graph    Chunks JSON
  ↓              ↓              ↓
vdb_*.json   GraphML     kv_store_*.json


QUERYING (Writing Phase):
  User Query
     ↓
  LightRAG (hybrid mode)
     ↓
  ┌──────────────┬──────────────┐
  ↓              ↓              ↓
Vector      Entity Graph  Community
Search        Search       Search
  ↓              ↓              ↓
  └──────────────┴──────────────┘
              ↓
     Combined Results
              ↓
      Used in Prompt
              ↓
      GPT-4o Response


EXPLORATION (Analysis Phase):
  GraphML File
     ↓
  Parse XML
     ↓
  ┌──────────────┬──────────────┐
  ↓              ↓              ↓
Text Stats    Single Graph  Multi Graph
(Analyzer)   (Visualizer)  (Explorer)
  ↓              ↓              ↓
CLI Output   HTML Graph    HTML Graph
```

---

## Bucket Contents Breakdown

```
rag_buckets/books/
│
├── graph_chunk_entity_relation.graphml  (5.5 MB)
│   └─> XML format
│       └─> Nodes (entities) + Edges (relationships)
│           └─> Used by: Analyzer, Visualizer, Multi-Explorer
│
├── kv_store_full_entities.json  (161 KB)
│   └─> Entity details (type, description)
│       └─> Used by: LightRAG queries
│
├── kv_store_full_relations.json  (402 KB)
│   └─> Relationship details (weight, keywords)
│       └─> Used by: LightRAG queries
│
├── kv_store_full_docs.json  (4.2 MB)
│   └─> Original document chunks
│       └─> Used by: LightRAG retrieval
│
├── vdb_entities.json  (74 MB)
│   └─> Vector embeddings of entities
│       └─> Used by: LightRAG vector search
│
└── vdb_relationships.json  (75 MB)
    └─> Vector embeddings of relationships
        └─> Used by: LightRAG vector search
```

**Total per bucket:** ~160 MB
**Total all buckets:** ~480 MB

---

## Usage Frequency

```
                Most Used ←─────────────→ Least Used

Writing Phase:
  LightRAG (automatic) ━━━━━━━━━━━━━━━━━━━━┓
  Interactive Brainstorm ━━━━━━━━━━━━━━━━┓│
  Automated Brainstorm ━━━━━━━━━━━━━━━┓││
                                       ↓↓↓
                              (uses LightRAG queries)

Exploration Phase:
  Multi-Bucket Explorer ━━━━━━━━━━━━━━━┓
  Graph Visualizer ━━━━━━━━━━━━━━━━━━━━━┓│
  Bucket Analyzer ━━━━━━━━━━━━━━━━━━━━━━┓││
  Bucket Manager (query) ━━━━━━━━━━━━━━━┓│││
                                        ↓↓↓↓
                               (when exploring)

Setup Phase (Once):
  Bucket Manager (create/add) ━━━━━━━━┓
                                       ↓
                            (initial setup only)
```

---

## Tool Selection Flowchart

```
                    START
                      │
                      ↓
         ┌────────────────────────┐
         │  What do you want?     │
         └────────────────────────┘
                      │
         ┌────────────┼────────────┐
         ↓            ↓            ↓
    ┌────────┐  ┌─────────┐  ┌────────┐
    │ Setup  │  │ Explore │  │ Write  │
    └────┬───┘  └────┬────┘  └───┬────┘
         │           │            │
         ↓           ↓            ↓
    ┌────────┐  ┌─────────┐  ┌────────┐
    │ Bucket │  │ Visual? │  │ Brain- │
    │Manager │  └────┬────┘  │ storm  │
    └────────┘       │        └────────┘
                     │             │
            ┌────────┼────────┐    ↓
            ↓        ↓        ↓  (Uses
       ┌────────┐ ┌───┐  ┌───┐  LightRAG
       │Analyzer│ │Viz│  │Multi│ auto)
       └────────┘ └───┘  └───┘
            │       │      │
            ↓       ↓      ↓
        [Text]  [HTML] [HTML+Search]
```

**Decision guide:**

- **Need to add documents?** → Bucket Manager
- **Need quick stats?** → Analyzer
- **Want to see structure?** → Visualizer (single bucket)
- **Want to find patterns?** → Multi-Explorer (all buckets)
- **Writing screenplay?** → Brainstorm (uses LightRAG auto)

---

## Performance Comparison

```
Tool            Load Time    Output Time    File Size
─────────────────────────────────────────────────────
Bucket Manager  1-2 sec      2-5 sec        N/A (text)
Analyzer        2-3 sec      <1 sec         N/A (text)
Visualizer      5-10 sec     3-5 sec        300-500 KB
Multi-Explorer  10-20 sec    5-10 sec       800-1200 KB
LightRAG Query  2-4 sec      varies         N/A (API)

(Times for typical dataset: ~6000 entities per bucket)
```

---

## Integration Points

```
┌─────────────────────────────────────────────────────────┐
│              LIZZY SYSTEM INTEGRATION                   │
└─────────────────────────────────────────────────────────┘

INTAKE → fills database with story structure
  ↓
BRAINSTORM → queries LightRAG buckets
  │           ↓
  │      Uses vector + graph search
  │           ↓
  │      Returns relevant context
  │           ↓
  └────→ Generates blueprint
              ↓
         Saves to database
              ↓
WRITE → uses blueprint + continuity
  ↓
Generates scene prose


Meanwhile, you can:
  - Explore buckets (Analyzer, Visualizer)
  - Find patterns (Multi-Explorer)
  - Test queries (Bucket Manager)
  - Understand structure (All visualization tools)
```

---

## Quick Reference

```bash
# SETUP
python3 manage_buckets.py          # Create/manage buckets

# TEXT EXPLORATION  
python -m lizzy.bucket_analyzer    # Stats, search, entities

# SINGLE BUCKET VISUALIZATION
python -m lizzy.graph_visualizer   # Interactive graph (one bucket)

# MULTI-BUCKET EXPLORATION
python -m lizzy.multi_bucket_explorer  # Cross-search, unified graph
# or
python explore_all_buckets.py      # Shortcut

# EXAMPLES
python examples_visualize.py       # 7 visualization scenarios

# WRITING (uses LightRAG automatically)
python3 -m lizzy.automated_brainstorm
python3 -m lizzy.interactive_brainstorm
```

---

## Summary

**5 tools, one ecosystem:**

1. **Bucket Manager** - Setup and testing
2. **Analyzer** - Quick text exploration
3. **Visualizer** - Single bucket deep dive
4. **Multi-Explorer** - Cross-bucket patterns
5. **LightRAG** - Powers everything (automatic)

**All reading from the same knowledge graphs LightRAG creates.**

**Choose based on your goal: Setup → Explore → Write**
