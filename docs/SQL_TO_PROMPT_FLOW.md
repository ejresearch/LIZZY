# SQL to Prompt Data Flow

## Complete Data Injection Pipeline

This document traces how data flows from SQLite tables → Python objects → LLM prompts.

---

## Step 1: Load Project Context from SQL

### On Module Initialization

```python
# In run_batch_processing():
brainstorm = AutomatedBrainstorm(db_path)
brainstorm.load_project_context()  # ← Loads ALL SQL data
```

### SQL Queries Executed

#### Query 1: Project Metadata
```python
self.project = self.db.get_project()
```

**SQL Behind the Scenes:**
```sql
SELECT * FROM projects LIMIT 1
```

**Returns:**
```python
{
    'id': 1,
    'name': 'The Proposal 2.0',
    'genre': 'Romantic Comedy',
    'description': '...',
    'created_at': '2025-01-15 10:30:00'
}
```

---

#### Query 2: Characters
```python
cursor.execute("SELECT name, description, role, arc FROM characters")
self.characters = [dict(row) for row in cursor.fetchall()]
```

**SQL:**
```sql
SELECT name, description, role, arc FROM characters
```

**Returns:**
```python
[
    {
        'name': 'Margaret Tate',
        'description': 'High-powered book editor, Canadian, facing deportation',
        'role': 'Protagonist',
        'arc': 'Ice queen to vulnerable human'
    },
    {
        'name': 'Andrew Paxton',
        'description': 'Margaret\'s assistant, dreams of being a writer',
        'role': 'Love Interest',
        'arc': 'Doormat to equal partner'
    }
]
```

---

#### Query 3: All 30 Scenes
```python
cursor.execute("""
    SELECT id, scene_number, title, description, characters, tone, act
    FROM scenes
    ORDER BY scene_number
""")
self.scenes = [dict(row) for row in cursor.fetchall()]
```

**SQL:**
```sql
SELECT id, scene_number, title, description, characters, tone, act
FROM scenes
ORDER BY scene_number
```

**Returns:**
```python
[
    {
        'id': 1,
        'scene_number': 1,
        'title': 'Opening Image',
        'description': 'Margaret commands her publishing empire...',
        'characters': 'Margaret, office staff',
        'tone': None,
        'act': 'Act 1'
    },
    {
        'id': 2,
        'scene_number': 2,
        'title': 'Status Quo Disrupted',
        'description': 'Margaret learns she\'s being deported...',
        'characters': 'Margaret, HR',
        'tone': None,
        'act': 'Act 1'
    },
    # ... 28 more scenes
]
```

---

#### Query 4: Writer Notes
```python
self.writer_notes = self.db.get_writer_notes()
```

**SQL Behind the Scenes:**
```sql
SELECT * FROM writer_notes LIMIT 1
```

**Returns:**
```python
{
    'id': 1,
    'logline': 'A demanding boss forces her assistant into a fake engagement to avoid deportation',
    'theme': 'True love requires vulnerability and equality',
    'inspiration': 'His Girl Friday meets Green Card',
    'tone': 'Screwball comedy with romantic heart',
    'comps': 'The Proposal (2009), The American President',
    'braindump': '...',
    'created_at': '2025-01-15 10:35:00'
}
```

---

## Step 2: Build Story Outline (SQL → String)

### Method: `build_story_outline()`

**Purpose:** Transforms SQL data into formatted text for prompts

```python
def build_story_outline(self) -> str:
    parts = []

    # Inject project metadata
    if self.project:
        parts.append(f"PROJECT: {self.project['name']}")
        parts.append(f"GENRE: {self.project['genre']}")

    # Inject writer notes
    if self.writer_notes:
        if self.writer_notes.get('logline'):
            parts.append(f"\nLOGLINE: {self.writer_notes['logline']}")
        if self.writer_notes.get('theme'):
            parts.append(f"THEME: {self.writer_notes['theme']}")
        if self.writer_notes.get('tone'):
            parts.append(f"TONE: {self.writer_notes['tone']}")
        if self.writer_notes.get('comps'):
            parts.append(f"COMPS: {self.writer_notes['comps']}")

    # Inject characters
    if self.characters:
        parts.append("\nCHARACTERS:")
        for char in self.characters:
            parts.append(f"  • {char['name']} ({char['role']}): {char['description']}")

    # Inject structure info
    if self.scenes:
        parts.append(f"\nSTRUCTURE: {len(self.scenes)} scenes")

    return "\n".join(parts)
```

**Output Example:**
```
PROJECT: The Proposal 2.0
GENRE: Romantic Comedy

LOGLINE: A demanding boss forces her assistant into a fake engagement to avoid deportation
THEME: True love requires vulnerability and equality
TONE: Screwball comedy with romantic heart
COMPS: The Proposal (2009), The American President

CHARACTERS:
  • Margaret Tate (Protagonist): High-powered book editor, Canadian, facing deportation
  • Andrew Paxton (Love Interest): Margaret's assistant, dreams of being a writer

STRUCTURE: 30 scenes
```

---

## Step 3: Build Scene Context (SQL → String)

### Method: `get_surrounding_context(scene)`

**Purpose:** Pulls previous/next scenes from SQL array

```python
def get_surrounding_context(self, scene: Dict) -> Dict[str, Optional[str]]:
    scene_num = scene['scene_number']

    prev_scene = None
    next_scene = None

    # Loop through self.scenes (already loaded from SQL)
    for s in self.scenes:
        if s['scene_number'] == scene_num - 1:
            prev_scene = f"Scene {s['scene_number']}: {s['title']} - {s['description']}"
        elif s['scene_number'] == scene_num + 1:
            next_scene = f"Scene {s['scene_number']}: {s['title']} - {s['description']}"

    return {
        'previous': prev_scene,
        'next': next_scene
    }
```

**Input:** Scene 5 (from SQL)
```python
{
    'id': 5,
    'scene_number': 5,
    'title': 'The Proposal',
    'description': 'Margaret demands Andrew marry her',
    'characters': 'Margaret, Andrew',
    'act': 'Act 1'
}
```

**Output:**
```python
{
    'previous': 'Scene 4: Inciting Incident - Margaret learns she has 24 hours before deportation',
    'next': 'Scene 6: Debate - Andrew negotiates terms of the fake engagement'
}
```

---

## Step 4: Inject into Expert Prompts

### Method: `build_expert_query(scene, bucket_name)`

**Example for Books Bucket:**

```python
def build_expert_query(self, scene: Dict, bucket_name: str) -> str:
    story_outline = self.build_story_outline()  # ← SQL data formatted
    scene_chars = scene.get('characters', '')    # ← From SQL scenes table
    surrounding = self.get_surrounding_context(scene)  # ← From SQL scenes table

    context_section = f"""STORY OUTLINE:
{story_outline}  # ← Injected here

SCENE CONTEXT:
Scene {scene['scene_number']}: {scene['title']}  # ← From SQL
Act: {scene.get('act', 'Unknown')}  # ← From SQL
Description: {scene['description']}  # ← From SQL
Characters: {scene_chars}  # ← From SQL

SURROUNDING SCENES:
Previous: {surrounding['previous'] or 'N/A'}  # ← From SQL
Next: {surrounding['next'] or 'N/A'}"""  # ← From SQL

    if bucket_name == "books":
        return f"""You are a SCREENPLAY STRUCTURE AND CRAFT EXPERT...

{context_section}  # ← ALL SQL DATA INJECTED HERE

## STRUCTURAL ANALYSIS
- Where does this scene fall in the three-act structure?
...
"""
```

---

## Complete Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        SQLite Database                          │
├─────────────────────────────────────────────────────────────────┤
│ TABLE: projects                                                 │
│   - name, genre, description                                    │
│                                                                 │
│ TABLE: characters                                               │
│   - name, description, role, arc                                │
│                                                                 │
│ TABLE: scenes                                                   │
│   - scene_number, title, description, characters, act           │
│                                                                 │
│ TABLE: writer_notes                                             │
│   - logline, theme, tone, comps                                 │
└─────────────────────────────────────────────────────────────────┘
                            ↓
                   load_project_context()
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Python Objects (in memory)                   │
├─────────────────────────────────────────────────────────────────┤
│ self.project = {...}                                            │
│ self.characters = [{...}, {...}]                                │
│ self.scenes = [{...}, {...}, ..., {...}]  # 30 scenes           │
│ self.writer_notes = {...}                                       │
└─────────────────────────────────────────────────────────────────┘
                            ↓
            build_story_outline() + get_surrounding_context()
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                   Formatted Context Strings                     │
├─────────────────────────────────────────────────────────────────┤
│ story_outline = """                                             │
│   PROJECT: The Proposal 2.0                                     │
│   GENRE: Romantic Comedy                                        │
│   LOGLINE: A demanding boss forces...                           │
│   CHARACTERS:                                                   │
│     • Margaret Tate (Protagonist): High-powered...              │
│   STRUCTURE: 30 scenes                                          │
│ """                                                             │
│                                                                 │
│ surrounding = {                                                 │
│   'previous': 'Scene 4: Inciting Incident...',                  │
│   'next': 'Scene 6: Debate...'                                  │
│ }                                                               │
└─────────────────────────────────────────────────────────────────┘
                            ↓
                   build_expert_query()
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                      LLM Prompt (Books)                         │
├─────────────────────────────────────────────────────────────────┤
│ You are a SCREENPLAY STRUCTURE AND CRAFT EXPERT...              │
│                                                                 │
│ GOLDEN-AGE ROMANTIC COMEDY DEFINITION:                          │
│ [Definition text]                                               │
│                                                                 │
│ STORY OUTLINE:                                                  │
│ PROJECT: The Proposal 2.0                    ← FROM projects    │
│ GENRE: Romantic Comedy                       ← FROM projects    │
│ LOGLINE: A demanding boss...                 ← FROM writer_notes│
│ THEME: True love requires...                 ← FROM writer_notes│
│ CHARACTERS:                                                     │
│   • Margaret Tate (Protagonist): ...         ← FROM characters  │
│   • Andrew Paxton (Love Interest): ...       ← FROM characters  │
│ STRUCTURE: 30 scenes                         ← FROM scenes      │
│                                                                 │
│ SCENE CONTEXT:                                                  │
│ Scene 5: The Proposal                        ← FROM scenes[4]   │
│ Act: Act 1                                   ← FROM scenes[4]   │
│ Description: Margaret demands...             ← FROM scenes[4]   │
│ Characters: Margaret, Andrew                 ← FROM scenes[4]   │
│                                                                 │
│ SURROUNDING SCENES:                                             │
│ Previous: Scene 4: Inciting Incident...      ← FROM scenes[3]   │
│ Next: Scene 6: Debate...                     ← FROM scenes[5]   │
│                                                                 │
│ ## STRUCTURAL ANALYSIS                                          │
│ - Where does this scene fall in the three-act structure?        │
│ ...                                                             │
└─────────────────────────────────────────────────────────────────┘
                            ↓
                    LightRAG Query (Books)
                            ↓
                    [Repeat for Plays]
                            ↓
                    [Repeat for Scripts]
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                   Synthesis Prompt (GPT-4o)                     │
├─────────────────────────────────────────────────────────────────┤
│ You are a MASTER SCREENPLAY CONSULTANT...                       │
│                                                                 │
│ STORY CONTEXT:                                                  │
│ [Same SQL data injected again]              ← FROM SQL          │
│                                                                 │
│ THREE EXPERT CONSULTATIONS:                                     │
│ === BOOKS EXPERT ANALYSIS ===                                   │
│ [Books LLM response]                                            │
│                                                                 │
│ === PLAYS EXPERT ANALYSIS ===                                   │
│ [Plays LLM response]                                            │
│                                                                 │
│ === SCRIPTS EXPERT ANALYSIS ===                                 │
│ [Scripts LLM response]                                          │
│                                                                 │
│ Synthesize into comprehensive scene blueprint...                │
└─────────────────────────────────────────────────────────────────┘
                            ↓
                   GPT-4o Synthesis Output
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                   Save Back to SQL                              │
├─────────────────────────────────────────────────────────────────┤
│ INSERT INTO brainstorm_sessions                                 │
│ (scene_id, tone, bucket_used, content)                          │
│ VALUES                                                          │
│   (5, 'Golden Age...', 'books', '[Books response]'),            │
│   (5, 'Golden Age...', 'plays', '[Plays response]'),            │
│   (5, 'Golden Age...', 'scripts', '[Scripts response]'),        │
│   (5, 'Golden Age...', 'all', '[Synthesized blueprint]')        │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Insight: Dynamic Context Assembly

**Every prompt is assembled fresh from SQL data:**

1. **User enters data in INTAKE** → Saved to SQL tables
2. **Automated Brainstorm loads SQL** → Into Python objects
3. **For each scene, SQL data is formatted** → Into prompt strings
4. **Prompts sent to LightRAG + GPT-4o** → With full context
5. **Results saved back to SQL** → For use by WRITE module

**No hardcoded story data** - everything flows dynamically from the database!

---

## Example: What Gets Injected for Scene 5

**From SQL:**
- Project name: "The Proposal 2.0"
- Genre: "Romantic Comedy"
- Logline: "A demanding boss forces her assistant into a fake engagement..."
- Theme: "True love requires vulnerability and equality"
- Characters: Margaret (Protagonist), Andrew (Love Interest)
- Scene 5 title: "The Proposal"
- Scene 5 description: "Margaret demands Andrew marry her"
- Previous scene: "Scene 4: Inciting Incident - Deportation notice"
- Next scene: "Scene 6: Debate - Andrew negotiates terms"

**Into Prompt:**
All of the above gets formatted and injected into the "STORY OUTLINE" and "SCENE CONTEXT" sections of each bucket's expert query.

**Result:**
LightRAG queries are contextualized with the FULL story, ensuring expert analysis is specific to THIS project, not generic romcom advice.
