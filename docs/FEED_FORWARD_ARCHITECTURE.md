# Feed-Forward Architecture

## Cumulative Context Building

Automated Brainstorm uses a **feed-forward mechanism** where each scene's synthesized blueprint becomes part of the context for the next scene.

This creates a **snowball effect** where scene analysis becomes progressively richer as more scenes are processed.

---

## How It Works

### Scene 1: Bootstrap Phase

**Input Context:**
- Story outline (project, logline, theme, characters)
- Scene 1 description (original)
- Previous scene: NONE
- Next scene: Scene 2 (original description)

**Processing:**
1. Query books bucket → Structure analysis
2. Query plays bucket → Dramatic analysis
3. Query scripts bucket → Execution analysis
4. Synthesize → **Scene 1 Blueprint** ✨

**Output:**
- Saves 4 brainstorm sessions to DB:
  - `scene_id=1, bucket_used='books'`
  - `scene_id=1, bucket_used='plays'`
  - `scene_id=1, bucket_used='scripts'`
  - `scene_id=1, bucket_used='all'` ← **BLUEPRINT**

---

### Scene 2: Feed-Forward Begins

**Input Context:**
- Story outline (same)
- Scene 2 description (original)
- **Previous scene: Scene 1 SYNTHESIZED BLUEPRINT** 🎯 ← **FEED-FORWARD!**
- Next scene: Scene 3 (original description)

**What's Different:**
Scene 2's prompts now include Scene 1's **complete blueprint** with:
- Structural Function
- Dramatic Beats
- Dialogue & Subtext
- Visual & Staging
- Character Psychology
- Golden-Age Execution Notes
- Pitfalls to Avoid

**Processing:**
1. Query books bucket → Analyzes Scene 2 with knowledge of Scene 1's detailed structure
2. Query plays bucket → Analyzes Scene 2 with knowledge of Scene 1's character dynamics
3. Query scripts bucket → Analyzes Scene 2 with knowledge of Scene 1's visual approach
4. Synthesize → **Scene 2 Blueprint** ✨

**Output:**
- Saves Scene 2's 4 brainstorm sessions
- Scene 2 blueprint now available for Scene 3

---

### Scene 3: Context Compounds

**Input Context:**
- Story outline (same)
- Scene 3 description (original)
- **Previous scene: Scene 2 SYNTHESIZED BLUEPRINT** 🎯
  - Which references Scene 1's beats/transitions
- Next scene: Scene 4 (original description)

**Cumulative Knowledge:**
- Scene 3 experts see Scene 2's full blueprint
- Scene 2's blueprint was informed by Scene 1's blueprint
- Each scene builds on ALL previous analysis

---

### Scene 15: Midpoint (Rich Context)

**Input Context:**
- Story outline (same)
- Scene 15 description (original)
- **Previous scene: Scene 14 SYNTHESIZED BLUEPRINT** 🎯
  - Scene 14 was informed by Scene 13
  - Scene 13 was informed by Scene 12
  - ... back to Scene 1
- Next scene: Scene 16 (original description)

**Expert Knowledge:**
By Scene 15, the experts have access to:
- 14 previous synthesized blueprints (via Scene 14's context)
- Complete understanding of story momentum
- Established character dynamics and arcs
- Visual and tonal patterns from earlier scenes
- Dramatic beats that have already landed

**Analysis Quality:**
Scene 15's analysis is **dramatically richer** than Scene 1's because it understands:
- What structural beats have already been hit
- How characters have evolved
- What emotional territory has been covered
- What needs to happen to maintain momentum

---

### Scene 30: Maximum Context

**Input Context:**
- Story outline (same)
- Scene 30 description (original)
- **Previous scene: Scene 29 SYNTHESIZED BLUEPRINT** 🎯
  - Informed by all 28 previous scenes
- Next scene: NONE (ending)

**Expert Knowledge:**
By Scene 30, the system has synthesized blueprints for **29 consecutive scenes**, creating a complete narrative understanding.

Scene 30's analysis can:
- Reference established character arcs
- Pay off setups from earlier scenes
- Maintain tonal consistency
- Deliver satisfying structural resolution
- Honor the cumulative emotional journey

---

## Technical Implementation

### Code Flow

```python
# Scene 2 processing
scene_2 = self.scenes[1]  # Scene number 2

# Get surrounding context
surrounding = self.get_surrounding_context(scene_2)
# ↓
# Calls _get_scene_blueprint(scene_1_id)
# ↓
# SQL: SELECT content FROM brainstorm_sessions
#      WHERE scene_id = 1 AND bucket_used = 'all'
# ↓
# Returns Scene 1's full synthesized blueprint
# ↓
surrounding['previous'] = f"""Scene 1: Opening Image

SYNTHESIZED BLUEPRINT:
## SCENE BLUEPRINT

### Structural Function
- Establishes protagonist's ordinary world
- Shows Margaret's power and control
- Sets up character flaw (coldness, control)

### Dramatic Beats
- Opens with Margaret commanding her empire
- Shows her treating Andrew as invisible
- Reveals her competence but lack of warmth
- Ends with her unaware of the storm coming

### Dialogue & Subtext
[Complete blueprint from Scene 1...]
"""

# This rich context is injected into Scene 2's expert prompts
```

---

## Feed-Forward Data Flow

```
Scene 1 Processing
├─ Query books/plays/scripts
├─ Synthesize blueprint
└─ Save to brainstorm_sessions (bucket_used='all')
         ↓
         │ [Stored in database]
         ↓
Scene 2 Processing
├─ Load Scene 1 blueprint from database ✨
├─ Inject into "Previous Scene" context
├─ Query books/plays/scripts (with Scene 1 knowledge)
├─ Synthesize blueprint (informed by Scene 1)
└─ Save to brainstorm_sessions
         ↓
         │ [Stored in database]
         ↓
Scene 3 Processing
├─ Load Scene 2 blueprint from database ✨
├─ Inject into "Previous Scene" context
├─ Query books/plays/scripts (with Scene 2 knowledge)
│   └─ Scene 2 blueprint references Scene 1
├─ Synthesize blueprint (informed by Scene 2)
└─ Save to brainstorm_sessions
         ↓
         │ [Continues...]
         ↓
Scene 30 Processing
├─ Load Scene 29 blueprint from database ✨
│   └─ Scene 29 was informed by Scene 28
│       └─ Scene 28 was informed by Scene 27
│           └─ ... back to Scene 1
├─ Inject into "Previous Scene" context
├─ Query books/plays/scripts (with full story knowledge)
├─ Synthesize blueprint (informed by entire narrative)
└─ Save to brainstorm_sessions
```

---

## Example: Scene 5 Prompt with Feed-Forward

### Without Feed-Forward (Old):
```
SURROUNDING SCENES:
Previous: Scene 4: Inciting Incident - Margaret learns she's being deported
Next: Scene 6: Debate - Andrew negotiates terms
```

### With Feed-Forward (New):
```
SURROUNDING SCENES:
Previous: Scene 4: Inciting Incident

SYNTHESIZED BLUEPRINT:
## SCENE BLUEPRINT

### Structural Function
- This is the inciting incident that disrupts Margaret's status quo
- Launches the central dramatic question: Will she avoid deportation?
- Forces Margaret into desperate action (the proposal)

### Dramatic Beats
- Opens with Margaret confidently navigating her day
- HR delivers the deportation notice
- Margaret's control shatters for the first time
- She realizes she has 24 hours to solve this
- Closes with her formulating the engagement plan

### Dialogue & Subtext
- Surface: Bureaucratic HR conversation about visa status
- Subtext: Margaret's entire identity is threatened
- Power dynamic: Margaret loses control for first time
- Wordplay: Legal jargon masks emotional devastation

### Visual & Staging
- Opens in Margaret's pristine office (control)
- HR arrives (disruption enters her space)
- Close-up on Margaret's face as news lands
- Visual: Her mask cracks briefly before she regains composure

### Character Psychology
- Margaret's objective: Maintain composure, find solution
- Tactic: Deny the severity, then problem-solve
- Obstacle: Immigration law is absolute
- Vulnerability: For first time, money and power can't fix this

### Golden-Age Execution Notes
- Use screwball pacing: Fast dialogue hiding emotional depth
- Physical comedy: Margaret's control showing cracks
- Sexual tension: None yet (pre-proposal)
- Reference: Similar to His Girl Friday's crisis setups

### Pitfalls to Avoid
- Don't make Margaret too sympathetic too quickly
- Don't overexplain the immigration stakes
- Keep her calculating, not panicked

Next: Scene 6: Debate - Andrew negotiates terms of the fake engagement
```

**Now Scene 5's experts can:**
- See that Scene 4 established Margaret's loss of control
- Understand that Scene 4 showed her first vulnerability
- Know that Scene 4 ended with her formulating the proposal plan
- Build Scene 5's proposal moment as a direct continuation
- Reference Scene 4's emotional and visual language

---

## Benefits of Feed-Forward

### 1. Narrative Continuity
Each scene understands what came before in **rich detail**, not just a one-sentence summary.

### 2. Character Arc Tracking
Experts can reference specific character moments, objectives, and vulnerabilities from previous blueprints.

### 3. Tonal Consistency
Visual style, dialogue approach, and comedic rhythm established in early scenes inform later scenes.

### 4. Beat Sheet Awareness
Structural experts see which beats have been hit, avoiding redundancy or missed opportunities.

### 5. Payoff Opportunities
Later scenes can reference specific setups from earlier blueprints (e.g., "callback to Scene 8's briefcase gag").

### 6. Snowball Quality Improvement
Scene 30's analysis is **exponentially richer** than Scene 1's because it has 29 scenes of context.

---

## Fallback Mechanism

```python
if prev_blueprint:
    # Use rich blueprint (preferred)
    prev_scene = f"Scene X: Title\n\nSYNTHESIZED BLUEPRINT:\n{prev_blueprint}"
else:
    # Fallback to original description
    prev_scene = f"Scene X: Title - {description}"
```

**Why This Matters:**
- First scene has no previous blueprint (fallback works)
- If a scene fails to process, subsequent scenes still work
- Graceful degradation ensures system never breaks

---

## Visual: Knowledge Accumulation

```
Scene 1:  [Original Description]
          ↓ Process ↓
          [Blueprint 1] ─────────────────────────────┐
                                                     ↓
Scene 2:  [Original Description] + [Blueprint 1]
          ↓ Process ↓
          [Blueprint 2] ─────────────────────┐
                                             ↓
Scene 3:  [Original] + [Blueprint 2]
                        (which includes Blueprint 1 knowledge)
          ↓ Process ↓
          [Blueprint 3] ─────────────┐
                                     ↓
...

Scene 30: [Original] + [Blueprint 29]
                        (which includes Blueprints 1-28 knowledge)
          ↓ Process ↓
          [Blueprint 30] ← Informed by entire narrative
```

---

## Real-World Example

### Scene 8 Blueprint (Already Processed):
```
### Character Psychology
- Margaret maintains icy exterior but shows micro-moments of humanity
- Andrew begins to see past her armor
- Sexual tension: First hint of physical awareness (hand touch during fake ring exchange)
```

### Scene 9 Prompt (Uses Scene 8 Blueprint):
```
SURROUNDING SCENES:
Previous: Scene 8: False Victory

SYNTHESIZED BLUEPRINT:
[Full Scene 8 blueprint including the character psychology above]

Next: Scene 10: Fun and Games - Margaret and Andrew navigate family dynamics
```

### Scene 9 Expert Analysis (Books Bucket):
```
## STRUCTURAL ANALYSIS
This scene should build on Scene 8's micro-moments of humanity. Since the
previous scene established their first physical touch and hint of chemistry,
Scene 9 should escalate that awareness while maintaining the class conflict...
```

**The expert referenced Scene 8's specific detail** (hand touch, micro-moments) because it had the **full blueprint**, not just "False Victory - They celebrate getting engaged."

---

## Key Insight

**Feed-forward transforms the system from:**
- 30 independent scene analyses →
- **1 continuous narrative construction**

Each scene isn't analyzed in isolation - it's analyzed as **part of a growing story** where previous decisions inform future choices.

This is how real writers work: each scene is written with awareness of what came before. Now the AI system does the same! 🎬
