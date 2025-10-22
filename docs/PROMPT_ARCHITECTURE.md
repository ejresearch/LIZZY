# Automated Brainstorm Prompt Architecture

## Overview

The Automated Brainstorm module uses a **four-layer prompt system** to generate comprehensive scene guidance for golden-age romantic comedies:

1. **Golden-Age Definition** - Shared context across all buckets
2. **Bucket-Specific Expert Prompts** - Three specialized perspectives
3. **Synthesis Prompt** - Unified scene blueprint
4. **Structured Output** - Consistent, actionable format

---

## Layer 1: Golden-Age Romantic Comedy Definition

All prompts begin with a consistent definition of the target genre:

```
GOLDEN-AGE ROMANTIC COMEDY DEFINITION:
The sophisticated screwball and romantic comedies of 1930s-1950s Hollywood, characterized by:
- Witty, rapid-fire dialogue with subtext and wordplay
- Class conflict or opposing worldviews driving romantic tension
- Physical comedy and slapstick integrated with verbal wit
- Strong, independent protagonists (especially female leads)
- Misunderstandings and mistaken identities as plot engines
- Sophisticated sexual tension within Production Code constraints
- Happy endings that unite love and equality

Reference films: His Girl Friday (1940), The Philadelphia Story (1940),
It Happened One Night (1934), Bringing Up Baby (1938), Ball of Fire (1941)
```

This ensures all three expert buckets understand the stylistic target.

---

## Layer 2: Bucket-Specific Expert Prompts

Each bucket receives **tailored questions** that play to its domain expertise:

### Books Bucket (Structure Expert)

**Focus:** Screenplay architecture, beat engineering, act mechanics

**Sections:**
- **Structural Analysis** - Three-act positioning, beat sheet function, plot advancement
- **Beat Engineering** - Essential dramatic beats, turning points, tension/release
- **Genre Mechanics** - Romcom conventions, romance/comedy balance, obstacles
- **Pacing & Transitions** - Scene length, transitions, momentum

**Query Style:** Analytical, focused on "where" in the structure and "why" this beat exists

---

### Plays Bucket (Dramatic Theory Expert)

**Focus:** Theatrical craft, dialogue, character psychology

**Sections:**
- **Dialogue Dynamics** - Subtext, verbal sparring, power shifts, wordplay
- **Character Psychology** - Objectives, tactics, obstacles, emotional masking
- **Dramatic Technique** - Irony, secrets, conflict, Aristotelian principles
- **Emotional Architecture** - Character journeys, audience guidance, vulnerability
- **Stage Business & Action** - Physical actions, body language, symbolic props

**Query Style:** Psychological, focused on "what characters want" and "how they interact"

---

### Scripts Bucket (Execution Expert)

**Focus:** Cinematic craft, visual storytelling, modern execution

**Sections:**
- **Visual Storytelling** - Opening shots, camera work, visual comedy, location
- **Pacing & Rhythm** - Tempo, cuts, comedic timing, film rhythm
- **Romantic Comedy Tropes** - Classic beats, freshening familiar moments, homage vs. originality
- **Dialogue Execution** - Speed, overlapping dialogue, pauses, screwball energy
- **Performance Notes** - Tone, physical comedy, restraint, chemistry
- **Practical Considerations** - Pitfalls, examples, technical/budget concerns

**Query Style:** Practical, focused on "how to execute" and "what works on screen"

---

## Layer 3: Synthesis Prompt

The synthesis prompt combines all three expert perspectives into a **unified scene blueprint**.

### Synthesis Approach

**Role:** Master screenplay consultant integrating structure + dramatic craft + execution

**Input:** Three expert analyses (books, plays, scripts)

**Output Format:**
```
## SCENE BLUEPRINT

### Structural Function
- Overall story accomplishment
- Beat/turning point identification
- Plot/character arc advancement

### Dramatic Beats
- Opening state
- Key turning points
- Closing state
- Transition

### Dialogue & Subtext
- Tone and pacing
- Surface vs. hidden meaning
- Wordplay opportunities
- Power dynamics

### Visual & Staging
- Opening image
- Visual/physical comedy
- Camera approach
- Location utilization

### Character Psychology
- Objectives and tactics
- Emotional journey
- Vulnerability moments
- Relationship dynamics

### Golden-Age Execution Notes
- Screwball/romcom tropes
- Wit and physical comedy balance
- Sexual tension notes
- Classic film inspirations

### Pitfalls to Avoid
- Common mistakes
- What could fall flat
- Tonal concerns
```

**Key Instruction:** "Be SPECIFIC, CONCRETE, and ACTIONABLE. Reference the expert insights directly when synthesizing."

---

## Layer 4: Context Injection

Every prompt receives rich context:

### Story Context
- Project name and genre
- Logline, theme, tone, comps (from writer_notes)
- Character roster with descriptions
- Scene count

### Scene Context
- Scene number, title, act
- Scene description
- Characters in scene

### Surrounding Context
- Previous scene summary
- Next scene summary

This ensures experts understand:
1. **Where** the scene sits in the story
2. **What** came before and what comes next
3. **Who** the characters are and what they want
4. **Why** this scene exists

---

## Prompt Flow Example

For **Scene 5: The Meet-Cute**:

### Step 1: Query Books Bucket
```
You are a SCREENPLAY STRUCTURE AND CRAFT EXPERT...

[Golden-age definition]
[Story context + Scene 5 details + Surrounding scenes]

As a structure expert, analyze this scene's DRAMATIC ARCHITECTURE:
## STRUCTURAL ANALYSIS
## BEAT ENGINEERING
## GENRE MECHANICS
## PACING & TRANSITIONS

Provide bullet points with specific, actionable guidance.
```

**Books Response:** Structural analysis focused on beat positioning, act mechanics

---

### Step 2: Query Plays Bucket
```
You are a CLASSICAL DRAMATIC THEORY EXPERT...

[Golden-age definition]
[Story context + Scene 5 details + Surrounding scenes]

As a dramatic theory expert, analyze this scene's THEATRICAL CRAFT:
## DIALOGUE DYNAMICS
## CHARACTER PSYCHOLOGY
## DRAMATIC TECHNIQUE
## EMOTIONAL ARCHITECTURE
## STAGE BUSINESS & ACTION

Provide bullet points with specific, actionable guidance.
```

**Plays Response:** Theatrical analysis focused on dialogue, subtext, psychology

---

### Step 3: Query Scripts Bucket
```
You are a MODERN ROMANTIC COMEDY EXECUTION EXPERT...

[Golden-age definition]
[Story context + Scene 5 details + Surrounding scenes]

As an execution expert, analyze this scene's CINEMATIC CRAFT:
## VISUAL STORYTELLING
## PACING & RHYTHM
## ROMANTIC COMEDY TROPES
## DIALOGUE EXECUTION
## PERFORMANCE NOTES
## PRACTICAL CONSIDERATIONS

Provide bullet points with specific, actionable guidance.
```

**Scripts Response:** Execution analysis focused on visual storytelling, performance

---

### Step 4: Synthesize All Three
```
You are a MASTER SCREENPLAY CONSULTANT synthesizing expert advice...

[Golden-age definition]
[Story context + Scene 5 details + Surrounding scenes]

THREE EXPERT CONSULTATIONS:
=== BOOKS EXPERT ANALYSIS ===
[Books response]

=== PLAYS EXPERT ANALYSIS ===
[Plays response]

=== SCRIPTS EXPERT ANALYSIS ===
[Scripts response]

---

Synthesize these three expert perspectives into a comprehensive scene blueprint
using the exact format specified.
```

**Synthesis Output:** Unified scene blueprint with 7 structured sections

---

## Database Storage

Each scene generates **4 brainstorm sessions**:

1. `bucket_used: "books"` - Structure expert analysis
2. `bucket_used: "plays"` - Dramatic theory analysis
3. `bucket_used: "scripts"` - Execution expert analysis
4. `bucket_used: "all"` - Synthesized scene blueprint

All linked to `scene_id` and tagged with `tone: "Golden Age Romantic Comedy"`

---

## Design Principles

1. **Specialization** - Each bucket focuses on its domain expertise
2. **Context-Awareness** - Full story context + surrounding scenes inform every query
3. **Structured Output** - Consistent bullet-point format for parsing and synthesis
4. **Synthesis Over Summation** - GPT-4o integrates insights, doesn't just concatenate
5. **Actionability** - Every output is practical guidance for writing, not abstract theory
6. **Genre Fidelity** - Golden-age romcom definition anchors all analysis

---

## Benefits of This Architecture

✅ **Comprehensive Coverage** - Structure + Drama + Execution = Complete scene blueprint
✅ **Expert Specialization** - Each bucket contributes unique perspective
✅ **Contextual Relevance** - Surrounding scenes prevent isolated analysis
✅ **Consistent Output** - Structured format enables downstream synthesis
✅ **Genre-Specific** - Golden-age romcom style guides all recommendations
✅ **Reusable Components** - Individual bucket analyses saved for reference
✅ **Scalable** - Same architecture works for all 30 scenes

---

## Future Enhancements

- Add **Tone Variations** (screwball vs. sophisticated vs. slapstick)
- Include **Character-Specific Queries** for ensemble scenes
- Add **Revision Prompts** for iterative refinement
- Integrate **Example Scenes** from reference films in prompts
- Support **Multi-Genre Blends** (romcom-thriller, romcom-sci-fi)
