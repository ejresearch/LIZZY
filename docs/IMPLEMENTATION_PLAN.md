# Brainstorm Improvements - Implementation Plan

## Overview
Implementing 18 major improvements across Interactive and Automated Brainstorm modules, plus 8 priority enhancements.

**Total Improvements:** 26
**Estimated Implementation Time:** 6-8 hours
**Complexity:** Medium-High

---

## Phase 1: Interactive Brainstorm (Improvements 1-5)

### ✅ 1. Scene-Specific Mode
**Files to Modify:** `lizzy/interactive_brainstorm.py`

**Changes:**
```python
# Add to InteractiveBrainstorm class
self.focused_scene = None  # Track which scene we're focused on

def enter_scene_focus_mode(self, scene_number: int):
    """Lock conversation to specific scene."""
    scene = next((s for s in self.scenes if s['scene_number'] == scene_number), None)
    if scene:
        self.focused_scene = scene
        console.print(f"[cyan]Now focusing on Scene {scene_number}: {scene['title']}[/cyan]")

        # Load blueprint if it exists
        blueprint = self._get_scene_blueprint(scene['id'])
        if blueprint:
            console.print("[dim]Existing blueprint loaded for context[/dim]")

def exit_scene_focus_mode(self):
    """Return to project-wide queries."""
    self.focused_scene = None
    console.print("[cyan]Exited scene focus mode[/cyan]")

def enhance_query_with_context(self, user_query: str, ...):
    # MODIFY: If focused_scene is set, inject scene-specific context
    if self.focused_scene:
        enhanced_parts.append(f"FOCUSED SCENE: Scene {self.focused_scene['scene_number']}: {self.focused_scene['title']}")
        enhanced_parts.append(f"Description: {self.focused_scene['description']}")

        # Load blueprint if exists
        blueprint = self._get_scene_blueprint(self.focused_scene['id'])
        if blueprint:
            enhanced_parts.append(f"EXISTING BLUEPRINT:\n{blueprint[:500]}...")  # Truncate
```

**New Commands in Conversation Mode:**
- `/focus 5` - Focus on Scene 5
- `/unfocus` - Return to project-wide
- `/blueprint` - Show focused scene's blueprint (if exists)

**Impact:** Massively improves relevance of answers

---

### ✅ 2. Bucket Comparison Mode
**Files to Modify:** `lizzy/interactive_brainstorm.py`

**Changes:**
```python
async def query_buckets_comparison(self, query: str, buckets: List[str]) -> Dict:
    """Query all buckets and return side-by-side comparison."""
    results = await self.query_buckets(query, buckets, mode="hybrid")

    # Don't synthesize - keep separate
    return {
        'query': query,
        'books': next((r for r in results if r['bucket'] == 'books'), None),
        'plays': next((r for r in results if r['bucket'] == 'plays'), None),
        'scripts': next((r for r in results if r['bucket'] == 'scripts'), None)
    }

def display_comparison(self, comparison: Dict):
    """Display side-by-side bucket comparison."""
    from rich.columns import Columns

    panels = []
    for bucket in ['books', 'plays', 'scripts']:
        if comparison[bucket]:
            panel = Panel(
                Markdown(comparison[bucket]['response']),
                title=f"{bucket.upper()} Expert",
                border_style="cyan"
            )
            panels.append(panel)

    console.print(Columns(panels))
```

**New Command:**
- `/compare <question>` - Show answers from all buckets side-by-side

**Impact:** See different perspectives clearly

---

### ✅ 3. Export to Blueprint Format
**Files to Modify:** `lizzy/interactive_brainstorm.py`

**Changes:**
```python
async def export_conversation_to_blueprint(self, scene_number: int) -> str:
    """Convert conversation insights into structured blueprint."""

    # Build prompt for GPT-4o
    conversation_text = "\n\n".join([
        f"{'User' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}"
        for msg in self.conversation_history
    ])

    prompt = f"""Convert this brainstorming conversation into a structured scene blueprint.

CONVERSATION:
{conversation_text}

OUTPUT FORMAT (use these exact sections):

## SCENE_BLUEPRINT

### EXECUTIVE_SUMMARY
[3-5 sentences summarizing the conversation insights]

### STRUCTURAL_FUNCTION
- [Key structural points from conversation]

### DRAMATIC_BEATS
- [Beats identified in conversation]

[... all sections from Automated Brainstorm format ...]

Extract insights from the conversation and organize them into this structure.
"""

    client = AsyncOpenAI()
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5
    )

    return response.choices[0].message.content

def save_as_blueprint(self, scene_number: int, blueprint: str):
    """Save conversation-derived blueprint to database."""
    scene = next((s for s in self.scenes if s['scene_number'] == scene_number), None)
    if not scene:
        return False

    with self.db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO brainstorm_sessions (scene_id, tone, bucket_used, content)
            VALUES (?, ?, ?, ?)
        """, (scene['id'], 'Interactive Conversation', 'all', blueprint))
        conn.commit()

    return True
```

**New Commands:**
- `/export` - Convert conversation to blueprint for focused scene
- `/export 5` - Convert conversation to blueprint for Scene 5

**Impact:** Bridges Interactive ↔ Automated workflows

---

### ✅ 4. Query History
**Files to Modify:** `lizzy/interactive_brainstorm.py`

**Changes:**
```python
# Add to __init__
self.query_history = []  # Track all queries

# Modify conversation loop
user_input = Prompt.ask("\n[bold cyan]You[/bold cyan]")

# Save to history
self.query_history.append({
    'timestamp': datetime.now(),
    'query': user_input,
    'buckets': self.current_buckets.copy()
})

# New commands
if user_input.lower() == '/history':
    self._show_query_history()
    continue

if user_input.lower().startswith('/rerun '):
    index = int(user_input.split()[1]) - 1
    if 0 <= index < len(self.query_history):
        user_input = self.query_history[index]['query']
        console.print(f"[dim]Re-running: {user_input}[/dim]")

def _show_query_history(self):
    """Display recent queries."""
    table = Table(title="Query History")
    table.add_column("#", style="dim")
    table.add_column("Time", style="cyan")
    table.add_column("Query")

    for i, query in enumerate(self.query_history[-10:], 1):  # Last 10
        table.add_row(
            str(i),
            query['timestamp'].strftime("%H:%M"),
            query['query'][:60] + ("..." if len(query['query']) > 60 else "")
        )

    console.print(table)
```

**New Commands:**
- `/history` - Show last 10 queries
- `/rerun 3` - Re-run query #3 from history

**Impact:** Easy to revisit previous questions

---

### ✅ 5. Suggested Questions
**Files to Modify:** `lizzy/interactive_brainstorm.py`

**Changes:**
```python
async def generate_follow_up_questions(self, query: str, response: str) -> List[str]:
    """Generate 3 suggested follow-up questions."""
    prompt = f"""Based on this Q&A, suggest 3 natural follow-up questions a screenwriter might ask.

QUERY: {query}
RESPONSE: {response[:500]}...

Provide 3 specific, actionable follow-up questions (one per line, no numbering):
"""

    client = AsyncOpenAI()
    result = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=150
    )

    questions = result.choices[0].message.content.strip().split('\n')
    return [q.strip('- ') for q in questions if q.strip()]

# After displaying response
suggestions = await self.generate_follow_up_questions(user_input, conversational_response)

console.print("\n[dim]You might also ask:[/dim]")
for i, suggestion in enumerate(suggestions, 1):
    console.print(f"[dim]{i}. {suggestion}[/dim]")
console.print("[dim]Type 1/2/3 to ask, or your own question:[/dim]")

# In conversation loop, check for numeric input
if user_input.isdigit() and 1 <= int(user_input) <= 3:
    user_input = suggestions[int(user_input) - 1]
    console.print(f"[cyan]You: {user_input}[/cyan]")
```

**Impact:** Helps users explore deeper without getting stuck

---

## Phase 2: Automated Brainstorm (Improvements 14-18)

### ✅ 14. Resume from Scene N
**Files to Modify:** `lizzy/automated_brainstorm.py`

**Changes:**
```python
async def run_batch_processing(self, start_from: int = 1) -> None:
    """Run automated brainstorming for scenes starting from start_from."""

    # Filter scenes
    scenes_to_process = [s for s in self.scenes if s['scene_number'] >= start_from]

    console.print(f"\n[bold]Processing {len(scenes_to_process)} scenes (starting from Scene {start_from})...[/bold]\n")

    # Rest of processing...

# In main():
if Confirm.ask("Resume from a specific scene?", default=False):
    start_scene = int(Prompt.ask("Start from scene number", default="1"))
else:
    start_scene = 1

await brainstorm.run_batch_processing(start_from=start_scene)
```

**Impact:** Saves time and money on partial re-runs

---

### ✅ 15. Selective Re-Generation
**Files to Modify:** `lizzy/automated_brainstorm.py`

**Changes:**
```python
async def regenerate_scenes(self, scene_numbers: List[int]) -> None:
    """Regenerate specific scenes only."""

    scenes_to_regen = [s for s in self.scenes if s['scene_number'] in scene_numbers]

    console.print(f"[yellow]Regenerating scenes: {', '.join(map(str, scene_numbers))}[/yellow]")
    console.print("[yellow]This will overwrite existing blueprints for these scenes.[/yellow]")

    if not Confirm.ask("Continue?"):
        return

    # Process scenes
    with Progress(...) as progress:
        task = progress.add_task("Regenerating...", total=len(scenes_to_regen))

        for scene in scenes_to_regen:
            result = await self.process_scene(scene, progress, task)
            results.append(result)

            if result['success']:
                self.display_scene_result(result)

# In main():
console.print("[1] Process all scenes")
console.print("[2] Resume from scene N")
console.print("[3] Regenerate specific scenes")

choice = Prompt.ask("Choose option", choices=["1", "2", "3"])

if choice == "3":
    scene_nums = Prompt.ask("Scene numbers (comma-separated, e.g., 5,12,18)")
    scenes = [int(n.strip()) for n in scene_nums.split(',')]
    await brainstorm.regenerate_scenes(scenes)
```

**Impact:** Surgical updates without full re-run

---

### ✅ 16. Confidence Scores
**Files to Modify:** `lizzy/automated_brainstorm.py`

**Changes:**
```python
def calculate_expert_agreement(self, bucket_results: List[Dict]) -> Dict[str, float]:
    """Calculate confidence based on expert agreement."""

    # Extract sections from each expert response
    sections = ['STRUCTURAL', 'DIALOGUE', 'VISUAL', 'CHARACTER']
    scores = {}

    for section in sections:
        # Simple heuristic: length similarity indicates agreement
        # If all experts wrote similar amounts, they likely agree
        lengths = []
        for result in bucket_results:
            # Count mentions of section keywords
            count = result['response'].lower().count(section.lower())
            lengths.append(count)

        # Calculate variance (low variance = high agreement)
        if lengths:
            avg = sum(lengths) / len(lengths)
            variance = sum((x - avg) ** 2 for x in lengths) / len(lengths)
            # Convert to 0-1 score (low variance = high score)
            score = max(0, min(1, 1 - (variance / (avg + 1))))
            scores[section] = score

    return scores

# In synthesize_expert_insights, add confidence scores
scores = self.calculate_expert_agreement(bucket_results)

# Add to synthesis prompt
score_text = "\n".join([f"{section}: {score:.2f}" for section, score in scores.items()])

system_prompt += f"\n\nEXPERT AGREEMENT SCORES:\n{score_text}\n(1.0 = perfect agreement, 0.0 = strong disagreement)\n"

# Display in results
console.print(f"\n[dim]Confidence Scores:[/dim]")
for section, score in scores.items():
    color = "green" if score > 0.7 else "yellow" if score > 0.4 else "red"
    console.print(f"[{color}]{section}: {score:.2f}[/{color}]")
```

**Impact:** Know which sections need human review

---

### ✅ 17. Preview Mode
**Files to Modify:** `lizzy/automated_brainstorm.py`

**Changes:**
```python
def preview_scene_prompts(self, scene_number: int):
    """Show what prompts will be sent for a scene."""

    scene = next((s for s in self.scenes if s['scene_number'] == scene_number), None)
    if not scene:
        console.print("[red]Scene not found[/red]")
        return

    # Build prompts (but don't send)
    books_prompt = self.build_expert_query(scene, "books")
    plays_prompt = self.build_expert_query(scene, "plays")
    scripts_prompt = self.build_expert_query(scene, "scripts")

    # Display
    console.print(Panel(books_prompt, title="Books Prompt Preview", border_style="cyan"))
    console.print(f"\n[dim]Token estimate: ~{len(books_prompt.split()) * 1.3:.0f} tokens[/dim]\n")

    if Confirm.ask("Show Plays prompt?"):
        console.print(Panel(plays_prompt, title="Plays Prompt Preview", border_style="cyan"))

    if Confirm.ask("Show Scripts prompt?"):
        console.print(Panel(scripts_prompt, title="Scripts Prompt Preview", border_style="cyan"))

# In main():
if Confirm.ask("Preview Scene 1 prompts before processing?", default=False):
    brainstorm.preview_scene_prompts(1)
    if not Confirm.ask("Proceed with processing?"):
        sys.exit(0)
```

**Impact:** Catch prompt issues before expensive run

---

### ✅ 18. Budget Estimator
**Files to Modify:** `lizzy/automated_brainstorm.py`

**Changes:**
```python
def estimate_cost_and_time(self, num_scenes: int) -> Dict:
    """Estimate cost and processing time."""

    # Token estimates (based on current prompts)
    tokens_per_scene = {
        'input': 3500,   # 3 expert prompts + synthesis
        'output': 4000,  # 3 expert responses + synthesis
        'delta': 350     # Delta summary generation
    }

    total_input = tokens_per_scene['input'] * num_scenes
    total_output = tokens_per_scene['output'] * num_scenes
    total_delta = tokens_per_scene['delta'] * (num_scenes - 1)  # No delta for Scene 1

    # Pricing (as of Jan 2025)
    gpt4o_input_cost = (total_input + total_delta) / 1_000_000 * 2.50  # $2.50/1M input
    gpt4o_output_cost = total_output / 1_000_000 * 10.00  # $10/1M output
    gpt4o_mini_cost = (total_input * 0.5) / 1_000_000 * 0.15  # LightRAG uses mini

    total_cost = gpt4o_input_cost + gpt4o_output_cost + gpt4o_mini_cost

    # Time estimate (45-60 sec per scene)
    time_minutes = (num_scenes * 52.5) / 60  # Average 52.5 sec per scene

    return {
        'num_scenes': num_scenes,
        'total_tokens': total_input + total_output + total_delta,
        'estimated_cost': total_cost,
        'estimated_time_minutes': time_minutes,
        'cost_per_scene': total_cost / num_scenes
    }

# In main():
estimate = brainstorm.estimate_cost_and_time(len(existing_scenes))

console.print(Panel.fit(
    f"[bold]Cost & Time Estimate[/bold]\n\n"
    f"Scenes to process: {estimate['num_scenes']}\n"
    f"Estimated cost: ${estimate['estimated_cost']:.2f}\n"
    f"Estimated time: {estimate['estimated_time_minutes']:.1f} minutes\n"
    f"Cost per scene: ${estimate['cost_per_scene']:.3f}",
    border_style="yellow"
))

if not Confirm.ask("\nProceed with processing?"):
    sys.exit(0)
```

**Impact:** No surprises on API bill

---

## Phase 3: Priority Improvements (Top 8)

### Implementation continues in next message due to length...

Would you like me to:
1. Implement these 18 improvements now (will take multiple messages)
2. Prioritize just the top 5 most impactful
3. Create implementation scripts you can review first

What's your preference?
