"""
Automated WRITE - Batch Scene Prose Generation

Processes all 30 scenes from blueprints to screenplay prose.
Uses feed-forward context where each scene benefits from the previous scene's draft.

Process for each scene:
1. Load scene blueprint (from brainstorm)
2. Add continuity (previous scene draft)
3. Add foreshadowing (next scene outline)
4. Generate 700-900 word prose with GPT-4o
5. Save versioned draft to database
6. Show progress and costs
"""

import asyncio
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from openai import AsyncOpenAI
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from .database import Database
import os

console = Console()


# Golden-era romcom tone (from write.py)
GOLDEN_ERA_ROMCOM_TONE = """You are writing a romantic comedy that revives the golden era of the genre—
When Harry Met Sally, You've Got Mail, Pretty Woman, Sleepless in Seattle, Notting Hill.

PRINCIPLES:
• Genuine emotional stakes and vulnerability
• Witty, quotable dialogue that reveals character and advances plot
• Earned romantic moments and clear "why them" chemistry
• Universal yet specific conflicts (career vs love, timing, class, baggage)
• Memorable set pieces; heart over hijinks; humor from truth, not humiliation

AVOID:
• Contrived misunderstandings solvable by one conversation
• Cruelty or mean-spirited humor
• Humiliation comedy
• Relationships without foundation
"""


class AutomatedWrite:
    """
    Batch process all 30 scenes from blueprints to prose.

    Feed-forward architecture:
    - Scene 1: No previous context
    - Scene 2: Gets Scene 1's draft for continuity
    - Scene 30: Gets Scene 29's draft, understands full journey
    """

    def __init__(self, db_path: Path):
        """
        Initialize Automated Write.

        Args:
            db_path: Path to project database
        """
        self.db_path = db_path
        self.db = Database(db_path)
        self.project = None
        self.scenes = []
        self.total_cost = 0.0
        self.total_tokens = 0
        self.total_words = 0

        # Initialize OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        self.client = AsyncOpenAI(api_key=api_key)

        # Ensure scene_drafts table exists
        self._init_drafts_table()

    def _init_drafts_table(self):
        """Create scene_drafts table if it doesn't exist"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scene_drafts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scene_id INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    version INTEGER DEFAULT 1,
                    word_count INTEGER,
                    tokens_used INTEGER,
                    cost_estimate REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (scene_id) REFERENCES scenes(id)
                )
            """)
            conn.commit()

    def load_project_context(self) -> None:
        """Load project metadata and all scenes"""
        self.project = self.db.get_project()

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, scene_number, title, description, characters, tone
                FROM scenes
                ORDER BY scene_number
            """)
            self.scenes = [dict(row) for row in cursor.fetchall()]

    def get_scene_blueprint(self, scene_id: int) -> Optional[str]:
        """
        Get most recent blueprint for a scene.

        Args:
            scene_id: Scene database ID

        Returns:
            Blueprint content or None
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT content
                FROM brainstorm_sessions
                WHERE scene_id = ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (scene_id,))

            row = cursor.fetchone()
            return row['content'] if row else None

    def get_previous_draft(self, scene_number: int) -> Optional[str]:
        """
        Get previous scene's most recent draft (for continuity).

        Args:
            scene_number: Current scene number

        Returns:
            Previous scene's draft or None
        """
        if scene_number <= 1:
            return None

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT sd.content
                FROM scene_drafts sd
                JOIN scenes s ON sd.scene_id = s.id
                WHERE s.scene_number = ?
                ORDER BY sd.version DESC
                LIMIT 1
            """, (scene_number - 1,))

            row = cursor.fetchone()
            return row['content'] if row else None

    def get_next_outline(self, scene_number: int) -> Optional[str]:
        """
        Get next scene's description (for foreshadowing).

        Args:
            scene_number: Current scene number

        Returns:
            Next scene's description or None
        """
        if scene_number >= 30:
            return None

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT description
                FROM scenes
                WHERE scene_number = ?
            """, (scene_number + 1,))

            row = cursor.fetchone()
            return row['description'] if row else None

    def _get_next_version(self, scene_id: int) -> int:
        """Get next version number for a scene"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT MAX(version) as max_version
                FROM scene_drafts
                WHERE scene_id = ?
            """, (scene_id,))

            result = cursor.fetchone()
            max_version = result['max_version'] if result['max_version'] else 0
            return max_version + 1

    def _build_write_prompt(
        self,
        scene: Dict,
        blueprint: Optional[str],
        previous_draft: Optional[str],
        next_outline: Optional[str],
        target_words: int = 800
    ) -> str:
        """
        Build prompt for draft generation.

        Args:
            scene: Scene dict with metadata
            blueprint: Blueprint from brainstorm
            previous_draft: Previous scene's draft
            next_outline: Next scene's description
            target_words: Target word count

        Returns:
            Complete prompt string
        """
        prompt_parts = []

        # Scene basics
        prompt_parts.append(f"**SCENE {scene['scene_number']}: {scene['title']}**")
        prompt_parts.append(f"\nDescription: {scene['description']}")
        prompt_parts.append(f"Characters: {scene['characters']}")

        if scene.get('tone'):
            prompt_parts.append(f"Tone: {scene['tone']}")

        # Blueprint (the key input!)
        if blueprint:
            prompt_parts.append(f"\n**BLUEPRINT FROM BRAINSTORM:**\n{blueprint}")
        else:
            prompt_parts.append("\n**NO BLUEPRINT AVAILABLE** - Write based on description only.")

        # Continuity context
        if previous_draft:
            prev_preview = previous_draft[:400] + "..." if len(previous_draft) > 400 else previous_draft
            prompt_parts.append(f"\n**PREVIOUS SCENE (for continuity):**\n{prev_preview}")

        if next_outline:
            prompt_parts.append(f"\n**NEXT SCENE (to foreshadow):**\n{next_outline}")

        # Instructions
        prompt_parts.append(f"""

**YOUR TASK:**
Write this scene as screenplay prose (NOT script format).

TARGET: {target_words} words (700-900 range)

REQUIREMENTS:
1. Write in present tense, active voice
2. Include vivid action and dialogue
3. Show character emotions through actions, not exposition
4. Make dialogue witty, natural, and character-specific
5. Build romantic/comedic tension
6. Maintain continuity with previous scene
7. Set up next scene organically

STRUCTURE:
- Opening: Establish setting and mood (50-100 words)
- Rising action: Character interactions, conflict emerges (400-500 words)
- Peak moment: Key beat or turning point (150-200 words)
- Resolution: Scene conclusion that propels story forward (100-150 words)

Write the scene now:
""")

        return "\n".join(prompt_parts)

    def _estimate_cost(self, model: str, tokens: int) -> float:
        """Estimate cost based on model and tokens"""
        # GPT-4o pricing (as of 2025)
        cost_per_1m = {
            "gpt-5": 2.50,  # Input: $2.50/1M, Output: $10/1M (average ~$5/1M)
            "gpt-5.1": 0.15,  # Input: $0.15/1M, Output: $0.60/1M (average ~$0.30/1M)
        }

        rate = cost_per_1m.get(model, 5.0)
        return (tokens / 1_000_000) * rate

    async def generate_scene_draft(
        self,
        scene: Dict,
        model: str = "gpt-5",
        target_words: int = 800
    ) -> Dict:
        """
        Generate prose for a single scene.

        Args:
            scene: Scene dict
            model: OpenAI model
            target_words: Target word count

        Returns:
            Dict with draft data
        """
        # Load context
        blueprint = self.get_scene_blueprint(scene['id'])
        previous_draft = self.get_previous_draft(scene['scene_number'])
        next_outline = self.get_next_outline(scene['scene_number'])

        # Build prompt
        prompt = self._build_write_prompt(
            scene, blueprint, previous_draft, next_outline, target_words
        )

        # Call OpenAI
        response = await self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": GOLDEN_ERA_ROMCOM_TONE},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,  # Higher for creative prose
            max_tokens=2500
        )

        # Extract content
        content = response.choices[0].message.content

        # Calculate stats
        word_count = len(content.split())
        tokens_used = response.usage.total_tokens if response.usage else 0
        cost = self._estimate_cost(model, tokens_used)

        # Update totals
        self.total_cost += cost
        self.total_tokens += tokens_used
        self.total_words += word_count

        return {
            'scene_id': scene['id'],
            'scene_number': scene['scene_number'],
            'content': content,
            'version': self._get_next_version(scene['id']),
            'word_count': word_count,
            'tokens_used': tokens_used,
            'cost_estimate': cost,
            'created_at': datetime.now().isoformat()
        }

    def save_draft(self, draft: Dict) -> int:
        """
        Save draft to database.

        Args:
            draft: Draft dict

        Returns:
            Draft ID
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO scene_drafts (
                    scene_id, content, version, word_count,
                    tokens_used, cost_estimate, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                draft['scene_id'],
                draft['content'],
                draft['version'],
                draft['word_count'],
                draft['tokens_used'],
                draft['cost_estimate'],
                draft['created_at']
            ))

            draft_id = cursor.lastrowid
            conn.commit()

        return draft_id

    async def process_all_scenes(
        self,
        scene_range: Optional[tuple] = None,
        model: str = "gpt-5"
    ):
        """
        Process all scenes in sequence (feed-forward).

        Args:
            scene_range: Optional (start, end) tuple for partial processing
            model: OpenAI model to use
        """
        # Determine which scenes to process
        if scene_range:
            start, end = scene_range
            scenes_to_process = [s for s in self.scenes if start <= s['scene_number'] <= end]
        else:
            scenes_to_process = self.scenes

        total_scenes = len(scenes_to_process)

        console.print(f"\n[bold cyan]Processing {total_scenes} scenes...[/bold cyan]\n")

        # Progress tracking
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:

            task = progress.add_task(
                f"[cyan]Writing scenes with {model}...",
                total=total_scenes
            )

            for i, scene in enumerate(scenes_to_process, 1):
                scene_num = scene['scene_number']

                # Update progress
                progress.update(
                    task,
                    description=f"[cyan]Scene {scene_num}: {scene['title'][:30]}..."
                )

                # Generate draft
                draft = await self.generate_scene_draft(scene, model=model)

                # Save to database
                draft_id = self.save_draft(draft)

                # Show mini-summary
                console.print(
                    f"  [green]✓[/green] Scene {scene_num}: "
                    f"{draft['word_count']} words, "
                    f"${draft['cost_estimate']:.4f}"
                )

                # Update progress
                progress.update(task, advance=1)

        # Final summary
        self._show_summary(total_scenes)

    def _show_summary(self, total_scenes: int):
        """Show final summary of batch processing"""
        console.print(f"\n[bold green]✓ Batch WRITE Complete![/bold green]\n")

        # Stats table
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Scenes Processed", str(total_scenes))
        table.add_row("Total Words", f"{self.total_words:,}")
        table.add_row("Total Tokens", f"{self.total_tokens:,}")
        table.add_row("Total Cost", f"${self.total_cost:.2f}")
        table.add_row("Avg Words/Scene", f"{self.total_words // total_scenes:,}")
        table.add_row("Avg Cost/Scene", f"${self.total_cost / total_scenes:.4f}")

        console.print(table)
        console.print()


async def main():
    """Main CLI for automated WRITE"""

    console.print("\n[bold magenta]╔═══════════════════════════════════════╗[/bold magenta]")
    console.print("[bold magenta]║   AUTOMATED WRITE - Batch Prose Gen   ║[/bold magenta]")
    console.print("[bold magenta]╚═══════════════════════════════════════╝[/bold magenta]\n")

    # List available projects
    projects_dir = Path("projects")
    if not projects_dir.exists():
        console.print("[red]No projects directory found![/red]")
        console.print("Run [cyan]python3 -m backend.start[/cyan] first.\n")
        return

    project_dirs = [d for d in projects_dir.iterdir() if d.is_dir()]

    if not project_dirs:
        console.print("[red]No projects found![/red]")
        console.print("Run [cyan]python3 -m backend.start[/cyan] to create a project.\n")
        return

    # Show available projects
    console.print("[bold cyan]Available Projects:[/bold cyan]\n")
    for i, proj in enumerate(project_dirs, 1):
        console.print(f"{i}. {proj.name}")

    # Select project
    choice = Prompt.ask(
        "\nSelect project",
        choices=[str(i) for i in range(1, len(project_dirs) + 1)],
        default="1"
    )

    selected_project = project_dirs[int(choice) - 1]
    db_path = selected_project / f"{selected_project.name}.db"

    if not db_path.exists():
        console.print(f"[red]Database not found: {db_path}[/red]\n")
        return

    console.print(f"\n[green]Selected:[/green] {selected_project.name}\n")

    # Initialize writer
    writer = AutomatedWrite(db_path)
    writer.load_project_context()

    console.print(f"[dim]Project: {writer.project.get('title', 'Untitled')}[/dim]")
    console.print(f"[dim]Scenes available: {len(writer.scenes)}[/dim]\n")

    # Choose scene range
    console.print("[bold cyan]Scene Range Options:[/bold cyan]")
    console.print("1. All scenes (1-30)")
    console.print("2. Act 1 (scenes 1-10)")
    console.print("3. Act 2 (scenes 11-20)")
    console.print("4. Act 3 (scenes 21-30)")
    console.print("5. Custom range")

    range_choice = Prompt.ask(
        "\nChoose range",
        choices=["1", "2", "3", "4", "5"],
        default="1"
    )

    scene_range = None
    if range_choice == "2":
        scene_range = (1, 10)
    elif range_choice == "3":
        scene_range = (11, 20)
    elif range_choice == "4":
        scene_range = (21, 30)
    elif range_choice == "5":
        start = int(Prompt.ask("Start scene", default="1"))
        end = int(Prompt.ask("End scene", default="30"))
        scene_range = (start, end)

    # Choose model
    console.print("\n[bold cyan]Model Options:[/bold cyan]")
    console.print("1. gpt-5 (higher quality, ~$0.015/scene)")
    console.print("2. gpt-5.1 (faster/cheaper, ~$0.001/scene)")

    model_choice = Prompt.ask(
        "\nChoose model",
        choices=["1", "2"],
        default="1"
    )

    model = "gpt-5" if model_choice == "1" else "gpt-5.1"

    # Estimate cost
    if scene_range:
        num_scenes = scene_range[1] - scene_range[0] + 1
    else:
        num_scenes = len(writer.scenes)

    est_cost = num_scenes * (0.015 if model == "gpt-5" else 0.001)

    console.print(f"\n[yellow]Estimated cost: ${est_cost:.2f} for {num_scenes} scenes[/yellow]")

    if not Confirm.ask("\nProceed with batch write?"):
        console.print("\n[yellow]Cancelled.[/yellow]\n")
        return

    # Process scenes
    await writer.process_all_scenes(scene_range=scene_range, model=model)

    console.print("[bold green]All drafts saved to database![/bold green]")
    console.print(f"[dim]Database: {db_path}[/dim]\n")


if __name__ == "__main__":
    asyncio.run(main())
