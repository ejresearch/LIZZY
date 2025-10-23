# Lizzy 2.0 - Quick Start Guide

**Complete AI-assisted screenplay writing in 5 simple steps**

---

## ⚡ Express Pipeline (30 minutes to first draft)

```bash
# 1. Create project (2 min)
python3 -m lizzy.start

# 2. Add your story (20 min)
python3 -m lizzy.intake "my_screenplay"

# 3. Generate blueprints (5 min)
python3 -m lizzy.automated_brainstorm

# 4. Write all 30 scenes (45 min)
python3 -m lizzy.automated_write

# 5. Export screenplay (1 min)
python3 -m lizzy.export
```

**Total time:** ~70 minutes
**Total cost:** ~$0.60
**Output:** Complete 30-scene screenplay in 4 formats

---

## 📋 Prerequisites

### 1. Install Dependencies

```bash
pip install openai lightrag-hku rich fastapi uvicorn pyvis cohere
```

### 2. Set API Keys

```bash
# Quick setup (interactive)
./setup_keys.sh

# Or manually
export OPENAI_API_KEY="sk-..."
export COHERE_API_KEY="..."  # Optional for reranking
```

### 3. Verify Installation

```bash
python3 -m lizzy.start --help
```

---

## 🎯 Step-by-Step Guide

### Step 1: Create Project

```bash
python3 -m lizzy.start
```

**Prompts:**
- Enter project name (e.g., "my_romcom")

**Output:**
- `projects/my_romcom/my_romcom.db` (SQLite database)
- `projects/my_romcom/exports/` (empty folder)

**Time:** 2 minutes

---

### Step 2: Add Story Data

```bash
python3 -m lizzy.intake "my_romcom"
```

**Interactive menu for:**

1. **Characters**
   - Name, role, description, arc
   - Add as many as needed

2. **Scenes** (30-beat structure)
   - Auto-populated with Save the Cat beats
   - Edit title, description, characters per scene
   - Specify tone/mood

3. **Writer's Notes**
   - Logline
   - Theme
   - Genre
   - Tone
   - Comparable films

**Tips:**
- Use descriptive scene descriptions (2-3 sentences)
- List main characters per scene
- Be specific about tone (witty, emotional, tense, etc.)

**Time:** 20 minutes

---

### Step 3: Generate Blueprints

```bash
python3 -m lizzy.automated_brainstorm
```

**Process:**
- Queries 3 expert knowledge buckets (books, plays, scripts)
- Synthesizes guidance for each scene
- Uses feed-forward context (each scene builds on previous)

**Options:**
- All scenes (1-30)
- By act (Act 1, 2, or 3)
- Custom range

**Output:**
- 120 brainstorm_sessions (4 per scene: books, plays, scripts, synthesized)

**Time:** ~5 minutes for all 30 scenes
**Cost:** ~$0.15

**Note:** You need RAG buckets set up first (one-time):

```bash
python3 manage_buckets.py
# Create "books", "plays", "scripts" buckets
# Add documents to each
```

---

### Step 4: Write Scenes

#### Option A: Automated (Recommended for first draft)

```bash
python3 -m lizzy.automated_write
```

**Process:**
- Loads blueprint for each scene
- Adds previous scene's draft (continuity)
- Adds next scene's outline (foreshadowing)
- Generates 700-900 word prose
- Saves to database

**Options:**
- **Scene range:**
  - All scenes (1-30)
  - By act (1-10, 11-20, 21-30)
  - Custom range

- **Model:**
  - `gpt-4o` - Higher quality (~$0.015/scene)
  - `gpt-4o-mini` - Faster/cheaper (~$0.001/scene)

**Time:** ~45 minutes for all 30 scenes (gpt-4o)
**Cost:** ~$0.45

**Output:** 30 scene drafts in database

---

#### Option B: Interactive (For revisions)

```bash
python3 -m lizzy.write
```

**Menu:**
1. Write a scene - Generate one scene at a time
2. View drafts - See all versions of a scene

**Best for:**
- Revising specific scenes
- Creating v2, v3 iterations
- Manual quality control

---

### Step 5: Export Screenplay

```bash
python3 -m lizzy.export
```

**Options:**

1. **Version strategy:**
   - Use latest version of each scene
   - Use specific version number

2. **Format:**
   - **Plain Text (.txt)** - Simple readable format
   - **Markdown (.md)** - With formatting and act headers
   - **Fountain (.fountain)** - Industry-standard screenplay markup
   - **Final Draft XML (.fdx)** - Import to Final Draft software
   - **All formats** - Get all 4 at once

**Output:**
- Files in `projects/my_romcom/exports/`
- Stats: total words, page count estimate

**Time:** 1 minute
**Cost:** $0

**What you can do with exports:**
- **.txt** - Read/share as plain text
- **.md** - View in any markdown editor, convert to PDF
- **.fountain** - Open in Final Draft, Highland, Fade In, WriterDuet
- **.fdx** - Direct import to Final Draft

---

## 🔄 Full Workflow Example

**Project:** "The Bookshop Romance"

```bash
# Setup (Day 1 - 30 min)
python3 -m lizzy.start
# Name: "bookshop_romance"

python3 -m lizzy.intake "bookshop_romance"
# Add characters:
#   - Emma (bookshop owner, guarded, arc: learns to trust)
#   - Jake (customer, charming, arc: learns commitment)
#   - Sophie (best friend, supportive)
# Fill 30 scenes with descriptions
# Add notes:
#   - Logline: "A bookshop owner falls for a mysterious customer..."
#   - Tone: Witty, warm, Nora Ephron-esque
#   - Comps: You've Got Mail, Notting Hill

# Knowledge (one-time setup - 20 min)
python3 manage_buckets.py
# Create: books, plays, scripts
# Add: Save the Cat PDF, screenplay theory, romcom scripts

# Brainstorm (Day 2 - 5 min)
python3 -m lizzy.automated_brainstorm
# Select: All scenes (1-30)
# Wait: ~5 minutes
# Check database: 120 brainstorm_sessions created

# Write (Day 3 - 45 min)
python3 -m lizzy.automated_write
# Select: All scenes (1-30)
# Model: gpt-4o
# Wait: ~45 minutes
# Check database: 30 scene_drafts created

# Review & Revise (Day 4 - as needed)
python3 -m lizzy.write
# Write a scene: 15 (rewrite midpoint)
# View drafts: Compare v1 and v2

# Export (Day 5 - 1 min)
python3 -m lizzy.export
# Version: Latest
# Format: All formats
# Output: 4 files in exports/

# Edit in Final Draft
open projects/bookshop_romance/exports/*.fountain
# Or import .fdx to Final Draft
```

**Result:** Complete first draft screenplay in ~5 days, ready for professional editing

---

## 💡 Tips & Best Practices

### For Better Blueprints

1. **Detailed scene descriptions**
   - Bad: "They meet at the bookshop"
   - Good: "Emma helps Jake find a rare poetry book. Their shared love of literature sparks chemistry. He lingers, making excuses to keep talking."

2. **Specific character notes**
   - Include key character traits in descriptions
   - Specify emotional state per scene
   - Note character goals/obstacles

3. **Use all 3 buckets**
   - Books = Structure guidance
   - Plays = Dialogue/dramatic wisdom
   - Scripts = Visual execution

### For Better Prose

1. **Run brainstorm first**
   - Blueprints dramatically improve prose quality
   - Without blueprints, AI writes from scene description only

2. **Choose the right model**
   - **gpt-4o:** Better dialogue, nuance, emotional depth
   - **gpt-4o-mini:** Faster, cheaper, good structure but less nuanced

3. **Use sequential writing**
   - Write Scene 1 before Scene 2
   - Feed-forward context creates better continuity
   - Scene 30 benefits from all 29 previous scenes

4. **Revise strategically**
   - First draft: Use automated_write for all 30
   - Second pass: Use interactive write for weak scenes
   - Creates v2, v3 versions for comparison

### For Professional Results

1. **Edit the exports**
   - AI prose is 70-80% there
   - Use .fountain in professional software
   - Polish dialogue, tighten action, add personal voice

2. **Version control**
   - Database keeps all versions forever
   - Can always go back to v1
   - Export different versions for comparison

3. **Iterate scenes individually**
   - If Scene 12 feels off, regenerate just that scene
   - Try different temperature/approach
   - Compare v1, v2, v3 side by side

---

## 🐛 Common Issues

### "No module named 'openai'"

**Fix:**
```bash
pip install openai
```

### "OPENAI_API_KEY not found"

**Fix:**
```bash
export OPENAI_API_KEY="sk-..."
# Or run: ./setup_keys.sh
```

### "No blueprint available"

**Fix:**
```bash
python3 -m lizzy.automated_brainstorm
# Must run brainstorm before write
```

### "Scene not found"

**Fix:**
```bash
python3 -m lizzy.intake "project_name"
# Must populate scenes with INTAKE first
```

### "No drafts found for export"

**Fix:**
```bash
python3 -m lizzy.automated_write
# Must write scenes before exporting
```

---

## 📊 Cost Calculator

**30-scene screenplay:**

| Component | Model | Cost |
|-----------|-------|------|
| Brainstorm | gpt-4o-mini | $0.15 |
| Write | gpt-4o | $0.45 |
| Write | gpt-4o-mini | $0.03 |
| Export | N/A | $0.00 |

**Total (quality):** $0.60 (brainstorm + gpt-4o write)
**Total (budget):** $0.18 (brainstorm + gpt-4o-mini write)

**With 3 revisions per scene:** ~$1.80 total

---

## 🎨 Advanced: Prompt Studio

For complex scenes, use Prompt Studio for experimentation:

```bash
./start_prompt_studio.sh
# Open: http://localhost:8001
```

**Natural language examples:**

- "Help me with scene 12, check all experts"
- "Character Emma in scene 4, dialogue focus"
- "Brainstorm scene 15 with scripts bucket"

**AI automatically:**
1. Parses your intent
2. Builds appropriate blocks (SQL + RAG)
3. Assembles rich prompt
4. Shows visual feedback
5. Executes with LLM

**Use for:**
- Exploring different approaches before brainstorming
- Testing specific RAG bucket queries
- Getting creative ideas
- Debugging scene issues

---

## 📁 Project Structure

After running the pipeline:

```
projects/my_screenplay/
├── my_screenplay.db          # All data (characters, scenes, drafts)
└── exports/
    ├── my_screenplay_v1_20250123.txt
    ├── my_screenplay_v1_20250123.md
    ├── my_screenplay_v1_20250123.fountain
    └── my_screenplay_v1_20250123.fdx
```

**Database tables:**
- `scenes` - 30-beat structure
- `characters` - Cast
- `notes` - Writer's notes
- `brainstorm_sessions` - Blueprints (120 rows)
- `scene_drafts` - Prose versions

---

## 🚀 Next Steps

1. **Edit in professional software**
   - Import .fountain or .fdx
   - Polish dialogue and action
   - Add your voice

2. **Share for feedback**
   - Export .txt for easy reading
   - Export .md for web sharing
   - Get notes from readers

3. **Iterate**
   - Identify weak scenes
   - Regenerate with interactive write
   - Compare versions
   - Re-export

4. **Extend the system**
   - Add more RAG buckets for different genres
   - Customize tone presets
   - Build character voice profiles

---

## 📞 Support

**Issues:** https://github.com/ejresearch/LIZZY/issues

**Documentation:** See `docs/` folder

**Key docs:**
- `ARCHITECTURE_MAP.md` - Complete system overview
- `WRITE_MODULE.md` - WRITE documentation
- `PROMPT_STUDIO_ARCHITECTURE.md` - Prompt Studio guide

---

**🎬 Ready to write? Run: `python3 -m lizzy.start`**
