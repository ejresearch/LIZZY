# WRITE Module

**Blueprint → Prose Converter**

The WRITE module transforms brainstorm blueprints into actual screenplay prose (700-900 words per scene) with golden-era romantic comedy tone.

---

## Overview

The WRITE module is the final step in Lizzy's screenplay pipeline:

```
START → INTAKE → BRAINSTORM → WRITE → Export
```

**What it does:**
1. Loads scene blueprint from brainstorm session
2. Adds continuity context (previous/next scenes)
3. Applies golden-era romcom tone principles
4. Generates 700-900 word prose with GPT-4o
5. Saves versioned drafts to database

---

## Quick Start

### Method 1: Python Import

```python
import asyncio
from lizzy.write import WriteModule

async def main():
    # Initialize for your project
    writer = WriteModule('the_proposal_2_0')

    # Load scene context
    context = writer.load_scene_context(1)

    # Generate draft
    draft = await writer.generate_draft(context)

    # Save to database
    draft_id = writer.save_draft(draft)

    # Display result
    writer.display_draft(draft)

asyncio.run(main())
```

### Method 2: CLI Interface

```bash
# Run the interactive CLI
python3 -m lizzy.write

# Or use the main function
python3 lizzy/write.py
```

CLI Options:
1. **Write a scene** - Generate new draft
2. **View drafts** - See all versions for a scene
3. **Exit**

---

## How It Works

### 1. Scene Context Loading

The module loads comprehensive context for writing:

```python
context = writer.load_scene_context(scene_number)
```

**What gets loaded:**
- **Scene basics**: number, title, description, characters, tone
- **Blueprint**: Latest brainstorm session content (if exists)
- **Previous draft**: Last scene's prose (for continuity)
- **Next outline**: Next scene's description (for foreshadowing)

### 2. Prompt Building

The module builds a rich prompt with:

**Scene Information:**
```
SCENE 1: Meeting at the Bookshop
Description: Lucy runs a quirky NYC bookshop...
Characters: Lucy, Marcus
Tone: Light, witty, sparks flying
```

**Blueprint (from brainstorm):**
```
BLUEPRINT FROM BRAINSTORM:
- Marcus enters looking for rare architecture book
- Banter about his "corporate" vibe vs her "bohemian" aesthetic
- Chemistry through verbal sparring
- He leaves intrigued, she's flustered
```

**Continuity Context:**
```
PREVIOUS SCENE (for continuity):
[First 300 characters of previous scene's prose]

NEXT SCENE (to foreshadow):
Marcus returns the next day with coffee as peace offering
```

**Writing Instructions:**
- Present tense, active voice
- 800 words (700-900 range)
- Vivid action and dialogue
- Show emotions through actions
- Build romantic/comedic tension
- Maintain continuity
- Set up next scene organically

### 3. Golden-Era Romcom Tone

The system message enforces classic romcom principles:

**PRINCIPLES:**
- Genuine emotional stakes and vulnerability
- Witty, quotable dialogue that reveals character
- Earned romantic moments with clear "why them" chemistry
- Universal yet specific conflicts (career vs love, timing, class)
- Memorable set pieces; heart over hijinks

**AVOID:**
- Contrived misunderstandings solvable by one conversation
- Cruelty or mean-spirited humor
- Humiliation comedy
- Relationships without foundation

**Inspiration:**
- When Harry Met Sally
- You've Got Mail
- Pretty Woman
- Sleepless in Seattle
- Notting Hill

### 4. Draft Generation

```python
draft = await writer.generate_draft(
    context,
    model="gpt-4o",        # or "gpt-4o-mini"
    target_words=800       # 700-900 range
)
```

**Result:**
- 700-900 words of screenplay prose
- Present tense narration
- Dialogue and action
- Character emotions shown through behavior
- Romantic/comedic tension
- Scene structure (opening, rising action, peak, resolution)

### 5. Draft Storage

Drafts are saved with versioning:

```python
draft_id = writer.save_draft(draft)
```

**Database:** `scene_drafts` table
**Tracks:**
- Content (prose)
- Version number (v1, v2, v3...)
- Word count
- Tokens used
- Cost estimate
- Created timestamp

**Versioning:**
- Each new draft for the same scene increments version
- All versions preserved
- Can retrieve any version later

---

## Database Schema

### scene_drafts Table

```sql
CREATE TABLE scene_drafts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scene_id INTEGER NOT NULL,           -- References scenes(id)
    content TEXT NOT NULL,               -- The prose
    version INTEGER DEFAULT 1,           -- v1, v2, v3...
    word_count INTEGER,                  -- Actual word count
    tokens_used INTEGER,                 -- GPT tokens consumed
    cost_estimate REAL,                  -- Estimated cost in USD
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (scene_id) REFERENCES scenes(id)
)
```

**Note:** This is separate from the `drafts` table (which stores full screenplay exports).

---

## Example Output

### Input Context

```
Scene 1: x
Description: x
Characters: (none)
Blueprint: None
```

### Generated Draft (891 words)

```
The scene opens in a lively, bustling bookshop in the heart of New York City,
filled with the comforting smell of aged paper and fresh coffee from the small
café in the back. The shop is nestled between two larger buildings, almost like
a secret waiting to be discovered. Outside, the city hums with a life of its own,
but inside, it's a different world—a haven of stories and possibilities.

Amidst the towering shelves, we find LUCY, a spirited woman in her thirties with
a penchant for old-fashioned romance novels and an uncanny ability to recommend
the perfect book to anyone who walks through the door...

[continues for ~800 words with dialogue, action, and romantic tension]
```

**Stats:**
- Word count: 891
- Tokens: 1,481
- Cost: $0.0148
- Version: 1

---

## API Reference

### WriteModule Class

```python
class WriteModule:
    def __init__(self, project_name: str)
    def load_scene_context(self, scene_number: int) -> Optional[SceneContext]
    async def generate_draft(self, context: SceneContext,
                            model: str = "gpt-4o",
                            target_words: int = 800) -> Draft
    def save_draft(self, draft: Draft) -> int
    def get_all_drafts(self, scene_number: int) -> List[Draft]
    def display_draft(self, draft: Draft)
```

### SceneContext Dataclass

```python
@dataclass
class SceneContext:
    scene_id: int              # Database ID
    scene_number: int          # Scene number (1-30)
    title: str                 # Scene title
    description: str           # Scene description
    characters: str            # Comma-separated character names
    tone: Optional[str]        # Desired tone
    blueprint: Optional[str]   # From brainstorm session
    previous_draft: Optional[str]  # Previous scene's prose
    next_outline: Optional[str]    # Next scene's description
```

### Draft Dataclass

```python
@dataclass
class Draft:
    scene_id: int              # Database ID
    scene_number: int          # For display
    content: str               # The prose
    version: int               # Version number
    word_count: int            # Word count
    tokens_used: int           # GPT tokens
    cost_estimate: float       # Estimated cost
    created_at: str            # ISO timestamp
```

---

## Cost Estimates

Based on GPT-4o pricing (as of 2025):

**Per Scene (800 words):**
- Input: ~500 tokens (context)
- Output: ~1,000 tokens (prose)
- Total: ~1,500 tokens
- **Cost: ~$0.015 per scene**

**Full 30-Scene Screenplay:**
- Total tokens: ~45,000
- **Total cost: ~$0.45**

**With Revisions (3 drafts per scene):**
- Total cost: ~$1.35

**Note:** Actual costs vary based on context size and output length.

---

## Writing Without Blueprints

The WRITE module can generate prose even without brainstorm blueprints:

**How it works:**
1. Uses scene description as the primary guide
2. Infers character dynamics from character names
3. Applies tone if specified
4. Still maintains continuity with prev/next scenes
5. Follows golden-era romcom principles

**When to use:**
- Quick prototyping
- Scenes with clear, detailed descriptions
- Testing the module
- Simple transitional scenes

**Best practice:**
- Run BRAINSTORM first for richer, more detailed prose
- Blueprint provides specific beats and dialogue ideas
- Better character development
- More cohesive story flow

---

## CLI Menu Example

```
╔═══════════════════════════════════════╗
║     WRITE - Draft Generation          ║
╚═══════════════════════════════════════╝

Options:
1. Write a scene (generate draft)
2. View drafts for a scene
3. Exit

Choose [1]:

Scene number [1]: 4

📖 Loading context for Scene 4...

Scene 4: Coffee Shop Reunion
Marcus bumps into Lucy at her favorite café

✅ Blueprint found

Generate draft? [y/n]: y

✍️  Generating draft... This may take 20-30 seconds...

✅ Saved as Draft v1 (ID: 4)

╭─ 📝 Draft (v1) ────────────────────────────────╮
│ Marcus pushes through the glass door of the    │
│ small corner café, shaking rain from his coat. │
│ He's here for his usual—black coffee, no       │
│ distractions—but then he sees her...           │
│                                                 │
│ [full prose continues...]                      │
╰────────────────────────────────────────────────╯

Words: 847 | Tokens: 1,523 | Cost: $0.0152
Created: 2025-10-22T17:31:02.792679
```

---

## Integration with Other Modules

### Complete Pipeline

```python
# 1. START - Create project structure
from lizzy.start import StartModule
starter = StartModule()
starter.create_project("my_romcom")

# 2. INTAKE - Populate with story data
from lizzy.intake import IntakeModule
intake = IntakeModule("my_romcom")
await intake.run()

# 3. BRAINSTORM - Generate scene blueprints
from lizzy.brainstorm import BrainstormModule
brainstorm = BrainstormModule("my_romcom")
blueprint = await brainstorm.run_scene(1)

# 4. WRITE - Generate prose from blueprint
from lizzy.write import WriteModule
writer = WriteModule("my_romcom")
context = writer.load_scene_context(1)
draft = await writer.generate_draft(context)
writer.save_draft(draft)

# 5. EXPORT - Compile full screenplay (future)
```

### With Prompt Studio

```python
# Use Prompt Studio to build custom context
from lizzy.prompt_studio import AIBlockComposer

composer = AIBlockComposer("my_romcom")
result = await composer.compose(
    "Help me write scene 4 with romantic tension"
)

# Then use WRITE with the composed prompt
# (Future integration - not yet built)
```

---

## File Structure

```
lizzy/
└── write.py                    # WRITE module (475 lines)
    ├── GOLDEN_ERA_ROMCOM_TONE  # System message
    ├── SceneContext            # Context dataclass
    ├── Draft                   # Draft dataclass
    ├── WriteModule             # Main class
    │   ├── __init__()
    │   ├── _init_drafts_table()
    │   ├── load_scene_context()
    │   ├── generate_draft()
    │   ├── _build_write_prompt()
    │   ├── save_draft()
    │   ├── _get_next_version()
    │   ├── _estimate_cost()
    │   ├── get_all_drafts()
    │   └── display_draft()
    └── main()                  # CLI interface
```

---

## Testing

Test script included: `test_write.py`

```bash
python3 test_write.py
```

**Tests:**
1. Loading scene context
2. Generating a draft
3. Saving to database
4. Retrieving all drafts

**Expected output:**
```
============================================================
Testing WRITE Module
============================================================

1. Loading scene 1 context...
✅ Loaded: Scene 1: x

2. Generating draft...
✅ Generated draft: v1, 891 words, $0.0148

3. Saving draft to database...
✅ Saved as draft ID: 1

4. Retrieving all drafts for scene 1...
✅ Found 1 draft(s): v1, 891 words

============================================================
✅ All tests passed!
============================================================
```

---

## Future Enhancements

**Not yet implemented (from white paper and Old Ender):**

1. **Batch Processing**
   - Process all 30 scenes automatically
   - Queue management
   - Progress tracking

2. **Export Formats**
   - Compile full screenplay to .txt
   - Export to .md with formatting
   - Screenplay format converter

3. **Advanced Continuity**
   - Cross-reference character arcs
   - Track recurring motifs
   - Ensure tonal consistency

4. **Tone Options**
   - Multiple tone presets beyond romcom
   - Custom tone definitions
   - Genre switching

5. **Revision System**
   - Compare versions side-by-side
   - Merge best elements
   - Track changes

6. **Quality Metrics**
   - Dialogue balance
   - Pacing analysis
   - Character presence tracking

---

## Troubleshooting

### Error: "Scene not found"

**Cause:** Scene number doesn't exist in database

**Fix:**
```bash
# Check what scenes exist
sqlite3 projects/my_project/my_project.db \
  "SELECT scene_number, title FROM scenes;"

# Run INTAKE to populate scenes
python3 -m lizzy.intake
```

### Error: "No blueprint available"

**Cause:** Scene hasn't been brainstormed yet

**Fix:**
```python
# Run brainstorm first
from lizzy.brainstorm import BrainstormModule
brainstorm = BrainstormModule("my_project")
await brainstorm.run_scene(1)

# Or proceed without blueprint
# (WRITE will use scene description only)
```

### Error: "OpenAI API key not found"

**Cause:** OPENAI_API_KEY environment variable not set

**Fix:**
```bash
export OPENAI_API_KEY="sk-..."

# Or add to .env file
echo 'OPENAI_API_KEY="sk-..."' >> .env
```

### Draft quality issues

**Too generic:**
- Run BRAINSTORM first for detailed blueprint
- Add more specific scene description
- Specify character names

**Wrong tone:**
- Currently only supports golden-era romcom
- Future: Custom tone options

**Continuity problems:**
- Ensure previous scenes are written first
- Check that scene descriptions flow logically

---

## Key Design Decisions

### Why separate `scene_drafts` table?

The existing `drafts` table is designed for full screenplay exports. Scene-specific drafts need different tracking:
- Linked to individual scenes
- Version control per scene
- Word count and cost per scene
- Independent lifecycle from full drafts

### Why 700-900 words?

Based on Old Ender specs and screenplay math:
- Feature film: 90-110 minutes
- 1 page ≈ 1 minute
- 30 scenes ≈ 3-4 pages per scene
- 3 pages ≈ 750 words

### Why GPT-4o not GPT-4o-mini?

**Creative writing needs:**
- Better prose quality
- More natural dialogue
- Stronger character voice
- Worth the cost difference (~$0.015 vs $0.0006 per scene)

**Cost comparison:**
- GPT-4o: $0.45 for full screenplay
- GPT-4o-mini: $0.018 for full screenplay
- Quality difference: Significant for final prose

### Why async/await?

- LLM calls take 20-30 seconds
- Allows for future parallel processing
- Better user experience (can show progress)
- Consistent with other modules

---

## Credits

**Based on:**
- Lizzy 2.0 White Paper
- Old Ender v1.0 write.py
- Golden-era romcom principles
- Classic screenplay structure

**Inspired by:**
- When Harry Met Sally (Nora Ephron)
- You've Got Mail (Nora Ephron)
- Pretty Woman (J.F. Lawton)
- Sleepless in Seattle (Jeff Arch)
- Notting Hill (Richard Curtis)

---

## Related Documentation

- [Lizzy Architecture](LIZZY_ARCHITECTURE.md)
- [Brainstorm Module](BRAINSTORM.md)
- [Prompt Studio](PROMPT_STUDIO_ARCHITECTURE.md)
- [White Paper](LIZZY_WHITE_PAPER.md)

---

**Status:** ✅ **Core functionality complete and tested**

**Version:** 1.0
**Last Updated:** October 22, 2025
**Test Status:** All tests passing
