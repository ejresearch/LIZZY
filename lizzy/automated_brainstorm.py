"""
Automated Brainstorm - Batch scene generation with expert knowledge graph consultation.
"""

import asyncio
import os
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import openai_embed
from openai import AsyncOpenAI
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.markdown import Markdown
from .database import Database
from .reranker import CohereReranker

console = Console()


# Custom GPT-5-mini completion function for LightRAG
async def gpt_5_1_complete(
    prompt: str,
    system_prompt: str = None,
    history_messages: list = None,
    **kwargs
) -> str:
    """GPT-5.1 completion function compatible with LightRAG."""
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    if history_messages:
        messages.extend(history_messages)
    messages.append({"role": "user", "content": prompt})

    response = await client.chat.completions.create(
        model="gpt-5.1",
        messages=messages,
        temperature=kwargs.get("temperature", 0.7),
        max_completion_tokens=kwargs.get("max_tokens", 2000)
    )

    return response.choices[0].message.content


class AutomatedBrainstorm:
    """
    Batch process all 30 scenes with expert knowledge graph consultation.

    For each scene:
    1. Query all three buckets (books, plays, scripts)
    2. Get expert perspective from each bucket
    3. Synthesize insights into actionable scene guidance
    4. Save to brainstorm_sessions table
    """

    def __init__(self, db_path: Path):
        """
        Initialize Automated Brainstorm.

        Args:
            db_path: Path to project database
        """
        self.db_path = db_path
        self.db = Database(db_path)
        self.project = None
        self.characters = []
        self.scenes = []
        self.writer_notes = None

        # Buckets - always use all three
        self.bucket_dir = Path("./rag_buckets")
        self.buckets = ["books", "plays", "scripts"]

        # Initialize reranker
        self.reranker = CohereReranker()

        # IMPROVEMENT #16: Store confidence scores
        self.scene_confidence_scores = {}

        # Cached context (built once in load_project_context)
        self._story_outline = None

        # Romantic comedy structural framework
        self._romcom_framework = """ROMANTIC COMEDY FRAMEWORK:
(Draw from these loosely as inspiration, not as rigid requirements)

TONE: Warm, lighthearted, grounded but aspirational. Real emotions in slightly heightened worlds.
Cozy and romantic. Stakes feel enormous but are really about identity and connection.
The audience thinks: "That could be me, if my life were a little more magical."

STRUCTURE (common patterns):
- Two protagonists with complementary flaws who resist connection
- Central question: Will they end up together? (audience knows yes, tension is how)
- Arc: Meet → Resist → Connect → Crisis (all seems lost) → Realization → Union
- The grand gesture or public declaration
- Racing to catch them before it's too late

COMEDY SOURCES (mix and match):
- Situational irony and misunderstanding
- Witty banter and verbal sparring
- Relatable awkwardness and vulnerability
- Fish-out-of-water moments
- The well-meaning but chaotic best friend
- Embarrassing family or coworkers
- Plans that go spectacularly wrong
- Overheard conversations, wrong conclusions

ROMANCE SOURCES (moments to build):
- Vulnerability and emotional honesty
- Small moments of recognition and care
- Transformation through love (becoming who they're meant to be)
- The almost-kiss, the loaded glance, the thing left unsaid
- Helping each other without being asked
- Seeing each other clearly when no one else does
- The quiet moment after the chaos
- Rain, rooftops, string lights, golden hour

EMOTIONAL ENGINE (internal and external):
- Internal fears: not good enough, don't deserve love, can't change, fear of rejection
- External obstacles: timing, circumstances, rival, career vs. love, geography, secrets
- The lie they tell themselves vs. the truth they need to learn
- What they want vs. what they need
- Pride getting in the way"""

        # Reusable LightRAG instances (initialized once per bucket)
        self._rag_instances = {}

        # Cached delta summaries {scene_number: delta_text}
        self._delta_cache = {}

    def load_project_context(self) -> None:
        """Load all project context from database."""
        # Project metadata
        self.project = self.db.get_project()

        # Characters
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name, description, role, arc FROM characters")
            self.characters = [dict(row) for row in cursor.fetchall()]

            # Scenes (all 30)
            cursor.execute("""
                SELECT id, scene_number, title, description, characters, tone
                FROM scenes
                ORDER BY scene_number
            """)
            scenes = [dict(row) for row in cursor.fetchall()]

            # Calculate act for each scene based on scene number
            for scene in scenes:
                scene_num = scene['scene_number']
                if scene_num <= 6:
                    scene['act'] = 1
                elif scene_num <= 24:
                    scene['act'] = 2
                else:
                    scene['act'] = 3

            self.scenes = scenes

        # Writer notes
        try:
            self.writer_notes = self.db.get_writer_notes()
        except Exception:
            self.writer_notes = None

        # Cache story outline (built once, used for all queries)
        self._story_outline = self.build_story_outline()

        # RAG instances are lazy-loaded in _get_rag_instance() to avoid shared state conflicts

    def _get_rag_instance(self, bucket_name: str) -> Optional[LightRAG]:
        """
        Get or create a LightRAG instance for a bucket (lazy loading).

        Args:
            bucket_name: Name of the bucket

        Returns:
            LightRAG instance or None if bucket doesn't exist
        """
        if bucket_name in self._rag_instances:
            return self._rag_instances[bucket_name]

        bucket_path = self.bucket_dir / bucket_name
        if not bucket_path.exists():
            return None

        self._rag_instances[bucket_name] = LightRAG(
            working_dir=str(bucket_path),
            embedding_func=openai_embed,
            llm_model_func=gpt_5_1_complete,
        )
        return self._rag_instances[bucket_name]

    def build_story_outline(self) -> str:
        """
        Build complete story outline for expert consultation.

        Returns:
            Formatted story outline with all context
        """
        parts = []

        # Project info
        if self.project:
            parts.append(f"PROJECT: {self.project['name']}")
            parts.append(f"GENRE: {self.project['genre']}")

        # Writer notes
        if self.writer_notes:
            if self.writer_notes.get('logline'):
                parts.append(f"\nLOGLINE: {self.writer_notes['logline']}")
            if self.writer_notes.get('theme'):
                parts.append(f"THEME: {self.writer_notes['theme']}")
            if self.writer_notes.get('tone'):
                parts.append(f"TONE: {self.writer_notes['tone']}")
            if self.writer_notes.get('comps'):
                parts.append(f"COMPS: {self.writer_notes['comps']}")

        # Characters
        if self.characters:
            parts.append("\nCHARACTERS:")
            for char in self.characters:
                parts.append(f"  • {char['name']} ({char['role']}): {char['description']}")

        # Scene structure (condensed)
        if self.scenes:
            parts.append(f"\nSTRUCTURE: {len(self.scenes)} scenes")

        return "\n".join(parts)

    def get_surrounding_context(self, scene: Dict) -> Dict[str, Optional[str]]:
        """
        Get context from previous and next scenes.

        For previous scene: Uses DELTA SUMMARY (compressed 250-token version)
        from synthesized blueprint if available, otherwise falls back to
        original scene description.

        For next scene: Uses original description (hasn't been processed yet).

        Args:
            scene: Current scene dictionary

        Returns:
            Dictionary with previous and next scene summaries
        """
        scene_num = scene['scene_number']

        prev_scene = None
        next_scene = None

        # Get previous scene data
        for s in self.scenes:
            if s['scene_number'] == scene_num - 1:
                # Try to get delta summary from previous scene
                prev_delta = self._get_scene_delta_summary(s)

                if prev_delta:
                    # Use compressed delta summary for feed-forward context
                    prev_scene = f"Scene {s['scene_number']}: {s['title']}\n\nDELTA SUMMARY:\n{prev_delta}"
                else:
                    # Fallback to original description
                    prev_scene = f"Scene {s['scene_number']}: {s['title']} - {s['description']}"

            elif s['scene_number'] == scene_num + 1:
                # Next scene hasn't been processed yet, use original description
                next_scene = f"Scene {s['scene_number']}: {s['title']} - {s['description']}"

        return {
            'previous': prev_scene,
            'next': next_scene
        }

    def _get_scene_blueprint(self, scene_id: int) -> Optional[str]:
        """
        Retrieve the synthesized blueprint for a scene if it exists.

        Args:
            scene_id: Scene ID from database

        Returns:
            Synthesized blueprint content or None
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT content
                    FROM brainstorm_sessions
                    WHERE scene_id = ? AND bucket_used = 'all'
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (scene_id,))

                row = cursor.fetchone()
                if row:
                    return row['content']
        except Exception as e:
            console.print(f"[dim]Could not load blueprint for scene {scene_id}: {e}[/dim]")

        return None

    async def _generate_delta_summary(self, scene: Dict, blueprint: str) -> str:
        """
        Generate a compressed delta summary from a full blueprint.

        Extracts key changes and beats in 250-300 tokens for efficient
        feed-forward context.

        Args:
            scene: Scene dictionary
            blueprint: Full synthesized blueprint

        Returns:
            Compressed delta summary (250-300 tokens)
        """
        try:
            client = AsyncOpenAI()
            response = await client.chat.completions.create(
                model="gpt-5.1",
                messages=[{
                    "role": "user",
                    "content": f"""Compress this scene blueprint into a 250-token DELTA SUMMARY.

Focus on:
- What changed (character arcs, relationships, power dynamics)
- Key dramatic beats that occurred
- Emotional/tonal shifts
- Setup for next scene

Scene {scene['scene_number']}: {scene['title']}

FULL BLUEPRINT:
{blueprint}

Provide a tight, bullet-point summary (250 tokens max) focusing on CHANGES and MOMENTUM."""
                }],
                temperature=0.3,
                max_tokens=350
            )

            return response.choices[0].message.content

        except Exception as e:
            console.print(f"[dim]Could not generate delta summary: {e}[/dim]")
            # Fallback: truncate blueprint to first 250 words
            words = blueprint.split()[:250]
            return " ".join(words) + "..."

    def _get_scene_delta_summary(self, scene: Dict) -> Optional[str]:
        """
        Get cached delta summary for a scene.

        Args:
            scene: Scene dictionary

        Returns:
            Delta summary from cache or None
        """
        scene_num = scene['scene_number']
        return self._delta_cache.get(scene_num)

    async def _cache_delta_summary(self, scene: Dict) -> None:
        """
        Generate and cache delta summary for a scene after processing.

        Args:
            scene: Scene dictionary
        """
        scene_num = scene['scene_number']

        # Don't regenerate if already cached
        if scene_num in self._delta_cache:
            return

        blueprint = self._get_scene_blueprint(scene['id'])
        if blueprint:
            delta = await self._generate_delta_summary(scene, blueprint)
            self._delta_cache[scene_num] = delta

    # === IMPROVEMENT #16: Confidence Scores ===

    def calculate_expert_agreement(self, bucket_results: List[Dict]) -> Dict[str, float]:
        """
        Calculate confidence based on expert agreement.

        Returns confidence scores (0-1) for each section type.
        Higher score = experts agree more = higher confidence.
        """
        sections = ['STRUCTURAL', 'DIALOGUE', 'VISUAL', 'CHARACTER', 'GOLDEN']
        scores = {}

        for section in sections:
            # Count mentions of section keywords in each expert response
            lengths = []
            for result in bucket_results:
                # Count mentions of section-related content
                response_lower = result['response'].lower()
                count = response_lower.count(section.lower())
                lengths.append(count)

            # Calculate variance (low variance = high agreement)
            if lengths and sum(lengths) > 0:
                avg = sum(lengths) / len(lengths)
                variance = sum((x - avg) ** 2 for x in lengths) / len(lengths)
                # Convert to 0-1 score (low variance = high score)
                score = max(0, min(1, 1 - (variance / (avg + 1))))
                scores[section] = score
            else:
                scores[section] = 0.5  # Neutral if no data

        return scores

    def display_confidence_scores(self, scene_num: int, scores: Dict[str, float]) -> None:
        """Display confidence scores with color coding."""
        console.print(f"\n[bold]Confidence Scores for Scene {scene_num}:[/bold]")

        for section, score in scores.items():
            # Color code based on confidence
            if score > 0.7:
                color = "green"
                indicator = "●●●"
            elif score > 0.4:
                color = "yellow"
                indicator = "●●○"
            else:
                color = "red"
                indicator = "●○○"

            console.print(f"[{color}]{indicator} {section}: {score:.2f}[/{color}]")

        avg_score = sum(scores.values()) / len(scores) if scores else 0
        if avg_score < 0.5:
            console.print("[yellow]⚠️  Low confidence - experts disagree. Review recommended.[/yellow]")

    # === IMPROVEMENT #17: Preview Mode ===

    def preview_scene_prompts(self, scene_number: int) -> None:
        """Show what prompts will be sent for a scene without executing."""
        scene = next((s for s in self.scenes if s['scene_number'] == scene_number), None)
        if not scene:
            console.print(f"[red]Scene {scene_number} not found[/red]")
            return

        # Build prompts (but don't send)
        books_prompt = self.build_expert_query(scene, "books")
        plays_prompt = self.build_expert_query(scene, "plays")
        scripts_prompt = self.build_expert_query(scene, "scripts")

        # Display preview
        console.print(Panel(
            books_prompt[:800] + "\n\n[dim]...(truncated)[/dim]" if len(books_prompt) > 800 else books_prompt,
            title="📚 Books Expert Prompt Preview",
            border_style="cyan"
        ))

        # Estimate tokens
        books_tokens = len(books_prompt.split()) * 1.3
        console.print(f"[dim]Estimated tokens: ~{books_tokens:.0f}[/dim]\n")

        if Confirm.ask("Show Plays prompt?", default=False):
            console.print(Panel(
                plays_prompt[:800] + "\n\n[dim]...(truncated)[/dim]" if len(plays_prompt) > 800 else plays_prompt,
                title="🎭 Plays Expert Prompt Preview",
                border_style="cyan"
            ))
            plays_tokens = len(plays_prompt.split()) * 1.3
            console.print(f"[dim]Estimated tokens: ~{plays_tokens:.0f}[/dim]\n")

        if Confirm.ask("Show Scripts prompt?", default=False):
            console.print(Panel(
                scripts_prompt[:800] + "\n\n[dim]...(truncated)[/dim]" if len(scripts_prompt) > 800 else scripts_prompt,
                title="🎬 Scripts Expert Prompt Preview",
                border_style="cyan"
            ))
            scripts_tokens = len(scripts_prompt.split()) * 1.3
            console.print(f"[dim]Estimated tokens: ~{scripts_tokens:.0f}[/dim]\n")

    # === IMPROVEMENT #18: Budget Estimator ===

    def estimate_cost_and_time(self, num_scenes: int, start_from: int = 1) -> Dict:
        """
        Estimate cost and processing time for scene generation.

        Args:
            num_scenes: Total number of scenes to process
            start_from: Starting scene number (for partial runs)

        Returns:
            Dictionary with cost and time estimates
        """
        scenes_to_process = num_scenes - start_from + 1

        # Token estimates (based on current prompts)
        tokens_per_scene = {
            'input': 3500,   # 3 expert prompts + synthesis prompt
            'output': 4000,  # 3 expert responses + synthesis response
            'delta': 350     # Delta summary generation
        }

        total_input = tokens_per_scene['input'] * scenes_to_process
        total_output = tokens_per_scene['output'] * scenes_to_process
        # Delta summaries: only for scenes that have a previous scene
        num_deltas = max(0, scenes_to_process - 1) if start_from == 1 else scenes_to_process
        total_delta = tokens_per_scene['delta'] * num_deltas

        # Pricing (as of January 2025)
        # GPT-4o: $2.50/1M input, $10.00/1M output
        # GPT-4o-mini: $0.15/1M input, $0.60/1M output
        gpt4o_input_cost = (total_input + total_delta) / 1_000_000 * 2.50
        gpt4o_output_cost = total_output / 1_000_000 * 10.00
        # LightRAG uses mini for queries
        gpt4o_mini_cost = (total_input * 0.5) / 1_000_000 * 0.15

        total_cost = gpt4o_input_cost + gpt4o_output_cost + gpt4o_mini_cost

        # Time estimate (45-60 sec per scene average)
        time_seconds = scenes_to_process * 52.5
        time_minutes = time_seconds / 60

        return {
            'num_scenes': num_scenes,
            'scenes_to_process': scenes_to_process,
            'start_from': start_from,
            'total_tokens': total_input + total_output + total_delta,
            'estimated_cost': total_cost,
            'estimated_time_minutes': time_minutes,
            'cost_per_scene': total_cost / scenes_to_process if scenes_to_process > 0 else 0,
            'breakdown': {
                'gpt4o_input': gpt4o_input_cost,
                'gpt4o_output': gpt4o_output_cost,
                'gpt4o_mini': gpt4o_mini_cost
            }
        }

    def display_cost_estimate(self, estimate: Dict) -> None:
        """Display cost and time estimate in a nice panel."""
        start_text = f" (starting from Scene {estimate['start_from']})" if estimate['start_from'] > 1 else ""

        content = f"""[bold]Automated Brainstorm - Cost & Time Estimate[/bold]

[cyan]Scope:[/cyan]
  Scenes to process: {estimate['scenes_to_process']} of {estimate['num_scenes']}{start_text}

[cyan]Cost Estimate:[/cyan]
  Total: [bold]${estimate['estimated_cost']:.2f}[/bold]
  Per scene: ${estimate['cost_per_scene']:.3f}

  Breakdown:
    GPT-4o input:  ${estimate['breakdown']['gpt4o_input']:.2f}
    GPT-4o output: ${estimate['breakdown']['gpt4o_output']:.2f}
    GPT-4o-mini:   ${estimate['breakdown']['gpt4o_mini']:.2f}

[cyan]Time Estimate:[/cyan]
  Total: [bold]{estimate['estimated_time_minutes']:.1f} minutes[/bold] (~{estimate['estimated_time_minutes']/60:.1f} hours)
  Per scene: ~{(estimate['estimated_time_minutes']*60)/estimate['scenes_to_process']:.0f} seconds

[cyan]Tokens:[/cyan]
  Total: ~{estimate['total_tokens']:,} tokens

[dim]Note: Estimates based on average token usage. Actual costs may vary.[/dim]"""

        console.print(Panel(content, border_style="yellow", padding=(1, 2)))

    # === IMPROVEMENT #14 & #15: Resume and Selective Regeneration ===

    async def regenerate_scenes(self, scene_numbers: List[int]) -> None:
        """
        Regenerate specific scenes only.

        Args:
            scene_numbers: List of scene numbers to regenerate
        """
        scenes_to_regen = [s for s in self.scenes if s['scene_number'] in scene_numbers]

        if not scenes_to_regen:
            console.print("[red]No valid scenes found to regenerate[/red]")
            return

        console.print(f"[yellow]⚠️  Regenerating scenes: {', '.join(map(str, scene_numbers))}[/yellow]")
        console.print("[yellow]This will overwrite existing blueprints for these scenes.[/yellow]")

        if not Confirm.ask("\nContinue?"):
            console.print("[yellow]Cancelled[/yellow]")
            return

        # Show cost estimate
        estimate = self.estimate_cost_and_time(len(self.scenes), min(scene_numbers))
        # Adjust for selective scenes
        estimate['scenes_to_process'] = len(scenes_to_regen)
        estimate['estimated_cost'] = estimate['cost_per_scene'] * len(scenes_to_regen)
        estimate['estimated_time_minutes'] = (len(scenes_to_regen) * 52.5) / 60
        self.display_cost_estimate(estimate)

        if not Confirm.ask("\nProceed with regeneration?"):
            console.print("[yellow]Cancelled[/yellow]")
            return

        # Process scenes
        results = []

        console.print(f"\n[bold]Regenerating {len(scenes_to_regen)} scene(s)...[/bold]\n")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:

            task = progress.add_task("Regenerating...", total=len(scenes_to_regen))

            for scene in scenes_to_regen:
                result = await self.process_scene(scene, progress, task)
                results.append(result)

                if result['success']:
                    self.display_scene_result(result)

        # Summary
        successful = sum(1 for r in results if r['success'])
        console.print(f"\n[bold green]✓ Regenerated: {successful}/{len(scenes_to_regen)} scenes[/bold green]")

    def build_expert_query(self, scene: Dict, bucket_name: str) -> str:
        """
        Build expert consultation query for a specific scene and bucket.

        Each bucket has custom prompts that play to its strengths:
        - Books: Structure, beat positioning, act mechanics
        - Plays: Dialogue, subtext, dramatic technique
        - Scripts: Visual storytelling, pacing, modern execution

        Args:
            scene: Scene dictionary from database
            bucket_name: Which expert bucket (books/plays/scripts)

        Returns:
            Formatted expert query
        """
        # Use cached context
        story_outline = self._story_outline
        scene_chars = scene.get('characters', '') or "main characters"
        surrounding = self.get_surrounding_context(scene)

        # Metadata header
        from datetime import datetime
        metadata = f"""---
SCENE_ID: {scene['id']}
SCENE_NUMBER: {scene['scene_number']}
ACT: {scene.get('act', 'Unknown')}
BUCKET: {bucket_name}
MODEL: "gpt-5.1 (LightRAG)"
VERSION: 2.0
PROJECT: {self.project['name'] if self.project else 'Unknown'}
TIMESTAMP: {datetime.now().isoformat()}
---"""

        # Build context section (same for all)
        context_section = f"""STORY OUTLINE:
{story_outline}

SCENE CONTEXT:
Scene {scene['scene_number']}: {scene['title']}
Act: {scene.get('act', 'Unknown')}
Description: {scene['description']}
Characters: {scene_chars}

SURROUNDING SCENES:
Previous: {surrounding['previous'] or 'N/A (first scene)'}
Next: {surrounding['next'] or 'N/A (last scene)'}"""

        # Bucket-specific prompts
        if bucket_name == "books":
            return f"""{metadata}

You are a SCREENPLAY STRUCTURE AND CRAFT EXPERT.

{self._romcom_framework}

{context_section}

As a structure expert, PROPOSE how to architect this scene.

**OUTPUT REQUIREMENTS:**
- Bullet points only (no paragraphs)
- Active, specific guidance (not theoretical analysis)

## PLOT_PYRAMID
Where does this scene fall in the rising/falling action:
- Position in three-act structure (setup, rising action, midpoint, crisis, climax, resolution)
- What beat does this scene represent (catalyst, point of no return, all is lost, etc.)
- What must change from scene open to close

## SUBPLOT_INTEGRATION
How do secondary storylines weave into this scene:
- Which subplots should surface here
- How side characters or B-stories echo or contrast the main arc
- Connections that pay off later or set up future scenes

## RELATIONSHIPS_AND_CHEMISTRY
How to build connection between characters:
- What draws these characters together or pushes them apart
- Moments that reveal compatibility, friction, or unspoken attraction
- How the relationship dynamic shifts within this scene

## PACING_AND_MOMENTUM
The rhythm and drive of this scene:
- Fast, slow, or building tempo
- Where to linger vs. move quickly
- How this scene propels into the next

Provide concrete, executable structural guidance."""

        elif bucket_name == "plays":
            return f"""{metadata}

You are a CLASSICAL STORY PATTERNS EXPERT drawing from Shakespeare and timeless dramatic works.

{self._romcom_framework}

{context_section}

As a story patterns expert, PROPOSE how this scene connects to proven dramatic archetypes.

**OUTPUT REQUIREMENTS:**
- Bullet points only (no paragraphs)
- Active, specific guidance (not theoretical analysis)

## STORY_ARCHETYPE
What classic pattern does this scene draw from:
- Which Shakespearean or classical framework applies (enemies to lovers, mistaken identity, forbidden love, battle of wills)
- How this scene fits that archetype
- Where to honor the pattern vs. subvert it

## RELATIONSHIP_DYNAMICS
The power and vulnerability between characters:
- Who has the upper hand, who's exposed
- What each character wants from the other (stated and unstated)
- How the dynamic shifts within this scene
- The push-pull tension that creates chemistry

## TIMELESS_TROPES
Proven dramatic devices to deploy:
- The overheard conversation, the interruption, the confession
- Mistaken assumptions, secrets, dramatic irony
- The meddling friend, the rival, the obstacle
- Physical comedy or mishaps that reveal character

## THEMATIC_UNDERCURRENT
What this scene is really about underneath:
- The deeper question or truth being explored
- How surface action reflects inner conflict
- What the audience should feel but characters won't say

Provide concrete, pattern-based guidance."""

        elif bucket_name == "scripts":
            return f"""{metadata}

You are a ROMCOM REFERENCE EXPERT with deep knowledge of modern romantic comedy films.

{self._romcom_framework}

{context_section}

As a reference expert, draw from existing romcoms to inspire and inform this scene.

**OUTPUT REQUIREMENTS:**
- Bullet points only (no paragraphs)
- Active, specific guidance (not theoretical analysis)

## COMPARABLE_SCENES
What existing romcom scenes does this remind you of:
- Specific scenes from films that tackle similar beats or dynamics
- What made those scenes work
- What can be borrowed or adapted

## EXECUTION_INSPIRATION
How did those films handle the specifics:
- Dialogue style and rhythm
- Visual approach and staging
- Tone balance (comedy vs. heart)
- Pacing and timing

## WHAT_TO_LEARN
Lessons from films that did this well:
- Techniques worth emulating
- Choices that elevated the scene
- How they made familiar beats feel fresh

## WHAT_TO_AVOID
Lessons from films that missed the mark:
- Common pitfalls for this type of scene
- What falls flat or feels forced
- Clichés to sidestep or reinvent

Provide concrete, reference-based guidance."""

        else:
            # Fallback (shouldn't happen)
            return f"{context_section}\n\nProvide guidance for writing this scene."

    async def query_bucket_for_scene(
        self,
        scene: Dict,
        bucket_name: str
    ) -> Optional[Dict]:
        """
        Query a single bucket for a single scene.

        Args:
            scene: Scene dictionary
            bucket_name: Bucket to query

        Returns:
            Result dictionary or None
        """
        # Get or create RAG instance (lazy loading)
        rag = self._get_rag_instance(bucket_name)
        if not rag:
            console.print(f"[yellow]⚠️  Bucket '{bucket_name}' not found[/yellow]")
            return None

        try:
            # Build expert query
            query = self.build_expert_query(scene, bucket_name)

            # Initialize storages (only does work on first call)
            await rag.initialize_storages()

            # Query with hybrid mode
            response = await rag.aquery(query, param=QueryParam(mode="hybrid"))

            # Apply reranking if available
            if response and self.reranker.is_available():
                chunks = [p.strip() for p in response.split('\n\n') if p.strip()]
                if len(chunks) > 1:
                    reranked = self.reranker.rerank(
                        query=query,
                        documents=chunks,
                        top_n=min(10, len(chunks))
                    )
                    response = '\n\n'.join([r['text'] for r in reranked])

            if response:
                return {
                    'bucket': bucket_name,
                    'response': response
                }

        except Exception as e:
            console.print(f"[red]✗ Error querying {bucket_name}: {e}[/red]")

        return None

    async def synthesize_expert_insights(
        self,
        scene: Dict,
        bucket_results: List[Dict]
    ) -> str:
        """
        Synthesize insights from all expert buckets into unified guidance.

        Combines structure (books), dramatic craft (plays), and execution (scripts)
        into a comprehensive, actionable scene blueprint.

        Args:
            scene: Scene dictionary
            bucket_results: Results from all buckets

        Returns:
            Synthesized guidance for writing the scene
        """
        # Build synthesis prompt
        story_outline = self.build_story_outline()
        surrounding = self.get_surrounding_context(scene)

        # Metadata for synthesis
        from datetime import datetime
        metadata = f"""---
SCENE_ID: {scene['id']}
SCENE_NUMBER: {scene['scene_number']}
ACT: {scene.get('act', 'Unknown')}
BUCKET: synthesis
MODEL: "gpt-5"
VERSION: 2.0
PROJECT: {self.project['name'] if self.project else 'Unknown'}
TIMESTAMP: {datetime.now().isoformat()}
---"""

        system_prompt = f"""{metadata}

You are a MASTER SCREENPLAY CONSULTANT synthesizing expert advice.

{self._romcom_framework}

STORY CONTEXT:
{story_outline}

SCENE TO SYNTHESIZE:
Scene {scene["scene_number"]}: {scene["title"]}
Act: {scene.get("act", "Unknown")}
Description: {scene["description"]}
Characters: {scene.get("characters", "main characters")}

SURROUNDING SCENES:
Previous: {surrounding["previous"] or "N/A"}
Next: {surrounding["next"] or "N/A"}

THREE EXPERT CONSULTATIONS:
1. **BOOKS (Structure Expert)** - Plot pyramid, subplot integration, relationships, pacing
2. **PLAYS (Story Patterns Expert)** - Shakespearean archetypes, timeless tropes, thematic undercurrent
3. **SCRIPTS (Reference Expert)** - Comparable scenes from romcoms, execution inspiration, what to learn/avoid

YOUR TASK:
Synthesize all three perspectives into ONE actionable scene blueprint.

**SYNTHESIS DIRECTIVE:**
- Weave together structure, pattern, and reference insights
- If experts disagree, prioritize character truth and emotional clarity
- Bullet points only (no paragraphs)

OUTPUT FORMAT (use these exact sections):

## SCENE_BLUEPRINT

### SUMMARY
What this scene needs to accomplish and how to approach it (3-5 sentences)

### STRUCTURE_AND_PACING
- Where this falls in the story arc
- What must change from open to close
- Subplot threads to weave in
- Tempo and momentum

### ARCHETYPE_AND_TROPES
- Which classic pattern this scene draws from
- Timeless devices to deploy (dramatic irony, the interruption, the reveal)
- How to honor the pattern while keeping it fresh

### RELATIONSHIP_DYNAMICS
- Power balance and vulnerability
- What draws characters together or apart
- The push-pull that creates chemistry
- How the dynamic shifts within the scene

### REFERENCE_POINTS
- Comparable scenes from existing romcoms
- What those scenes did well
- Techniques worth borrowing
- Clichés to avoid

### THEMATIC_CORE
- What this scene is really about underneath
- The emotional truth to convey
- What the audience should feel

Be SPECIFIC, CONCRETE, ACTIONABLE."""

        # Combine bucket results
        expert_context = "\n\n".join([
            f"=== {result['bucket'].upper()} EXPERT ANALYSIS ===\n{result['response']}"
            for result in bucket_results
        ])

        # Call GPT-4o for synthesis
        try:
            client = AsyncOpenAI()
            response = await client.chat.completions.create(
                model="gpt-5",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"{expert_context}\n\n---\n\nSynthesize these three expert perspectives into a comprehensive scene blueprint using the exact format specified."}
                ],
                temperature=0.7,
                max_tokens=2000
            )

            return response.choices[0].message.content

        except Exception as e:
            console.print(f"[red]Error in synthesis: {e}[/red]")
            # Fallback: return raw expert results
            return expert_context

    async def process_scene(self, scene: Dict, progress: Progress, task_id) -> Dict:
        """
        Process a single scene through all expert buckets.

        Args:
            scene: Scene dictionary
            progress: Rich progress instance
            task_id: Progress task ID

        Returns:
            Processing results
        """
        scene_num = scene['scene_number']
        scene_title = scene['title']

        progress.update(task_id, description=f"Scene {scene_num}: {scene_title}")

        # Query all three buckets in parallel
        results = await asyncio.gather(
            *[self.query_bucket_for_scene(scene, bucket) for bucket in self.buckets],
            return_exceptions=True
        )

        # Filter successful results
        bucket_results = [r for r in results if r and not isinstance(r, Exception)]

        # Synthesize insights
        if bucket_results:
            synthesized = await self.synthesize_expert_insights(scene, bucket_results)

            # IMPROVEMENT #16: Calculate confidence scores
            confidence_scores = self.calculate_expert_agreement(bucket_results)
            self.scene_confidence_scores[scene_num] = confidence_scores

            # Save to database
            self._save_brainstorm_session(scene, bucket_results, synthesized)

            # Cache delta summary for next scene's context
            await self._cache_delta_summary(scene)

            progress.update(task_id, advance=1)

            return {
                'scene_number': scene_num,
                'scene_title': scene_title,
                'success': True,
                'bucket_results': bucket_results,
                'synthesized': synthesized,
                'confidence_scores': confidence_scores
            }
        else:
            progress.update(task_id, advance=1)
            return {
                'scene_number': scene_num,
                'scene_title': scene_title,
                'success': False,
                'error': 'No bucket results'
            }

    def _save_brainstorm_session(
        self,
        scene: Dict,
        bucket_results: List[Dict],
        synthesized: str
    ) -> None:
        """Save brainstorm session to database."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            # Save synthesized result
            cursor.execute("""
                INSERT INTO brainstorm_sessions
                (scene_id, tone, bucket_used, content)
                VALUES (?, ?, ?, ?)
            """, (
                scene['id'],
                self.tone,
                "all",  # Used all buckets
                synthesized
            ))

            # Optionally save individual bucket results as separate sessions
            for bucket_result in bucket_results:
                cursor.execute("""
                    INSERT INTO brainstorm_sessions
                    (scene_id, tone, bucket_used, content)
                    VALUES (?, ?, ?, ?)
                """, (
                    scene['id'],
                    self.tone,
                    bucket_result['bucket'],
                    bucket_result['response']
                ))

            conn.commit()

    def display_scene_result(self, result: Dict) -> None:
        """Display results for a completed scene."""
        if not result['success']:
            console.print(f"\n[red]✗ Scene {result['scene_number']}: {result['scene_title']} - Failed[/red]")
            return

        console.print(f"\n[bold cyan]✓ Scene {result['scene_number']}: {result['scene_title']}[/bold cyan]")

        # IMPROVEMENT #16: Show confidence scores if available
        if 'confidence_scores' in result:
            self.display_confidence_scores(result['scene_number'], result['confidence_scores'])

        # Show synthesized guidance
        console.print(Panel(
            Markdown(result['synthesized']),
            title=f"Scene {result['scene_number']} Guidance",
            border_style="green"
        ))

    async def run_batch_processing(self, start_from: int = 1, skip_confirmation: bool = False) -> None:
        """
        Run automated brainstorming for scenes.

        Args:
            start_from: Starting scene number (default: 1, process all)
            skip_confirmation: Skip user confirmation prompts (for web/API usage)
        """
        console.clear()

        # Load project
        console.print("[cyan]Loading project context...[/cyan]")
        self.load_project_context()

        if not self.project:
            console.print("[red]Error: No project found[/red]")
            return

        if not self.scenes:
            console.print("[red]Error: No scenes found. Add scenes in INTAKE first.[/red]")
            return

        # IMPROVEMENT #14: Filter scenes to process
        scenes_to_process = [s for s in self.scenes if s['scene_number'] >= start_from]

        # Show header
        start_text = f" (starting from Scene {start_from})" if start_from > 1 else ""
        console.print(Panel.fit(
            f"[bold cyan]Automated Brainstorm[/bold cyan]\n\n"
            f"Project: {self.project['name']}\n"
            f"Scenes to process: {len(scenes_to_process)} of {len(self.scenes)}{start_text}\n"
            f"Buckets: {', '.join(self.buckets)}\n"
            f"Tone: {self.tone}",
            border_style="cyan"
        ))

        # IMPROVEMENT #18: Show cost estimate
        estimate = self.estimate_cost_and_time(len(self.scenes), start_from)
        self.display_cost_estimate(estimate)

        # Confirm (skip if called from web/API)
        if not skip_confirmation:
            if not Confirm.ask(f"\n[cyan]Proceed with processing?[/cyan]"):
                console.print("[yellow]Cancelled[/yellow]")
                return

            # IMPROVEMENT #17: Preview option
            if len(scenes_to_process) > 0 and Confirm.ask("\nPreview Scene 1 prompts before processing?", default=False):
                self.preview_scene_prompts(scenes_to_process[0]['scene_number'])
                if not Confirm.ask("\nProceed with batch processing?"):
                    console.print("[yellow]Cancelled[/yellow]")
                    return

        # Process scenes with progress bar
        console.print(f"\n[bold]Processing {len(scenes_to_process)} scenes...[/bold]\n")

        results = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:

            task = progress.add_task(
                "Starting...",
                total=len(scenes_to_process)
            )

            for scene in scenes_to_process:
                result = await self.process_scene(scene, progress, task)
                results.append(result)

                # Display result as it completes
                if result['success']:
                    self.display_scene_result(result)

        # Summary
        successful = sum(1 for r in results if r['success'])
        console.print(f"\n[bold green]✓ Completed: {successful}/{len(scenes_to_process)} scenes[/bold green]")

        if successful < len(scenes_to_process):
            failed = len(scenes_to_process) - successful
            console.print(f"[yellow]⚠️  Failed: {failed} scenes[/yellow]")

        console.print(f"\n[dim]Results saved to brainstorm_sessions table[/dim]")


async def main():
    """CLI entrypoint."""
    import sys
    from .start import StartModule

    start = StartModule()

    # Project selection
    console.print(Panel.fit(
        "[bold cyan]Automated Brainstorm[/bold cyan]\n\n"
        "Batch process all 30 scenes with expert consultation",
        border_style="cyan"
    ))

    existing = start.list_projects()

    if not existing:
        console.print("\n[yellow]No projects found.[/yellow]")
        console.print("\n[cyan]Create one first:[/cyan]")
        console.print("  python -m lizzy.start")
        sys.exit(0)

    # Show project table
    table = Table(title="Available Projects", show_header=True, header_style="bold cyan")
    table.add_column("#", style="dim")
    table.add_column("Project Name", style="green")

    for idx, proj_name in enumerate(existing, 1):
        table.add_row(str(idx), proj_name)

    console.print("\n")
    console.print(table)

    # Select project
    project_idx = int(Prompt.ask(
        "\nChoose project number",
        choices=[str(i) for i in range(1, len(existing) + 1)]
    ))
    project_name = existing[project_idx - 1]

    # Get database path
    db_path = start.get_project_path(project_name)

    if not db_path:
        console.print(f"[red]Error: Project '{project_name}' not found[/red]")
        sys.exit(1)

    # Initialize brainstorm
    brainstorm = AutomatedBrainstorm(db_path)

    # IMPROVEMENTS #14 & #15: Processing mode selection
    console.print("\n[bold]Processing Mode:[/bold]")
    console.print("[1] Process all scenes")
    console.print("[2] Resume from scene N")
    console.print("[3] Regenerate specific scenes")

    mode = Prompt.ask("\nChoose option", choices=["1", "2", "3"], default="1")

    if mode == "1":
        # Process all scenes
        await brainstorm.run_batch_processing()

    elif mode == "2":
        # Resume from scene N
        start_scene = int(Prompt.ask("Start from scene number", default="1"))
        await brainstorm.run_batch_processing(start_from=start_scene)

    elif mode == "3":
        # Regenerate specific scenes
        scene_nums_str = Prompt.ask("Scene numbers (comma-separated, e.g., 5,12,18)")
        try:
            scene_nums = [int(n.strip()) for n in scene_nums_str.split(',')]
            # Load project context first
            brainstorm.load_project_context()
            await brainstorm.regenerate_scenes(scene_nums)
        except ValueError:
            console.print("[red]Invalid scene numbers[/red]")
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
