# How Automated Brainstorm Works - Complete Walkthrough

## Overview

Automated Brainstorm processes all 30 scenes from your romcom beat sheet, consulting three expert knowledge graphs (books, plays, scripts) for each scene, then synthesizing their insights into comprehensive scene blueprints.

**Key Innovation:** Each scene builds on previous scenes through feed-forward delta summaries, creating cumulative narrative understanding.

---

## Step-by-Step Execution

### Step 0: User Runs the Script

```bash
python3 autobrainstorm.py
# OR
python3 -m lizzy.automated_brainstorm
```

**What Happens:**
1. System shows list of available projects
2. User selects project (e.g., "The Proposal 2.0")
3. System confirms: "Process all 30 scenes?"
4. User confirms
5. **Batch processing begins** ⚡

---

### Step 1: Load All Project Data (Once at Startup)

```python
brainstorm = AutomatedBrainstorm(db_path)
brainstorm.load_project_context()
```

**SQL Queries Executed:**

```sql
-- Query 1: Project metadata
SELECT * FROM projects LIMIT 1
-- Returns: {'name': 'The Proposal 2.0', 'genre': 'Romantic Comedy', ...}

-- Query 2: All characters
SELECT name, description, role, arc FROM characters
-- Returns: [
--   {'name': 'Margaret Tate', 'description': 'High-powered editor...', 'role': 'Protagonist', 'arc': 'Ice queen to vulnerable'},
--   {'name': 'Andrew Paxton', 'description': 'Assistant...', 'role': 'Love Interest', 'arc': 'Doormat to equal'}
-- ]

-- Query 3: All 30 scenes
SELECT id, scene_number, title, description, characters, tone, act
FROM scenes
ORDER BY scene_number
-- Returns: [
--   {'id': 1, 'scene_number': 1, 'title': 'Opening Image', 'description': '...', 'act': 'Act 1'},
--   {'id': 2, 'scene_number': 2, 'title': 'Status Quo', ...},
--   ... (30 total)
-- ]

-- Query 4: Writer notes
SELECT * FROM writer_notes LIMIT 1
-- Returns: {'logline': '...', 'theme': '...', 'tone': '...', 'comps': '...'}
```

**Result:**
All project data is now **in memory** for the entire run. No more database reads during processing (except for feed-forward delta summaries).

---

### Step 2: Process Scene 1 (Bootstrap Phase)

#### 2A. Build Story Outline

```python
story_outline = self.build_story_outline()
```

**Output:**
```
PROJECT: The Proposal 2.0
GENRE: Romantic Comedy

LOGLINE: A demanding boss forces her assistant into a fake engagement to avoid deportation
THEME: True love requires vulnerability and equality
TONE: Screwball comedy with romantic heart
COMPS: The Proposal (2009), The American President

CHARACTERS:
  • Margaret Tate (Protagonist): High-powered book editor, Canadian, facing deportation...
  • Andrew Paxton (Love Interest): Margaret's assistant, aspiring writer...

STRUCTURE: 30 scenes
```

This story outline gets **injected into every prompt** for all 3 buckets and synthesis.

---

#### 2B. Get Surrounding Context

```python
surrounding = self.get_surrounding_context(scene_1)
```

**For Scene 1:**
```python
{
    'previous': None,  # First scene, no previous
    'next': 'Scene 2: Status Quo - Margaret commands her empire...'
}
```

**No delta summary yet** - Scene 1 is the bootstrap, nothing came before it.

---

#### 2C. Query Books Bucket (Structure Expert)

**Prompt Built:**
```
---
SCENE_ID: 1
SCENE_NUMBER: 1
ACT: Act 1
BUCKET: books
MODEL: gpt-4o-mini (LightRAG)
VERSION: 2.0
PROJECT: The Proposal 2.0
TIMESTAMP: 2025-01-22T15:45:00
---

You are a SCREENPLAY STRUCTURE AND CRAFT EXPERT consulting on a golden-age romantic comedy.

GOLDEN-AGE ROMCOM: 1930s-50s screwball/romantic comedies featuring witty rapid-fire dialogue, class conflict, physical comedy, strong independent leads (esp. female), misunderstandings, sophisticated sexual tension (Production Code era). Reference: His Girl Friday, Philadelphia Story, It Happened One Night, Bringing Up Baby.

STORY OUTLINE:
PROJECT: The Proposal 2.0
GENRE: Romantic Comedy
LOGLINE: A demanding boss forces her assistant...
[... full outline ...]

SCENE CONTEXT:
Scene 1: Opening Image
Act: Act 1
Description: Margaret commands her publishing empire with icy efficiency
Characters: Margaret, office staff

SURROUNDING SCENES:
Previous: N/A (first scene)
Next: Scene 2: Status Quo - Margaret commands her empire...

As a structure expert, PROPOSE how to architect this scene's dramatic structure.

**OUTPUT REQUIREMENTS:**
- Bullet points only (no paragraphs)
- 5-7 bullets per section
- Target length: 400-800 tokens total
- Active, specific guidance (not theoretical analysis)

**DIRECTIVE:** Extend and critique the surrounding context; do not restate it.

## STRUCTURAL_FUNCTION
Propose where this scene falls structurally and what beat it must hit:
- Three-act position and romcom beat sheet function
- Structural purpose (setup, catalyst, midpoint reversal, crisis, climax)
- How this advances plot threads and character arcs

## BEAT_ENGINEERING
[... remaining sections ...]
```

**This prompt goes to LightRAG** which:
1. Searches the "books" knowledge graph (screenplay theory, structure books)
2. Finds relevant passages about opening images, Act 1 setup, romcom beats
3. Uses GPT-4o-mini to synthesize an answer
4. **Optional:** Cohere reranks the retrieved chunks for better relevance

**Books Response (example):**
```
## STRUCTURAL_FUNCTION
- Opening Image occurs in first 1-2 minutes, establishes protagonist's "before" state
- This is the setup phase: introduce Margaret's world, her power, her flaw (emotional coldness)
- Advances character arc by showing what needs to change (from control to vulnerability)

## BEAT_ENGINEERING
- Opening beat: Visual of Margaret's domain (corner office, pristine, controlled)
- Mid-scene beat: Show her competence and coldness through interactions
- Closing beat: Hint at isolation - she's powerful but alone
- Must establish contrast with eventual transformation

[... etc ...]
```

---

#### 2D. Query Plays Bucket (Dramatic Theory Expert)

**Same process**, but prompt asks about:
- Dialogue and subtext
- Character psychology (objectives, tactics, obstacles)
- Dramatic technique (irony, secrets, conflict)
- Emotional architecture
- Stage business and physical action

**Plays Response (example):**
```
## DIALOGUE_DYNAMICS
- Surface: Professional commands, efficient corporate speak
- Subtext: Margaret's emotional disconnect, fear of vulnerability masked by control
- Power dynamic: Margaret dominates every interaction
- Wordplay: Use clipped, authoritative language to show emotional armor

## CHARACTER_PSYCHOLOGY
- Margaret's objective: Maintain absolute control and efficiency
- Tactic: Intimidation, perfectionism, emotional distance
- Obstacle: No one challenges her (everyone fears her)
- How she masks feelings: Performance of confidence hides fear of intimacy

[... etc ...]
```

---

#### 2E. Query Scripts Bucket (Execution Expert)

**Same process**, but prompt asks about:
- Visual storytelling (camera, shots, visual comedy)
- Pacing and rhythm (tempo, cuts, timing)
- Romcom tropes to employ
- Dialogue execution (speed, overlapping, pauses)
- Performance notes (tone, physical comedy, chemistry)
- Practical considerations (pitfalls, examples, budget)

**Scripts Response (example):**
```
## VISUAL_STORYTELLING
- Opening shot: Slow push-in through glass walls toward Margaret's office (visual isolation)
- Camera: Controlled, symmetrical framing reflects her controlled world
- Visual comedy: None yet - establish serious baseline for later contrast
- Location: Sleek Manhattan publishing house, all glass and steel (cold, modern)

## PACING_AND_RHYTHM
- Tempo: Brisk, efficient - match Margaret's energy
- Cuts: Quick cuts between employees reacting to her commands
- Beats: Rapid-fire - establish pace that will slow when she's vulnerable later
- Film rhythm: Sets high-energy baseline

[... etc ...]
```

---

#### 2F. Synthesize All Three Experts (GPT-4o)

**Now GPT-4o receives:**
1. The same story outline and scene context
2. **All three expert responses** (Books + Plays + Scripts)
3. Instructions to synthesize into one unified blueprint

**Synthesis Prompt:**
```
---
SCENE_ID: 1
BUCKET: synthesis
MODEL: gpt-4o
VERSION: 2.0
---

You are a MASTER SCREENPLAY CONSULTANT synthesizing expert advice...

[... story context ...]

THREE EXPERT CONSULTATIONS:
=== BOOKS EXPERT ANALYSIS ===
[Full Books response - 400-800 tokens]

=== PLAYS EXPERT ANALYSIS ===
[Full Plays response - 400-800 tokens]

=== SCRIPTS EXPERT ANALYSIS ===
[Full Scripts response - 400-800 tokens]

**SYNTHESIS DIRECTIVE:**
- If experts disagree, prioritize cinematic clarity and character truth
- Reference expert insights directly (e.g., "Books expert notes...", "Scripts suggests...")
- Bullet points only (5-7 per section)
- Target length: 800-1200 tokens total

## SCENE_BLUEPRINT

### EXECUTIVE_SUMMARY
[3-5 sentence overview]

### STRUCTURAL_FUNCTION
[Synthesized from all three experts]

### DRAMATIC_BEATS
[...]

### DIALOGUE_AND_SUBTEXT
[...]

### VISUAL_AND_STAGING
[...]

### CHARACTER_PSYCHOLOGY
[...]

### GOLDEN_AGE_EXECUTION
[...]

### PITFALLS_TO_AVOID
[...]
```

**Synthesized Blueprint (example):**
```markdown
## SCENE_BLUEPRINT

### EXECUTIVE_SUMMARY
Scene 1 establishes Margaret's "before" state as an ice-queen publishing executive who commands her empire with ruthless efficiency. Books expert identifies this as the classic opening image that shows what will transform by film's end. Scripts recommends cold, controlled visuals (glass, steel, symmetry) that contrast with later warmth. Plays emphasizes showing her competence while hinting at isolation - she's powerful but emotionally disconnected.

### STRUCTURAL_FUNCTION
- Opening image of romcom beat sheet: shows protagonist's flawed "before" state
- Establishes Margaret's ordinary world before it's disrupted (inciting incident comes Scene 4)
- Advances character arc by showing emotional armor that must crack

### DRAMATIC_BEATS
- Opens with Margaret arriving at her pristine corner office, everything in its place
- Mid-scene: Efficient, intimidating interactions with staff (books expert: show competence + coldness)
- Someone makes a mistake → Margaret's icy response establishes her as formidable
- Closes with her alone in office, powerful but isolated (plays expert: visual of loneliness)
- Transition: Cuts to...

[... continues through all sections ...]
```

---

#### 2G. Save to Database

```python
# Save 4 brainstorm sessions for Scene 1
INSERT INTO brainstorm_sessions (scene_id, tone, bucket_used, content) VALUES
  (1, 'Golden Age Romantic Comedy', 'books', '[Books response]'),
  (1, 'Golden Age Romantic Comedy', 'plays', '[Plays response]'),
  (1, 'Golden Age Romantic Comedy', 'scripts', '[Scripts response]'),
  (1, 'Golden Age Romantic Comedy', 'all', '[Synthesized blueprint]')
```

**Result:** Scene 1 complete! Blueprint stored in database.

---

#### 2H. Display Result

```
✓ Scene 1: Opening Image

┌─ Scene 1 Guidance ────────────────────┐
│ ## SCENE_BLUEPRINT                    │
│                                       │
│ ### EXECUTIVE_SUMMARY                 │
│ Scene 1 establishes Margaret's...    │
│                                       │
│ ### STRUCTURAL_FUNCTION               │
│ - Opening image shows "before" state  │
│ [... full blueprint displayed ...]   │
└───────────────────────────────────────┘
```

User sees the result **immediately** as it completes.

---

### Step 3: Process Scene 2 (Feed-Forward Begins!)

#### 3A. Get Surrounding Context

```python
surrounding = self.get_surrounding_context(scene_2)
```

**Now there IS a previous scene!**

**What happens:**
1. System queries database for Scene 1's synthesized blueprint
2. **Generates 250-token delta summary** using GPT-4o-mini:

**Delta Summary Prompt:**
```
Compress this scene blueprint into a 250-token DELTA SUMMARY.

Focus on:
- What changed (character arcs, relationships, power dynamics)
- Key dramatic beats that occurred
- Emotional/tonal shifts
- Setup for next scene

Scene 1: Opening Image

FULL BLUEPRINT:
[2,000 token blueprint from Scene 1]

Provide a tight, bullet-point summary (250 tokens max) focusing on CHANGES and MOMENTUM.
```

**Delta Summary Output (example):**
```
SCENE 1 DELTA:
- Established Margaret's "before" state: ice-queen executive with absolute control
- Power dynamics: Margaret dominates all interactions, staff fears her
- Visual language set: cold glass/steel environment, controlled symmetry
- Emotional arc: Showed competence but hinted at isolation and loneliness
- Key beat: Margaret alone in office (powerful but disconnected)
- Setup for next: Ordinary world established, ready for disruption
- Tone: Brisk, efficient, emotionally armored
```

**Injection into Scene 2 prompts:**
```
SURROUNDING SCENES:
Previous: Scene 1: Opening Image

DELTA SUMMARY:
- Established Margaret's "before" state: ice-queen executive...
- Power dynamics: Margaret dominates...
[... 250-token summary ...]

Next: Scene 3: Theme Stated - Margaret's assistant Andrew hints at her isolation
```

---

#### 3B. Query All Three Buckets

**Books, Plays, Scripts all receive:**
- Same story outline (PROJECT, LOGLINE, THEME, CHARACTERS)
- Scene 2 details
- **Scene 1's delta summary** (250 tokens, not 2,000!)
- Scene 3's original description

**Each expert can now:**
- Build on Scene 1's established visual language
- Continue character dynamics from Scene 1
- Reference specific beats that occurred
- Avoid redundancy with Scene 1

**Example - Books Expert on Scene 2:**
```
## STRUCTURAL_FUNCTION
- Following Scene 1's establishment of ordinary world, Scene 2 deepens status quo
- Books expert: Continue the "before" state but add new dimension (introduce love interest)
- Building on Scene 1's isolation theme: show Margaret's treatment of Andrew specifically
```

Notice: Expert **extends** Scene 1 (doesn't restate it) thanks to "extend and critique" directive!

---

#### 3C. Synthesize → Save → Display

Same process as Scene 1, but now synthesis has richer context.

---

### Step 4: Process Scene 3 (Context Compounds!)

**Surrounding context for Scene 3:**
```
Previous: Scene 2: Status Quo

DELTA SUMMARY:
- Introduced Andrew Paxton (love interest) as Margaret's overworked assistant
- Power imbalance established: Margaret treats Andrew as invisible/expendable
- Showed Andrew's competence and hidden ambition (wants to be a writer)
- Visual contrast: Andrew's cramped desk vs Margaret's office (class divide)
- Emotional beat: Andrew's resentment brewing beneath compliant surface
- Setup for Scene 3: Tension between them ready to surface
- Builds on Scene 1: Margaret's coldness now has a specific victim
```

**Now Scene 3's experts see:**
- Scene 2's delta (which references Scene 1)
- They understand:
  - Margaret's cold persona (Scene 1)
  - Andrew as her victim (Scene 2)
  - Power imbalance trajectory (Scenes 1 + 2)

**Cumulative knowledge is building!**

---

### Step 5-30: Recursive Processing

**Scene 5 sees:**
- Scene 4 delta (which was informed by Scene 3 delta, which was informed by Scene 2 delta, which was informed by Scene 1)

**Scene 15 (Midpoint) sees:**
- Scene 14 delta (which contains cumulative knowledge of all 13 previous scenes)

**Scene 30 (Resolution) sees:**
- Scene 29 delta (which contains the entire narrative journey through 29 scenes!)

---

## Visual: Full System Flow

```
┌─────────────────────────────────────────────────────────────┐
│ USER RUNS: python3 autobrainstorm.py                        │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ LOAD PROJECT DATA (Once)                                    │
│ ├─ SQL: projects table → self.project                       │
│ ├─ SQL: characters table → self.characters                  │
│ ├─ SQL: scenes table → self.scenes (all 30)                 │
│ └─ SQL: writer_notes table → self.writer_notes              │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ BUILD STORY OUTLINE (Once, used for all scenes)             │
│ "PROJECT: The Proposal 2.0                                  │
│  LOGLINE: A demanding boss forces...                        │
│  CHARACTERS: Margaret (Protagonist), Andrew (Love Interest)"│
└─────────────────────────────────────────────────────────────┘
                          ↓
        ┌─────────────────┴─────────────────┐
        ↓                                   ↓
┌─────────────────┐              ┌─────────────────┐
│   SCENE 1       │              │   SCENE 2       │
│   (Bootstrap)   │              │   (Feed-Forward)│
└─────────────────┘              └─────────────────┘
        ↓                                   ↓
Get Surrounding Context                Get Surrounding Context
├─ Previous: None                      ├─ Previous: Scene 1 DELTA ✨
└─ Next: Scene 2 desc                  └─ Next: Scene 3 desc
        ↓                                   ↓
Build Prompt (Books)                   Build Prompt (Books)
├─ Metadata header                     ├─ Metadata header
├─ Golden-age def (40 tokens)          ├─ Golden-age def (40 tokens)
├─ Story outline                       ├─ Story outline
├─ Scene 1 context                     ├─ Scene 2 context
├─ Surrounding (no previous)           ├─ Surrounding (Scene 1 delta!)
└─ Active verb questions               └─ Active verb questions
        ↓                                   ↓
Query LightRAG (books bucket)          Query LightRAG (books bucket)
├─ Search screenplay theory            ├─ Search screenplay theory
├─ GPT-4o-mini synthesizes             ├─ GPT-4o-mini synthesizes
└─ Cohere reranks (optional)           └─ Cohere reranks (optional)
        ↓                                   ↓
Books Response (400-800 tokens)        Books Response (400-800 tokens)
        ↓                                   ↓
        ↓                                   ↓
[Repeat for Plays bucket]              [Repeat for Plays bucket]
        ↓                                   ↓
[Repeat for Scripts bucket]            [Repeat for Scripts bucket]
        ↓                                   ↓
        ↓                                   ↓
Synthesize (GPT-4o)                    Synthesize (GPT-4o)
├─ Receives all 3 responses            ├─ Receives all 3 responses
├─ "If disagree, prioritize clarity"   ├─ "If disagree, prioritize clarity"
├─ Generates unified blueprint         ├─ Generates unified blueprint
└─ Adds executive summary              └─ Adds executive summary
        ↓                                   ↓
Save to Database                       Save to Database
├─ scene_id=1, bucket='books'          ├─ scene_id=2, bucket='books'
├─ scene_id=1, bucket='plays'          ├─ scene_id=2, bucket='plays'
├─ scene_id=1, bucket='scripts'        ├─ scene_id=2, bucket='scripts'
└─ scene_id=1, bucket='all'            └─ scene_id=2, bucket='all'
        ↓                                   ↓
Generate Delta Summary                 Generate Delta Summary
(saved for Scene 2 to use)             (saved for Scene 3 to use)
        ↓                                   ↓
Display to User                        Display to User
✓ Scene 1: Opening Image               ✓ Scene 2: Status Quo
[Shows full blueprint]                 [Shows full blueprint]
        ↓                                   ↓
        └───────────────────────────────────┘
                          ↓
                    [Continue for Scenes 3-30...]
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ FINAL OUTPUT                                                 │
│ ✓ Completed: 30/30 scenes                                   │
│ Results saved to brainstorm_sessions table                  │
│                                                              │
│ DATABASE NOW CONTAINS:                                       │
│ - 120 brainstorm sessions (4 per scene × 30 scenes)         │
│ - 30 synthesized blueprints (ready for WRITE module)        │
│ - 30 individual expert analyses (for reference)             │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Mechanisms Explained

### 1. Feed-Forward (The Snowball Effect)

**Scene 1:**
- Context: Just original descriptions
- Output: Blueprint 1

**Scene 2:**
- Context: Original descriptions + Delta 1
- Output: Blueprint 2 (informed by Scene 1)

**Scene 3:**
- Context: Original descriptions + Delta 2 (which was informed by Delta 1)
- Output: Blueprint 3 (informed by Scenes 1-2)

**Scene 30:**
- Context: Original descriptions + Delta 29 (cumulative knowledge of 29 scenes)
- Output: Blueprint 30 (informed by ENTIRE narrative)

**Result:** By Scene 30, the system has **29 scenes of cumulative context**.

---

### 2. Delta Summary Compression

**Without Compression:**
- Scene 5 would receive Scene 4's full 2,000-token blueprint
- Scene 30 would receive Scene 29's full 2,500-token blueprint
- Total feed-forward: ~60,000 tokens

**With Compression:**
- Every scene receives a 250-token delta summary
- Focus: changes, momentum, beats, setup
- Total feed-forward: ~7,500 tokens

**Savings:** ~52,500 tokens ($0.80 at GPT-4o pricing)

---

### 3. Three-Expert Architecture

**Why Three Experts?**

- **Books** = Structural thinking (beats, arcs, mechanics)
- **Plays** = Psychological thinking (objectives, subtext, emotion)
- **Scripts** = Practical thinking (shots, pacing, execution)

**Why Not Just One LLM?**

Each expert queries a **different LightRAG bucket**:
- Books bucket contains: Save the Cat, Story, The Writer's Journey, screenplay craft books
- Plays bucket contains: Shakespeare, Molière, classical dramatic theory
- Scripts bucket contains: Actual romantic comedy screenplays

**Different source material = different perspectives**

---

### 4. Synthesis Layer

**Why Not Just Concatenate?**

GPT-4o synthesis:
- **Resolves conflicts:** If Books says 3 pages, Scripts says 5, synthesis picks based on "cinematic clarity"
- **Finds patterns:** "All three experts emphasize the power dynamic shift here..."
- **Attributes sources:** "Books expert identifies this as midpoint, Scripts recommends shooting as..."
- **Adds executive summary:** Quick TL;DR for scanning

---

## What You Get At The End

### Database Contains:

**120 Brainstorm Sessions:**
```sql
SELECT * FROM brainstorm_sessions WHERE scene_id = 5;

-- Returns 4 rows:
-- 1. bucket='books'   → Structure analysis (400-800 tokens)
-- 2. bucket='plays'   → Dramatic analysis (400-800 tokens)
-- 3. bucket='scripts' → Execution analysis (400-800 tokens)
-- 4. bucket='all'     → Synthesized blueprint (800-1200 tokens)
```

**30 Synthesized Blueprints** (bucket='all') ready for WRITE module to use!

---

## Performance Stats

**Per Scene:**
- 3 LightRAG queries (books, plays, scripts): ~30 seconds
- 3 Cohere reranks (optional): ~3 seconds
- 1 Delta summary generation: ~2 seconds
- 1 GPT-4o synthesis: ~10 seconds
- **Total: ~45-60 seconds per scene**

**Full 30-Scene Run:**
- **Total time: ~25-30 minutes**
- **Total cost: ~$2-3** (GPT-4o + GPT-4o-mini + Cohere)
- **Total tokens: ~375,000** (input + output)

---

## What Makes V2.0 Special

✅ **Feed-forward delta summaries** - Each scene builds on previous
✅ **Compressed prompts** - 78% reduction in golden-age definition
✅ **Active guidance** - "Propose", "Advise", "Recommend" (not "analyze")
✅ **Enforced formatting** - Bullet points, 5-7 per section, 400-800 tokens
✅ **Metadata tracking** - Version, timestamp, model for every output
✅ **Disagreement resolution** - "Prioritize cinematic clarity"
✅ **Executive summaries** - Quick scan of every scene
✅ **Expert attribution** - Know which expert said what

---

## Next Step: WRITE Module

The WRITE module will:
1. Load all 30 synthesized blueprints from database
2. Use them to write actual screenplay scenes
3. Maintain consistency across the full script
4. Reference specific blueprint guidance for each scene

**The blueprints are the bridge between brainstorming and writing!** 🎬
