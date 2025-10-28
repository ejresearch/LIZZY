"""
EXPORT Module - Compile Scene Drafts to Screenplay Formats

Takes all scene drafts from database and compiles them into:
- Plain text (.txt)
- Markdown (.md)
- Fountain format (.fountain) - industry-standard screenplay markup
- Final Draft XML (.fdx) - compatible with Final Draft software

Supports:
- Version selection (use latest or specific versions)
- Act breaks and headers
- Title page generation
- Scene numbering
- Multiple output formats
"""

import os
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.table import Table
from .database import Database

console = Console()


class ScreenplayExporter:
    """
    Compile scene drafts into various screenplay formats.
    """

    def __init__(self, db_path: Path):
        """
        Initialize exporter.

        Args:
            db_path: Path to project database
        """
        self.db_path = db_path
        self.db = Database(db_path)
        self.project = None
        self.scenes = []
        self.drafts = []

    def load_project(self):
        """Load project metadata"""
        self.project = self.db.get_project()

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, scene_number, title, description, act
                FROM scenes
                ORDER BY scene_number
            """)
            self.scenes = [dict(row) for row in cursor.fetchall()]

    def load_drafts(self, version_preference: str = "latest") -> bool:
        """
        Load scene drafts from database.

        Args:
            version_preference: "latest" or specific version number

        Returns:
            True if all scenes have drafts, False otherwise
        """
        self.drafts = []

        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            for scene in self.scenes:
                if version_preference == "latest":
                    cursor.execute("""
                        SELECT content, version, word_count
                        FROM scene_drafts
                        WHERE scene_id = ?
                        ORDER BY version DESC
                        LIMIT 1
                    """, (scene['id'],))
                else:
                    cursor.execute("""
                        SELECT content, version, word_count
                        FROM scene_drafts
                        WHERE scene_id = ? AND version = ?
                        LIMIT 1
                    """, (scene['id'], int(version_preference)))

                row = cursor.fetchone()

                if row:
                    self.drafts.append({
                        'scene_number': scene['scene_number'],
                        'scene_title': scene['title'],
                        'content': row['content'],
                        'version': row['version'],
                        'word_count': row['word_count'],
                        'act': scene.get('act', self._infer_act(scene['scene_number']))
                    })
                else:
                    # Missing draft
                    console.print(
                        f"[yellow]⚠ Scene {scene['scene_number']} has no draft "
                        f"(version: {version_preference})[/yellow]"
                    )
                    return False

        return True

    def _infer_act(self, scene_number: int) -> int:
        """Infer act number from scene number (30-beat structure)"""
        if scene_number <= 10:
            return 1
        elif scene_number <= 20:
            return 2
        else:
            return 3

    def _generate_title_page(self) -> str:
        """Generate screenplay title page"""
        title = self.project.get('title', 'Untitled Screenplay')
        author = self.project.get('author', 'Anonymous')
        logline = self.project.get('logline', '')
        date = datetime.now().strftime("%B %d, %Y")

        title_page = f"""
                                {title.upper()}


                                    by

                                 {author}




        {logline if logline else ''}





                                                    Generated: {date}
                                                    Via Lizzy 2.0
"""
        return title_page

    def export_to_text(self, output_path: Path) -> None:
        """
        Export to plain text format.

        Args:
            output_path: Where to save the file
        """
        lines = []

        # Title page
        lines.append(self._generate_title_page())
        lines.append("\n" + "="*80 + "\n\n")

        # Scenes
        current_act = 0

        for draft in self.drafts:
            # Act break
            if draft['act'] != current_act:
                current_act = draft['act']
                lines.append(f"\n\n{'='*80}\n")
                lines.append(f"ACT {current_act}\n")
                lines.append(f"{'='*80}\n\n")

            # Scene header
            lines.append(f"\n--- SCENE {draft['scene_number']}: {draft['scene_title'].upper()} ---\n\n")

            # Scene content
            lines.append(draft['content'])
            lines.append("\n\n")

        # Write file
        output_path.write_text("\n".join(lines))
        console.print(f"[green]✓ Exported to:[/green] {output_path}")

    def export_to_markdown(self, output_path: Path) -> None:
        """
        Export to markdown format.

        Args:
            output_path: Where to save the file
        """
        lines = []

        # Title page
        title = self.project.get('title', 'Untitled Screenplay')
        author = self.project.get('author', 'Anonymous')
        logline = self.project.get('logline', '')

        lines.append(f"# {title}\n")
        lines.append(f"**by {author}**\n\n")

        if logline:
            lines.append(f"> {logline}\n\n")

        lines.append(f"*Generated: {datetime.now().strftime('%B %d, %Y')} via Lizzy 2.0*\n\n")
        lines.append("---\n\n")

        # Scenes
        current_act = 0

        for draft in self.drafts:
            # Act break
            if draft['act'] != current_act:
                current_act = draft['act']
                lines.append(f"\n## Act {current_act}\n\n")

            # Scene header
            lines.append(f"### Scene {draft['scene_number']}: {draft['scene_title']}\n\n")

            # Scene content
            lines.append(draft['content'])
            lines.append("\n\n")

        # Write file
        output_path.write_text("\n".join(lines))
        console.print(f"[green]✓ Exported to:[/green] {output_path}")

    def export_to_fountain(self, output_path: Path) -> None:
        """
        Export to Fountain format (industry-standard screenplay markup).

        Fountain can be imported into Final Draft, Highland, Fade In, etc.

        Args:
            output_path: Where to save the file
        """
        lines = []

        # Title page (Fountain format)
        title = self.project.get('title', 'Untitled Screenplay')
        author = self.project.get('author', 'Anonymous')
        logline = self.project.get('logline', '')

        lines.append(f"Title: {title}")
        lines.append(f"Author: {author}")
        lines.append(f"Draft date: {datetime.now().strftime('%m/%d/%Y')}")
        if logline:
            lines.append(f"Logline: {logline}")
        lines.append("")  # Blank line ends title page

        # Scenes
        current_act = 0

        for draft in self.drafts:
            # Act break
            if draft['act'] != current_act:
                current_act = draft['act']
                lines.append(f"\n# ACT {current_act}\n")

            # Scene heading (must start with INT. or EXT.)
            # Since we have prose, we'll use a generic scene heading
            scene_heading = f"INT./EXT. SCENE {draft['scene_number']} - {draft['scene_title'].upper()}"
            lines.append(f"\n{scene_heading}\n")

            # Scene content
            # Note: Fountain expects traditional screenplay format
            # Since we have prose, we'll add it as action blocks
            lines.append(draft['content'])
            lines.append("")

        # Write file
        output_path.write_text("\n".join(lines))
        console.print(f"[green]✓ Exported to:[/green] {output_path}")

    def export_to_final_draft(self, output_path: Path) -> None:
        """
        Export to Final Draft XML format (.fdx).

        Creates a minimal but valid Final Draft file.

        Args:
            output_path: Where to save the file
        """
        title = self.project.get('title', 'Untitled Screenplay')
        author = self.project.get('author', 'Anonymous')

        # Build FDX XML
        fdx_lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<FinalDraft DocumentType="Script" Template="No" Version="5">',
            f'  <Content>',
            f'    <Paragraph Type="Title">',
            f'      <Text>{self._escape_xml(title)}</Text>',
            f'    </Paragraph>',
            f'    <Paragraph Type="Authors">',
            f'      <Text>by {self._escape_xml(author)}</Text>',
            f'    </Paragraph>',
            f'    <Paragraph Type="Action">',
            f'      <Text></Text>',
            f'    </Paragraph>',
        ]

        current_act = 0

        for draft in self.drafts:
            # Act break
            if draft['act'] != current_act:
                current_act = draft['act']
                fdx_lines.append(f'    <Paragraph Type="Action">')
                fdx_lines.append(f'      <Text>ACT {current_act}</Text>')
                fdx_lines.append(f'    </Paragraph>')

            # Scene heading
            scene_heading = f"SCENE {draft['scene_number']}: {draft['scene_title'].upper()}"
            fdx_lines.append(f'    <Paragraph Type="Scene Heading">')
            fdx_lines.append(f'      <Text>{self._escape_xml(scene_heading)}</Text>')
            fdx_lines.append(f'    </Paragraph>')

            # Scene content (as action)
            # Split by paragraphs
            paragraphs = draft['content'].split('\n\n')
            for para in paragraphs:
                if para.strip():
                    fdx_lines.append(f'    <Paragraph Type="Action">')
                    fdx_lines.append(f'      <Text>{self._escape_xml(para.strip())}</Text>')
                    fdx_lines.append(f'    </Paragraph>')

        fdx_lines.append('  </Content>')
        fdx_lines.append('</FinalDraft>')

        # Write file
        output_path.write_text("\n".join(fdx_lines))
        console.print(f"[green]✓ Exported to:[/green] {output_path}")

    def _escape_xml(self, text: str) -> str:
        """Escape XML special characters"""
        return (text
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&apos;"))

    def show_draft_stats(self):
        """Display statistics about loaded drafts"""
        if not self.drafts:
            console.print("[yellow]No drafts loaded[/yellow]")
            return

        total_words = sum(d['word_count'] for d in self.drafts)
        total_scenes = len(self.drafts)

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Total Scenes", str(total_scenes))
        table.add_row("Total Words", f"{total_words:,}")
        table.add_row("Avg Words/Scene", f"{total_words // total_scenes:,}")
        table.add_row("Est. Pages (250 words/page)", f"{total_words // 250:,}")

        console.print(table)
        console.print()


async def main():
    """Main CLI for EXPORT"""

    console.print("\n[bold magenta]╔═══════════════════════════════════════╗[/bold magenta]")
    console.print("[bold magenta]║      EXPORT - Screenplay Compiler      ║[/bold magenta]")
    console.print("[bold magenta]╚═══════════════════════════════════════╝[/bold magenta]\n")

    # List available projects
    projects_dir = Path("projects")
    if not projects_dir.exists():
        console.print("[red]No projects directory found![/red]")
        return

    project_dirs = [d for d in projects_dir.iterdir() if d.is_dir()]

    if not project_dirs:
        console.print("[red]No projects found![/red]")
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

    # Initialize exporter
    exporter = ScreenplayExporter(db_path)
    exporter.load_project()

    console.print(f"[dim]Project: {exporter.project.get('title', 'Untitled')}[/dim]")
    console.print(f"[dim]Scenes: {len(exporter.scenes)}[/dim]\n")

    # Version selection
    console.print("[bold cyan]Version Selection:[/bold cyan]")
    console.print("1. Use latest version of each scene")
    console.print("2. Use specific version number")

    version_choice = Prompt.ask(
        "\nChoose version strategy",
        choices=["1", "2"],
        default="1"
    )

    version_pref = "latest"
    if version_choice == "2":
        version_pref = Prompt.ask("Version number", default="1")

    # Load drafts
    console.print(f"\n[yellow]Loading drafts (version: {version_pref})...[/yellow]\n")

    success = exporter.load_drafts(version_preference=version_pref)

    if not success:
        console.print("\n[red]Cannot export: Some scenes are missing drafts[/red]")
        console.print("[yellow]Run WRITE module first to generate all scene drafts[/yellow]\n")
        return

    # Show stats
    console.print("[bold green]✓ All drafts loaded![/bold green]\n")
    exporter.show_draft_stats()

    # Choose export formats
    console.print("[bold cyan]Export Formats:[/bold cyan]")
    console.print("1. Plain Text (.txt)")
    console.print("2. Markdown (.md)")
    console.print("3. Fountain (.fountain)")
    console.print("4. Final Draft XML (.fdx)")
    console.print("5. All formats")

    format_choice = Prompt.ask(
        "\nChoose format",
        choices=["1", "2", "3", "4", "5"],
        default="5"
    )

    # Prepare output directory
    exports_dir = selected_project / "exports"
    exports_dir.mkdir(exist_ok=True)

    # Generate base filename
    title = exporter.project.get('title', selected_project.name)
    safe_title = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in title)
    safe_title = safe_title.replace(' ', '_').lower()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_filename = f"{safe_title}_v{version_pref}_{timestamp}"

    # Export
    console.print(f"\n[yellow]Exporting...[/yellow]\n")

    formats_to_export = []
    if format_choice == "1":
        formats_to_export = ["txt"]
    elif format_choice == "2":
        formats_to_export = ["md"]
    elif format_choice == "3":
        formats_to_export = ["fountain"]
    elif format_choice == "4":
        formats_to_export = ["fdx"]
    else:
        formats_to_export = ["txt", "md", "fountain", "fdx"]

    for fmt in formats_to_export:
        output_path = exports_dir / f"{base_filename}.{fmt}"

        if fmt == "txt":
            exporter.export_to_text(output_path)
        elif fmt == "md":
            exporter.export_to_markdown(output_path)
        elif fmt == "fountain":
            exporter.export_to_fountain(output_path)
        elif fmt == "fdx":
            exporter.export_to_final_draft(output_path)

    console.print(f"\n[bold green]✓ Export complete![/bold green]")
    console.print(f"[dim]Output directory: {exports_dir}[/dim]\n")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
