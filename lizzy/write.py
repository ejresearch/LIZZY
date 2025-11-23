"""
Lizzy WRITE Module

Takes brainstorm blueprints and generates actual screenplay prose.

Process:
1. Load blueprint for a scene (from brainstorm session)
2. Add continuity context (previous/next scenes)
3. Apply golden-era romcom tone
4. Generate 700-900 word prose with GPT-4o
5. Save as draft in database
6. Display formatted result

Based on Lizzy white paper and Old Ender v3.
"""

import os
import sqlite3
from datetime import datetime
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from openai import AsyncOpenAI
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich import print as rprint

console = Console()


# Golden-era romcom tone (from Old Ender)
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


@dataclass
class SceneContext:
    """Context needed to write a scene"""
    scene_id: int  # Database ID
    scene_number: int
    title: str
    description: str
    characters: str
    tone: Optional[str]
    blueprint: Optional[str]  # From brainstorm
    previous_draft: Optional[str]  # Previous scene's final draft
    next_outline: Optional[str]  # Next scene's description


@dataclass
class Draft:
    """A generated draft"""
    scene_id: int  # Database ID
    scene_number: int  # For display
    content: str
    version: int
    word_count: int
    tokens_used: int
    cost_estimate: float
    created_at: str


class WriteModule:
    """
    Core WRITE module - blueprint to prose converter
    """

    def __init__(self, project_name: str):
        self.project_name = project_name
        self.db_path = f"projects/{project_name}/{project_name}.db"

        # Initialize OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        self.client = AsyncOpenAI(api_key=api_key)

        # Initialize screenplay formatter
        from .screenplay_writer import ScreenplayWriter
        self.screenplay_writer = ScreenplayWriter(project_name)

        # Ensure drafts table exists
        self._init_drafts_table()

    def _init_drafts_table(self):
        """Create scene_drafts table if it doesn't exist"""
        conn = sqlite3.connect(self.db_path)
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
        conn.close()

    def load_scene_context(self, scene_number: int) -> Optional[SceneContext]:
        """
        Load all context needed to write a scene.

        Args:
            scene_number: Which scene to load

        Returns:
            SceneContext with all data, or None if scene not found
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get current scene
        cursor.execute("""
            SELECT id, scene_number, title, description, characters, tone
            FROM scenes
            WHERE scene_number = ?
        """, (scene_number,))

        scene = cursor.fetchone()
        if not scene:
            conn.close()
            return None

        # Get blueprint from most recent brainstorm session
        cursor.execute("""
            SELECT bs.content
            FROM brainstorm_sessions bs
            JOIN scenes s ON bs.scene_id = s.id
            WHERE s.scene_number = ?
            ORDER BY bs.created_at DESC
            LIMIT 1
        """, (scene_number,))

        blueprint_row = cursor.fetchone()
        blueprint = blueprint_row['content'] if blueprint_row else None

        # Get previous scene's draft (for continuity)
        previous_draft = None
        if scene_number > 1:
            cursor.execute("""
                SELECT sd.content
                FROM scene_drafts sd
                JOIN scenes s ON sd.scene_id = s.id
                WHERE s.scene_number = ?
                ORDER BY sd.version DESC
                LIMIT 1
            """, (scene_number - 1,))

            prev_row = cursor.fetchone()
            previous_draft = prev_row['content'] if prev_row else None

        # Get next scene's outline (for foreshadowing)
        next_outline = None
        if scene_number < 30:
            cursor.execute("""
                SELECT description
                FROM scenes
                WHERE scene_number = ?
            """, (scene_number + 1,))

            next_row = cursor.fetchone()
            next_outline = next_row['description'] if next_row else None

        conn.close()

        return SceneContext(
            scene_id=scene['id'],
            scene_number=scene['scene_number'],
            title=scene['title'],
            description=scene['description'],
            characters=scene['characters'],
            tone=scene['tone'],
            blueprint=blueprint,
            previous_draft=previous_draft,
            next_outline=next_outline
        )

    async def generate_draft(
        self,
        context: SceneContext,
        model: str = "gpt-5",
        target_words: int = 800
    ) -> Draft:
        """
        Generate screenplay prose from blueprint.

        Args:
            context: Scene context with blueprint
            model: Which OpenAI model to use
            target_words: Target word count (700-900)

        Returns:
            Draft object with generated prose
        """

        # Build the prompt
        prompt = self._build_write_prompt(context, target_words)

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

        return Draft(
            scene_id=context.scene_id,
            scene_number=context.scene_number,
            content=content,
            version=self._get_next_version(context.scene_id),
            word_count=word_count,
            tokens_used=tokens_used,
            cost_estimate=cost,
            created_at=datetime.now().isoformat()
        )

    def _build_write_prompt(self, context: SceneContext, target_words: int) -> str:
        """Build the prompt for draft generation"""

        prompt_parts = []

        # Scene basics
        prompt_parts.append(f"**SCENE {context.scene_number}: {context.title}**")
        prompt_parts.append(f"\nDescription: {context.description}")
        prompt_parts.append(f"Characters: {context.characters}")

        if context.tone:
            prompt_parts.append(f"Tone: {context.tone}")

        # Blueprint (the key input!)
        if context.blueprint:
            prompt_parts.append(f"\n**BLUEPRINT FROM BRAINSTORM:**\n{context.blueprint}")
        else:
            prompt_parts.append("\n**NO BLUEPRINT AVAILABLE** - Write based on description only.")

        # Continuity context
        if context.previous_draft:
            prev_preview = context.previous_draft[:300] + "..." if len(context.previous_draft) > 300 else context.previous_draft
            prompt_parts.append(f"\n**PREVIOUS SCENE (for continuity):**\n{prev_preview}")

        if context.next_outline:
            prompt_parts.append(f"\n**NEXT SCENE (to foreshadow):**\n{context.next_outline}")

        # Instructions
        prompt_parts.append(f"""

**YOUR TASK:**
Write this scene in PROPER SCREENPLAY FORMAT following industry standards.

TARGET: {target_words} words / 2-3 pages (1 page ≈ 1 minute of screen time)

SCREENPLAY FORMAT REQUIREMENTS:
1. Scene heading: INT./EXT. LOCATION - TIME (all caps, flush left)
2. Action lines: Present tense, active voice, visual descriptions
3. Character names: ALL CAPS, centered before dialogue
4. Dialogue: Under character name, indented properly
5. Parentheticals: (brief acting directions) in parentheses
6. Transitions: CUT TO:, DISSOLVE TO:, etc. (flush right when needed)

CONTENT REQUIREMENTS:
1. Show character emotions through actions, NOT exposition
2. Make dialogue witty, natural, and character-specific
3. Build romantic/comedic tension
4. Maintain continuity with previous scene
5. Set up next scene organically
6. Include specific visual details and character reactions

FORMATTING EXAMPLES:
```
INT. COFFEE SHOP - DAY

The morning rush. Sunlight streams through large windows. SARAH (30s,
professional attire) scans the crowded room.

She spots an empty table and hurries over.

                    SARAH
          (to herself)
Finally.

JAKE (20s, barista apron) approaches with a coffee pot.

                    JAKE
Morning, Sarah. The usual?

                    SARAH
          (smiling)
You know me too well.
```

Write the complete scene now in proper screenplay format:
""")

        return "\n".join(prompt_parts)

    def save_draft(self, draft: Draft) -> int:
        """
        Save draft to database.

        Returns:
            Draft ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO scene_drafts (
                scene_id, content, version, word_count,
                tokens_used, cost_estimate, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            draft.scene_id,
            draft.content,
            draft.version,
            draft.word_count,
            draft.tokens_used,
            draft.cost_estimate,
            draft.created_at
        ))

        draft_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return draft_id

    def _get_next_version(self, scene_id: int) -> int:
        """Get next version number for a scene"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT MAX(version) as max_version
            FROM scene_drafts
            WHERE scene_id = ?
        """, (scene_id,))

        result = cursor.fetchone()
        conn.close()

        max_version = result[0] if result[0] else 0
        return max_version + 1

    def _estimate_cost(self, model: str, tokens: int) -> float:
        """Estimate cost based on model and tokens"""
        cost_per_1m = {
            "gpt-5": 10.0,
            "gpt-5.1": 0.40,
        }

        rate = cost_per_1m.get(model, 10.0)
        return (tokens / 1_000_000) * rate

    def get_all_drafts(self, scene_number: int) -> List[Draft]:
        """Get all drafts for a scene"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT sd.scene_id, s.scene_number, sd.content, sd.version, sd.word_count,
                   sd.tokens_used, sd.cost_estimate, sd.created_at
            FROM scene_drafts sd
            JOIN scenes s ON sd.scene_id = s.id
            WHERE s.scene_number = ?
            ORDER BY sd.version DESC
        """, (scene_number,))

        rows = cursor.fetchall()
        conn.close()

        return [Draft(**dict(row)) for row in rows]

    def export_draft(
        self,
        draft: Draft,
        output_format: str = "docx",
        validate: bool = True
    ) -> tuple[str, bool, list[str]]:
        """
        Export a draft as a formatted screenplay.

        Args:
            draft: The draft to export
            output_format: Format to export (txt, docx, pdf)
            validate: Whether to validate the screenplay

        Returns:
            tuple of (output_path, is_valid, validation_errors)
        """
        return self.screenplay_writer.format_scene(
            raw_screenplay=draft.content,
            scene_number=draft.scene_number,
            output_format=output_format,
            validate=validate
        )

    def get_formatted_preview(self, draft: Draft, max_lines: int = 50) -> str:
        """
        Get a formatted preview of a draft.

        Args:
            draft: The draft to preview
            max_lines: Max lines to show

        Returns:
            Formatted screenplay text (truncated)
        """
        return self.screenplay_writer.get_formatted_preview(
            raw_screenplay=draft.content,
            max_lines=max_lines
        )

    def validate_draft(self, draft: Draft):
        """
        Validate a draft's screenplay formatting.

        Returns:
            ValidationReport with validation results
        """
        return self.screenplay_writer.validate_screenplay(draft.content)

    def display_draft(self, draft: Draft):
        """Display a draft with Rich formatting"""

        console.print(f"\n[bold cyan]Scene {draft.scene_number} - Draft v{draft.version}[/bold cyan]")

        # Get formatted preview
        formatted_preview = self.get_formatted_preview(draft, max_lines=40)

        console.print(Panel(
            formatted_preview,
            title=f"📝 Formatted Screenplay (v{draft.version})",
            border_style="green"
        ))

        # Validate
        validation_report = self.validate_draft(draft)
        if not validation_report.passed:
            console.print(f"\n[yellow]⚠️  Formatting issues:[/yellow]")
            for error in validation_report.errors[:3]:  # Show first 3 errors
                console.print(f"  • {error}")
        else:
            console.print(f"\n[green]✓ Screenplay formatting validated[/green]")

        console.print(f"\n[dim]Words: {draft.word_count} | Tokens: {draft.tokens_used} | Cost: ${draft.cost_estimate:.4f}[/dim]")
        console.print(f"[dim]Created: {draft.created_at}[/dim]\n")


async def main():
    """Main CLI for WRITE module"""

    console.print("\n[bold magenta]╔═══════════════════════════════════════╗[/bold magenta]")
    console.print("[bold magenta]║     WRITE - Draft Generation          ║[/bold magenta]")
    console.print("[bold magenta]╚═══════════════════════════════════════╝[/bold magenta]\n")

    # Get project name
    project_name = Prompt.ask("Project name", default="the_proposal_2_0")

    writer = WriteModule(project_name)

    while True:
        console.print("\n[bold cyan]Options:[/bold cyan]")
        console.print("1. Write a scene (generate draft)")
        console.print("2. View drafts for a scene")
        console.print("3. Export draft as screenplay (TXT/DOCX/PDF)")
        console.print("4. Exit")

        choice = Prompt.ask("Choose", choices=["1", "2", "3", "4"], default="1")

        if choice == "1":
            # Generate a draft
            scene_num = int(Prompt.ask("Scene number", default="1"))

            console.print(f"\n[yellow]📖 Loading context for Scene {scene_num}...[/yellow]")

            context = writer.load_scene_context(scene_num)

            if not context:
                console.print(f"[red]❌ Scene {scene_num} not found![/red]")
                continue

            # Show context
            console.print(f"\n[bold]Scene {context.scene_number}: {context.title}[/bold]")
            console.print(f"[dim]{context.description}[/dim]")

            if context.blueprint:
                console.print(f"\n[green]✅ Blueprint found[/green]")
            else:
                console.print(f"\n[yellow]⚠️  No blueprint - will write from description only[/yellow]")

            if not Confirm.ask("\nGenerate draft?"):
                continue

            console.print(f"\n[yellow]✍️  Generating draft... This may take 20-30 seconds...[/yellow]\n")

            draft = await writer.generate_draft(context)

            # Save
            draft_id = writer.save_draft(draft)

            console.print(f"[green]✅ Saved as Draft v{draft.version} (ID: {draft_id})[/green]")

            # Display
            writer.display_draft(draft)

        elif choice == "2":
            # View drafts
            scene_num = int(Prompt.ask("Scene number", default="1"))

            drafts = writer.get_all_drafts(scene_num)

            if not drafts:
                console.print(f"\n[yellow]No drafts found for Scene {scene_num}[/yellow]")
                continue

            console.print(f"\n[bold]Found {len(drafts)} draft(s) for Scene {scene_num}:[/bold]\n")

            for draft in drafts:
                console.print(f"[cyan]v{draft.version}[/cyan] - {draft.word_count} words - {draft.created_at}")

            which = int(Prompt.ask("\nView which version?", default="1"))

            selected = next((d for d in drafts if d.version == which), None)

            if selected:
                writer.display_draft(selected)
            else:
                console.print(f"[red]Version {which} not found[/red]")

        elif choice == "3":
            # Export draft
            scene_num = int(Prompt.ask("Scene number", default="1"))

            drafts = writer.get_all_drafts(scene_num)

            if not drafts:
                console.print(f"\n[yellow]No drafts found for Scene {scene_num}[/yellow]")
                continue

            # Show available drafts
            console.print(f"\n[bold]Found {len(drafts)} draft(s) for Scene {scene_num}:[/bold]\n")
            for draft in drafts:
                console.print(f"[cyan]v{draft.version}[/cyan] - {draft.word_count} words - {draft.created_at}")

            which = int(Prompt.ask("\nExport which version?", default=str(drafts[-1].version)))
            selected = next((d for d in drafts if d.version == which), None)

            if not selected:
                console.print(f"[red]Version {which} not found[/red]")
                continue

            # Choose format
            format_choice = Prompt.ask(
                "Export format",
                choices=["txt", "docx", "pdf"],
                default="docx"
            )

            console.print(f"\n[yellow]⏳ Formatting and exporting...[/yellow]")

            # Export
            output_path, is_valid, errors = writer.export_draft(selected, format_choice)

            console.print(f"\n[green]✅ Exported to: {output_path}[/green]")

            if not is_valid:
                console.print(f"\n[yellow]⚠️  Formatting warnings ({len(errors)} issues):[/yellow]")
                for error in errors[:5]:
                    console.print(f"  • {error}")
            else:
                console.print(f"[green]✓ Screenplay formatting validated[/green]")

        elif choice == "4":
            console.print("\n[green]Goodbye![/green]\n")
            break


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
