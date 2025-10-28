"""
Automated Brainstorm - Batch Scene Generation

Processes all 30 scenes from the beat sheet, querying expert knowledge buckets
for each scene and synthesizing golden-age romantic comedy insights.

Each bucket acts as an expert consultant:
- Books: Screenplay theory and structure
- Plays: Classical dramatic wisdom
- Scripts: Modern romantic comedy execution
"""

import asyncio
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import gpt_4o_mini_complete, openai_embed
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

        # Buckets - always use all three for golden age romcom
        self.bucket_dir = Path("./rag_buckets")
        self.buckets = ["books", "plays", "scripts"]

        # Tone
        self.tone = "Golden Age Romantic Comedy"

        # Initialize reranker
        self.reranker = CohereReranker()

        # IMPROVEMENT #16: Store confidence scores
        self.scene_confidence_scores = {}

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
                model="gpt-4o-mini",
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
        Get or generate delta summary for a scene.

        Checks database for cached delta, generates if not found.

        Args:
            scene: Scene dictionary

        Returns:
            Delta summary or None
        """
        # For now, generate on-the-fly from blueprint
        # TODO: Cache delta summaries in database for reuse
        blueprint = self._get_scene_blueprint(scene['id'])

        if blueprint:
            # Generate delta summary synchronously by running async function
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            if loop.is_running():
                # If loop is running, we're already in async context
                # This shouldn't happen but handle gracefully
                return None
            else:
                delta = loop.run_until_complete(self._generate_delta_summary(scene, blueprint))
                return delta

        return None

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
        story_outline = self.build_story_outline()
        scene_chars = scene.get('characters', '') or "main characters"
        surrounding = self.get_surrounding_context(scene)

        # Compressed golden-age romcom definition (~100 tokens)
        golden_age_definition = """GOLDEN AGE ROMCOM: Nineteen-thirties to nineteen-fifties screwball/romantic comedies featuring witty rapid-fire dialogue, class conflict, physical comedy, strong independent leads (esp. female), misunderstandings, sophisticated sexual tension (Production Code era). Reference: His Girl Friday, Philadelphia Story, It Happened One Night, Bringing Up Baby."""

        # Metadata header
        from datetime import datetime
        metadata = f"""---
SCENE_ID: {scene['id']}
SCENE_NUMBER: {scene['scene_number']}
ACT: {scene.get('act', 'Unknown')}
BUCKET: {bucket_name}
MODEL: "gpt-4o-mini (LightRAG)"
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

You are a SCREENPLAY STRUCTURE AND CRAFT EXPERT consulting on a golden-age romantic comedy.

{golden_age_definition}

{context_section}

As a structure expert, PROPOSE how to architect this scene dramatic structure.

**OUTPUT REQUIREMENTS:**
- Bullet points only (no paragraphs)
- five to seven bullets per section
- Target length: 400-800 tokens total
- Active, specific guidance (not theoretical analysis)

**DIRECTIVE:** Extend and critique the surrounding context; do not restate it.

## STRUCTURAL_FUNCTION
Propose where this scene falls structurally and what beat it must hit:
- Three-act position and romcom beat sheet function
- Structural purpose (setup, catalyst, midpoint reversal, crisis, climax)
- How this advances plot threads and character arcs

## BEAT_ENGINEERING
Advise which dramatic beats must occur within this scene:
- Essential turning points and revelations
- Tension escalation or release mechanics
- What must change from scene open to close

## GENRE_MECHANICS
Recommend which romcom conventions to employ or subvert:
- Genre tropes to activate (meet-cute, obstacle, reversal, confession)
- Balance between romance beats and comedy beats
- Connection to overall romantic arc trajectory

## PACING_AND_TRANSITIONS
Specify pacing requirements and transitions:
- Script page length (target range)
- Transition from previous scene (cut, dissolve, match cut)
- Momentum creation for next scene

Provide concrete, executable structural guidance."""

        elif bucket_name == "plays":
            return f"""{metadata}

You are a CLASSICAL DRAMATIC THEORY EXPERT consulting on a golden-age romantic comedy.

{golden_age_definition}

{context_section}

As a dramatic theory expert, PROPOSE how to craft this scene theatrical dimensions.

**OUTPUT REQUIREMENTS:**
- Bullet points only (no paragraphs)
- five to seven bullets per section
- Target length: 400-800 tokens total
- Active, specific guidance (not theoretical analysis)

**DIRECTIVE:** Extend and critique the surrounding context; do not restate it.

## DIALOGUE_DYNAMICS
Advise how to construct dialogue and subtext:
- Subtext layers beneath surface conversation
- Verbal sparring and wit execution
- Power dynamic shifts through dialogue
- Wordplay, double meanings, innuendo opportunities

## CHARACTER_PSYCHOLOGY
Propose character objectives and tactics:
- Each character scene objective (what they want)
- Tactics to achieve objectives (how they pursue it)
- Obstacles (internal fears, external blocks)
- How characters mask or reveal true feelings

## DRAMATIC_TECHNIQUE
Recommend dramatic tools to deploy:
- Dramatic irony opportunities to exploit
- How secrets, lies, misunderstandings escalate
- Central conflict or tension axis
- Aristotelian principles (reversal, recognition, catharsis)

## EMOTIONAL_ARCHITECTURE
Map the emotional journey:
- Each character emotional trajectory through scene
- How to guide audience emotions beat by beat
- Vulnerability or truth to be revealed
- How this deepens character relationships

## STAGE_BUSINESS_AND_ACTION
Specify physical actions and business:
- Physical actions that enhance dramatic beats
- Body language that contradicts or supports dialogue
- Props or setting elements with symbolic weight

Provide concrete theatrical guidance."""

        elif bucket_name == "scripts":
            return f"""{metadata}

You are a MODERN ROMANTIC COMEDY EXECUTION EXPERT consulting on a golden-age romantic comedy.

{golden_age_definition}

{context_section}

As an execution expert, ADVISE how to execute this scene cinematically.

**OUTPUT REQUIREMENTS:**
- Bullet points only (no paragraphs)
- five to seven bullets per section
- Target length: 400-800 tokens total
- Active, specific guidance (not theoretical analysis)

**DIRECTIVE:** Extend and critique the surrounding context; do not restate it.

## VISUAL_STORYTELLING
Propose visual approach and shot design:
- Opening image/establishing shot
- Camera work to capture emotional dynamics
- Visual comedy opportunities
- Setting/location utilization

## PACING_AND_RHYTHM
Specify tempo and cutting:
- Scene tempo (fast banter, slow burn, escalating chaos)
- Cuts and shot selection for rhythm
- Comedic beat timing and pauses
- How this fits overall film pacing

## ROMCOM_TROPES
Recommend genre conventions to deploy:
- Classic tropes to activate (meet-cute, obstacle, confession)
- How to freshen familiar beats
- Contemporary updates to golden-age style
- Balance homage vs. originality

## DIALOGUE_EXECUTION
Advise on dialogue delivery and timing:
- Dialogue speed and rhythm
- Overlapping or rapid-fire exchanges
- Silence and reaction shot placement
- Screwball energy or verbal tennis requirements

## PERFORMANCE_NOTES
Specify actor direction:
- Comedic and romantic tone targets
- Physical comedy and timing essentials
- Restraint vs. broadness calibration
- Chemistry or antagonism intensity

## PRACTICAL_CONSIDERATIONS
Identify execution risks and examples:
- Common pitfalls for this scene type
- Classic/modern romcom examples done well
- Technical or budget concerns

Provide concrete execution guidance."""

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
        bucket_path = self.bucket_dir / bucket_name

        if not bucket_path.exists():
            console.print(f"[yellow]⚠️  Bucket '{bucket_name}' not found[/yellow]")
            return None

        try:
            # Build expert query
            query = self.build_expert_query(scene, bucket_name)

            # Initialize LightRAG
            rag = LightRAG(
                working_dir=str(bucket_path),
                embedding_func=openai_embed,
                llm_model_func=gpt_4o_mini_complete,
            )

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
MODEL: "gpt-4o"
VERSION: 2.0
PROJECT: {self.project['name'] if self.project else 'Unknown'}
TIMESTAMP: {datetime.now().isoformat()}
---"""

        golden_age_desc = "GOLDEN AGE ROMCOM: Nineteen-thirties to nineteen-fifties screwball/romantic comedies featuring witty rapid-fire dialogue, class conflict, physical comedy, strong independent leads (esp. female), misunderstandings, sophisticated sexual tension (Production Code era). Reference: His Girl Friday, Philadelphia Story, It Happened One Night, Bringing Up Baby."

        system_prompt = f"""{metadata}

You are a MASTER SCREENPLAY CONSULTANT synthesizing expert advice for a golden-age romantic comedy.

{golden_age_desc}

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
1. **BOOKS (Structure Expert)** - Screenplay craft, beat engineering, act mechanics
2. **PLAYS (Dramatic Theory Expert)** - Dialogue, subtext, character psychology, theatrical technique
3. **SCRIPTS (Execution Expert)** - Visual storytelling, pacing, performance, modern romcom execution

YOUR TASK:
Synthesize all three perspectives into ONE comprehensive, actionable scene blueprint.

**SYNTHESIS DIRECTIVE:**
- If experts disagree, prioritize cinematic clarity and character truth
- Reference expert insights directly (e.g., "Books expert notes...", "Scripts suggests...")
- Bullet points only (five to seven per section)
- Target length: 800-1200 tokens total

OUTPUT FORMAT (use these exact sections):

## SCENE_BLUEPRINT

### EXECUTIVE_SUMMARY
[Three to five sentence overview of this scene purpose and execution approach]

### STRUCTURAL_FUNCTION
- What this scene accomplishes in overall story
- Which beat/turning point it represents
- How it advances plot and character arcs

### DRAMATIC_BEATS
- Opening state/situation
- Key turning points within scene
- Closing state and what has changed
- Transition to next scene

### DIALOGUE_AND_SUBTEXT
- Tone and pacing of dialogue
- Surface vs. hidden meaning
- Wordplay, wit, verbal sparring opportunities
- Power dynamics and objectives

### VISUAL_AND_STAGING
- Opening image/establishing shot
- Key visual moments or physical comedy
- Camera approach and shot selection
- Setting/location utilization

### CHARACTER_PSYCHOLOGY
- Each character objective and tactics
- Emotional journey through scene
- Vulnerability or growth moments
- Relationship dynamics

### GOLDEN_AGE_EXECUTION
- Screwball/romcom tropes to employ
- Balance wit and physical comedy
- Sexual tension or romantic chemistry notes
- Classic film references or inspirations

### PITFALLS_TO_AVOID
- Common mistakes for this scene type
- What could fall flat or feel forced
- Tonal concerns

Be SPECIFIC, CONCRETE, ACTIONABLE. Reference expert insights directly."""

        # Combine bucket results
        expert_context = "\n\n".join([
            f"=== {result['bucket'].upper()} EXPERT ANALYSIS ===\n{result['response']}"
            for result in bucket_results
        ])

        # Call GPT-4o for synthesis
        try:
            client = AsyncOpenAI()
            response = await client.chat.completions.create(
                model="gpt-4o",
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

        # Query all three buckets
        bucket_results = []

        for bucket in self.buckets:
            result = await self.query_bucket_for_scene(scene, bucket)
            if result:
                bucket_results.append(result)

        # Synthesize insights
        if bucket_results:
            synthesized = await self.synthesize_expert_insights(scene, bucket_results)

            # IMPROVEMENT #16: Calculate confidence scores
            confidence_scores = self.calculate_expert_agreement(bucket_results)
            self.scene_confidence_scores[scene_num] = confidence_scores

            # Save to database
            self._save_brainstorm_session(scene, bucket_results, synthesized)

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
