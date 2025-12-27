# LIZZY: The Thesis Implementation

Original framework built for the master's thesis:
> "Automating the Screenplay: The Creative and Technical Viability of AI in Screenwriting"

---

## Theoretical Foundation

### Kozmetsky's Creative and Innovative Management (CIM) Framework

The system was designed around three core components:

1. **Drivers** — Technological and creative factors shaping AI behavior
2. **Interactions (Talent)** — Dynamic interplay between human creativity and AI suggestions
3. **Feedback Loops** — Iterative cycles of input, adaptation, and refinement

### AI as Pseudo-Participant

The thesis positioned AI tools in dual roles:
- **Technological Artifacts** — Products of training data and algorithmic design
- **Active Agents** — Dynamic participants that generate content and influence decisions

---

## The Test Case

**Source Material:** William Shakespeare's *The Two Noble Kinsmen* (co-written with John Fletcher)

**Adaptation Goal:** Modern romantic comedy screenplay

**Why Shakespeare:**
- Strong three-act/five-act structures that map to modern romcom
- Pioneered romcom tropes (enemies to lovers, mistaken identity, love triangles)
- Mastery of witty, rhythmic dialogue
- Complex character dynamics
- Lesser-known play avoids bias from familiar adaptations

---

## Framework Architecture

### Phase 1: Start.py
**Purpose:** Project initialization

- Create project directory
- Initialize SQLite database
- Set up file structure for exports

### Phase 2: Intake.py
**Purpose:** Structured data collection

**Character Intake:**
- Name, role, personality
- Flaws, arcs, relationships
- Backstory elements

**Scene Breakdown:**
- 30-scene beat sheet
- Act structure (Acts 1-3)
- Scene descriptions, tone, characters involved

**Writer Notes:**
- Logline
- Theme
- Tone/comps
- Braindump ideas

### Phase 3: Brainstorm.py
**Purpose:** Knowledge graph consultation for scene blueprints

**Three Expert Buckets (LightRAG):**

| Bucket | Content | Expertise |
|--------|---------|-----------|
| `books/` | Screenwriting craft books | Structure, beats, pacing |
| `plays/` | Complete Shakespeare | Dialogue, dramatic patterns, subtext |
| `scripts/` | Selected romcom screenplays | Visual storytelling, execution |

**Process per scene:**
1. Query all three buckets with scene context
2. Get expert perspective from each domain
3. Synthesize insights into actionable blueprint
4. Save to `brainstorm_sessions` table

**Condensed Brainstorming Prompts (from thesis Table 4.1):**
- Structure expert: Plot pyramid, subplot integration, pacing
- Dialogue expert: Character voice, subtext, emotional beats
- Visual expert: Comparable scenes, execution patterns

### Phase 4: Write.py
**Purpose:** Prose generation from blueprints

**Input per scene:**
- Scene description (from intake)
- Brainstorm blueprint (from brainstorm)
- Previous scene draft (feed-forward continuity)
- Character information
- Writer notes

**Output:**
- 700-900 word screenplay prose
- Golden-era romcom tone (When Harry Met Sally, You've Got Mail)
- Stored with version control, word count, token usage

---

## Database Schema

```
project.db
├── projects          # Metadata
├── characters        # Name, role, arc, flaw, relationships
├── scenes            # Number, title, description, tone
├── brainstorm_sessions  # Scene blueprints from RAG
├── scene_drafts      # Versioned prose output
└── writer_notes      # Logline, theme, tone, comps
```

---

## Key Thesis Findings

### What Worked

1. **Structured prompt engineering** outperformed vanilla LLM prompting
2. **LightRAG hybrid queries** provided relevant domain expertise
3. **Feed-forward context** (previous scene → current scene) maintained continuity
4. **Character intake upfront** improved consistency across scenes
5. **Beat sheet structure** gave AI clear narrative guardrails

### What Needed Improvement

1. **Memory fragmentation** — State split across phases, no continuous thread
2. **Batch processing** — Not interactive, couldn't refine in real-time
3. **Directive parsing** — Regex-based state tracking was fragile
4. **Phase transitions** — User had to exit and re-enter between stages
5. **Single voice** — Experts only appeared in brainstorm, not throughout

---

## Thesis Scripts Produced

| Script | Method | Purpose |
|--------|--------|---------|
| TNK_0 | Raw GPT-4o, no framework | Baseline/pilot |
| TNK_A | GPT-4o-mini + beat sheet + characters | Benchmark |
| TNK_B | GPT-4o-mini + framework (no RAG) | Test structure alone |
| TNK_C | Full framework with LightRAG | Final evaluation |

**Evaluation criteria:**
- Narrative coherence
- Character consistency
- Dialogue authenticity (subtext, wit, emotional depth)
- Structural integrity
- Genre alignment (romcom conventions)

---

## The Gap That Became lizzy_3

The thesis proved the **concept** works. But the **experience** was fragmented:

```
User workflow in thesis LIZZY:

1. Run start.py → create project
2. Run intake.py → enter all characters, scenes manually
3. Run brainstorm.py → wait for batch processing
4. Run write.py → wait for batch processing
5. Run export.py → get final screenplay

Total: 5 separate CLI invocations, no conversation, no real-time refinement
```

**lizzy_3 vision:**

```
User workflow in lizzy_3:

1. Start chatting with Syd
2. Develop idea conversationally
3. Experts chime in when relevant
4. Brainstorm and write happen inline
5. Export when ready

Total: One continuous conversation
```

---

## Theoretical Contribution

The thesis contributed to the field by demonstrating that:

> "AI can function as an effective collaborative screenwriting partner when equipped with structured memory, domain expertise retrieval, and iterative feedback mechanisms — not as a replacement for human creativity, but as an augmentation of it."

This positions AI as a **pseudo-participant** in the creative process, aligning with Actor-Network Theory's concept of non-human agency in social phenomena.
