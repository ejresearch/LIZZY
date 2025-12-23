"""
Edit Project Module - Project Content Editor

Purpose: Edit and manage characters, scenes, and metadata for existing projects.

Note: For creating NEW projects, use IDEATE instead:
    python -m backend.ideate_web     # Web UI (guided or quick mode)
    python -m backend.ideate --quick # CLI quick mode

This module is for editing projects AFTER they've been created.
"""

from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.panel import Panel
from .database import Database

console = Console()


class ProjectEditor:
    """
    Edit characters, scenes, and metadata for existing projects.

    Provides a Rich UI for:
    - Adding/editing/deleting characters
    - Adding/editing/deleting scenes
    - Managing writer notes
    - Viewing brainstorm sessions and drafts
    """

    def __init__(self, db_path: Path):
        """
        Initialize project editor.

        Args:
            db_path: Path to project database
        """
        self.db_path = db_path
        self.db = Database(db_path)

    def run_interactive(self) -> None:
        """
        Run interactive editing session.

        Main menu for managing project content.
        """
        while True:
            console.clear()
            self._show_status()

            console.print("\n[bold]What would you like to do?[/bold]")
            console.print("[1] Add character")
            console.print("[2] Add scene")
            console.print("[3] View all characters")
            console.print("[4] View all scenes")
            console.print("[5] Edit character")
            console.print("[6] Edit scene")
            console.print("[7] Delete character")
            console.print("[8] Delete scene")
            console.print("[9] Writer notes")
            console.print("[10] Project metadata")
            console.print("[11] View brainstorm sessions")
            console.print("[12] View drafts")
            console.print("[13] Exit")

            choice = Prompt.ask(
                "\nChoose an option",
                choices=["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13"],
                default="13"
            )

            if choice == "1":
                self._add_character()
            elif choice == "2":
                self._add_scene()
            elif choice == "3":
                self._view_characters()
            elif choice == "4":
                self._view_scenes()
            elif choice == "5":
                self._edit_character()
            elif choice == "6":
                self._edit_scene()
            elif choice == "7":
                self._delete_character()
            elif choice == "8":
                self._delete_scene()
            elif choice == "9":
                self._edit_writer_notes()
            elif choice == "10":
                self._edit_project_metadata()
            elif choice == "11":
                self._view_brainstorm_sessions()
            elif choice == "12":
                self._view_drafts()
            elif choice == "13":
                console.print("\n[green]Editing complete![/green]")
                console.print("\n[cyan]Next steps:[/cyan]")
                project = self.db.get_project()
                if project:
                    console.print(f"  python -m backend.automated_brainstorm")
                    console.print("  [dim](Generate creative ideas for your scenes)[/dim]")
                break

    def _show_status(self) -> None:
        """Display project status with counts for all tables."""
        project = self.db.get_project()

        if project:
            # Get counts for all tables
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM characters")
                char_count = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM scenes")
                scene_count = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM writer_notes")
                notes_count = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM brainstorm_sessions")
                brainstorm_count = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM drafts")
                draft_count = cursor.fetchone()[0]

            console.print(Panel.fit(
                f"[bold cyan]{project['name']}[/bold cyan] [dim](Edit Mode)[/dim]\n\n"
                f"Genre: {project['genre']}\n\n"
                f"[bold]Core Elements:[/bold]\n"
                f"  Characters: {char_count} | Scenes: {scene_count}\n"
                f"  Writer Notes: {'✓' if notes_count > 0 else '○'} | Project Metadata: ✓\n\n"
                f"[bold]Generated Content:[/bold]\n"
                f"  Brainstorm Sessions: {brainstorm_count} | Drafts: {draft_count}",
                border_style="cyan"
            ))

    def _add_character(self) -> None:
        """Add a new character."""
        console.print("\n[bold cyan]Add Character[/bold cyan]\n")

        name = Prompt.ask("Name")
        description = Prompt.ask("Description")
        role = Prompt.ask(
            "Role",
            choices=["protagonist", "love_interest", "antagonist", "supporting"],
            default="supporting"
        )

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO characters (name, description, role) VALUES (?, ?, ?)",
                (name, description, role)
            )

        console.print(f"\n[green]Added character:[/green] {name}")
        Prompt.ask("\n[dim]Press Enter to continue[/dim]", default="")

    def _add_scene(self) -> None:
        """Add a new scene."""
        console.print("\n[bold cyan]Add Scene[/bold cyan]\n")

        # Get next scene number
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(scene_number) FROM scenes")
            result = cursor.fetchone()
            next_number = (result[0] or 0) + 1

        scene_number = int(Prompt.ask("Scene number", default=str(next_number)))
        title = Prompt.ask("Title")
        description = Prompt.ask("Description")

        # Show available characters
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM characters")
            chars = [row[0] for row in cursor.fetchall()]

        if chars:
            console.print(f"\n[dim]Available characters: {', '.join(chars)}[/dim]")
            characters = Prompt.ask("Characters in this scene (comma-separated)", default="")
        else:
            characters = ""

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO scenes (scene_number, title, description, characters) VALUES (?, ?, ?, ?)",
                (scene_number, title, description, characters)
            )

        console.print(f"\n[green]Added scene {scene_number}:[/green] {title}")
        Prompt.ask("\n[dim]Press Enter to continue[/dim]", default="")

    def _view_characters(self) -> None:
        """Display all characters in a Rich table."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name, description, role FROM characters ORDER BY id")
            rows = cursor.fetchall()

        if not rows:
            console.print("\n[yellow]No characters added yet[/yellow]")
            Prompt.ask("\n[dim]Press Enter to continue[/dim]", default="")
            return

        table = Table(title="Characters", show_header=True, header_style="bold cyan")
        table.add_column("Name", style="green")
        table.add_column("Role", style="yellow")
        table.add_column("Description")

        for row in rows:
            table.add_row(row[0], row[2], row[1])

        console.print("\n")
        console.print(table)
        Prompt.ask("\n[dim]Press Enter to continue[/dim]", default="")

    def _view_scenes(self) -> None:
        """Display all scenes in a Rich table."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT scene_number, title, description, characters FROM scenes ORDER BY scene_number")
            rows = cursor.fetchall()

        if not rows:
            console.print("\n[yellow]No scenes added yet[/yellow]")
            Prompt.ask("\n[dim]Press Enter to continue[/dim]", default="")
            return

        table = Table(title="Scenes", show_header=True, header_style="bold cyan")
        table.add_column("#", style="cyan", width=4)
        table.add_column("Title", style="green")
        table.add_column("Characters", style="yellow")
        table.add_column("Description")

        for row in rows:
            table.add_row(
                str(row[0]),
                row[1],
                row[3] or "[dim](none)[/dim]",
                row[2]
            )

        console.print("\n")
        console.print(table)
        Prompt.ask("\n[dim]Press Enter to continue[/dim]", default="")

    def _edit_character(self) -> None:
        """Edit an existing character."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, description, role FROM characters ORDER BY id")
            rows = cursor.fetchall()

        if not rows:
            console.print("\n[yellow]No characters to edit[/yellow]")
            Prompt.ask("\n[dim]Press Enter to continue[/dim]", default="")
            return

        # Show characters table
        table = Table(title="Select Character to Edit", show_header=True, header_style="bold cyan")
        table.add_column("#", style="dim")
        table.add_column("Name", style="green")
        table.add_column("Role", style="yellow")
        table.add_column("Description")

        for idx, row in enumerate(rows, 1):
            table.add_row(str(idx), row[1], row[3], row[2])

        console.print("\n")
        console.print(table)

        # Select character
        char_idx = int(Prompt.ask(
            "\nChoose character number",
            choices=[str(i) for i in range(1, len(rows) + 1)]
        ))
        selected = rows[char_idx - 1]
        char_id, old_name, old_desc, old_role = selected

        console.print(f"\n[bold cyan]Editing: {old_name}[/bold cyan]")
        console.print("[dim]Press Enter to keep current value[/dim]\n")

        # Get new values
        name = Prompt.ask("Name", default=old_name)
        description = Prompt.ask("Description", default=old_desc)
        role = Prompt.ask(
            "Role",
            choices=["protagonist", "love_interest", "antagonist", "supporting"],
            default=old_role
        )

        # Update database
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE characters SET name = ?, description = ?, role = ? WHERE id = ?",
                (name, description, role, char_id)
            )

        console.print(f"\n[green]Updated character:[/green] {name}")
        Prompt.ask("\n[dim]Press Enter to continue[/dim]", default="")

    def _edit_scene(self) -> None:
        """Edit an existing scene."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, scene_number, title, description, characters FROM scenes ORDER BY scene_number")
            rows = cursor.fetchall()

        if not rows:
            console.print("\n[yellow]No scenes to edit[/yellow]")
            Prompt.ask("\n[dim]Press Enter to continue[/dim]", default="")
            return

        # Show scenes table
        table = Table(title="Select Scene to Edit", show_header=True, header_style="bold cyan")
        table.add_column("#", style="dim")
        table.add_column("Scene", style="cyan")
        table.add_column("Title", style="green")
        table.add_column("Characters", style="yellow")

        for idx, row in enumerate(rows, 1):
            table.add_row(str(idx), str(row[1]), row[2], row[4] or "[dim](none)[/dim]")

        console.print("\n")
        console.print(table)

        # Select scene
        scene_idx = int(Prompt.ask(
            "\nChoose scene number",
            choices=[str(i) for i in range(1, len(rows) + 1)]
        ))
        selected = rows[scene_idx - 1]
        scene_id, old_number, old_title, old_desc, old_chars = selected

        console.print(f"\n[bold cyan]Editing: Scene {old_number} - {old_title}[/bold cyan]")
        console.print("[dim]Press Enter to keep current value[/dim]\n")

        # Get new values
        scene_number = int(Prompt.ask("Scene number", default=str(old_number)))
        title = Prompt.ask("Title", default=old_title)
        description = Prompt.ask("Description", default=old_desc)

        # Show available characters
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM characters")
            chars = [row[0] for row in cursor.fetchall()]

        if chars:
            console.print(f"\n[dim]Available characters: {', '.join(chars)}[/dim]")
            characters = Prompt.ask("Characters in this scene (comma-separated)", default=old_chars or "")
        else:
            characters = old_chars or ""

        # Update database
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE scenes SET scene_number = ?, title = ?, description = ?, characters = ? WHERE id = ?",
                (scene_number, title, description, characters, scene_id)
            )

        console.print(f"\n[green]Updated scene {scene_number}:[/green] {title}")
        Prompt.ask("\n[dim]Press Enter to continue[/dim]", default="")

    def _delete_character(self) -> None:
        """Delete a character."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, description, role FROM characters ORDER BY id")
            rows = cursor.fetchall()

        if not rows:
            console.print("\n[yellow]No characters to delete[/yellow]")
            Prompt.ask("\n[dim]Press Enter to continue[/dim]", default="")
            return

        # Show characters table
        table = Table(title="Select Character to Delete", show_header=True, header_style="bold cyan")
        table.add_column("#", style="dim")
        table.add_column("Name", style="green")
        table.add_column("Role", style="yellow")
        table.add_column("Description")

        for idx, row in enumerate(rows, 1):
            table.add_row(str(idx), row[1], row[3], row[2])

        console.print("\n")
        console.print(table)

        # Select character
        char_idx = int(Prompt.ask(
            "\nChoose character number",
            choices=[str(i) for i in range(1, len(rows) + 1)]
        ))
        selected = rows[char_idx - 1]
        char_id, char_name = selected[0], selected[1]

        # Confirm deletion
        if Confirm.ask(f"[red]Delete character '{char_name}'? This cannot be undone.[/red]"):
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM characters WHERE id = ?", (char_id,))

            console.print(f"\n[green]Deleted character:[/green] {char_name}")
        else:
            console.print("\n[yellow]Cancelled[/yellow]")

        Prompt.ask("\n[dim]Press Enter to continue[/dim]", default="")

    def _delete_scene(self) -> None:
        """Delete a scene."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, scene_number, title, description FROM scenes ORDER BY scene_number")
            rows = cursor.fetchall()

        if not rows:
            console.print("\n[yellow]No scenes to delete[/yellow]")
            Prompt.ask("\n[dim]Press Enter to continue[/dim]", default="")
            return

        # Show scenes table
        table = Table(title="Select Scene to Delete", show_header=True, header_style="bold cyan")
        table.add_column("#", style="dim")
        table.add_column("Scene", style="cyan")
        table.add_column("Title", style="green")
        table.add_column("Description")

        for idx, row in enumerate(rows, 1):
            table.add_row(str(idx), str(row[1]), row[2], row[3])

        console.print("\n")
        console.print(table)

        # Select scene
        scene_idx = int(Prompt.ask(
            "\nChoose scene number",
            choices=[str(i) for i in range(1, len(rows) + 1)]
        ))
        selected = rows[scene_idx - 1]
        scene_id, scene_number, scene_title = selected[0], selected[1], selected[2]

        # Confirm deletion
        if Confirm.ask(f"[red]Delete scene {scene_number} - '{scene_title}'? This cannot be undone.[/red]"):
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM scenes WHERE id = ?", (scene_id,))

            console.print(f"\n[green]Deleted scene {scene_number}:[/green] {scene_title}")
        else:
            console.print("\n[yellow]Cancelled[/yellow]")

        Prompt.ask("\n[dim]Press Enter to continue[/dim]", default="")

    def _edit_writer_notes(self) -> None:
        """Edit project writer notes."""
        console.print("\n[bold cyan]Writer Notes[/bold cyan]\n")

        # Get existing notes
        notes = self.db.get_writer_notes()

        console.print("[dim]Press Enter to keep current value, or type new text[/dim]\n")

        # Prompt for each field
        logline = Prompt.ask(
            "Logline (one-sentence story summary)",
            default=notes.get('logline', '') if notes else ''
        )

        theme = Prompt.ask(
            "Theme (what the story is really about)",
            default=notes.get('theme', '') if notes else ''
        )

        inspiration = Prompt.ask(
            "Inspiration (what inspired this story)",
            default=notes.get('inspiration', '') if notes else ''
        )

        tone = Prompt.ask(
            "Tone (overall voice and style)",
            default=notes.get('tone', '') if notes else ''
        )

        comps = Prompt.ask(
            "Comps (comparable films, e.g., 'When Harry Met Sally meets The Proposal')",
            default=notes.get('comps', '') if notes else ''
        )

        console.print("\n[cyan]Braindump (free-form creative notes):[/cyan]")
        console.print("[dim]Enter your notes, then type 'done' on a new line[/dim]\n")

        # Multi-line braindump input
        braindump_lines = []
        current_braindump = notes.get('braindump', '') if notes else ''

        if current_braindump:
            console.print(f"[dim]Current braindump:\n{current_braindump}\n[/dim]")
            if Confirm.ask("Keep current braindump?"):
                braindump = current_braindump
            else:
                console.print("[yellow]Enter new braindump (type 'done' when finished):[/yellow]")
                while True:
                    line = Prompt.ask("", default="")
                    if line.lower() == 'done':
                        break
                    braindump_lines.append(line)
                braindump = "\n".join(braindump_lines)
        else:
            console.print("[yellow]Enter braindump (type 'done' when finished):[/yellow]")
            while True:
                line = Prompt.ask("", default="")
                if line.lower() == 'done':
                    break
                braindump_lines.append(line)
            braindump = "\n".join(braindump_lines)

        # Save to database
        self.db.upsert_writer_notes(
            logline=logline,
            theme=theme,
            inspiration=inspiration,
            tone=tone,
            comps=comps,
            braindump=braindump
        )

        console.print("\n[green]Writer notes saved![/green]")
        Prompt.ask("\n[dim]Press Enter to continue[/dim]", default="")

    def _edit_project_metadata(self) -> None:
        """Edit project name, genre, and description."""
        console.print("\n[bold cyan]Project Metadata[/bold cyan]\n")

        project = self.db.get_project()

        if not project:
            console.print("[red]Error: No project metadata found[/red]")
            Prompt.ask("\n[dim]Press Enter to continue[/dim]", default="")
            return

        console.print("[dim]Press Enter to keep current value[/dim]\n")

        # Prompt for each field
        name = Prompt.ask(
            "Project name",
            default=project.get('name', '')
        )

        genre = Prompt.ask(
            "Genre",
            default=project.get('genre', 'Romantic Comedy')
        )

        description = Prompt.ask(
            "Description",
            default=project.get('description', '')
        )

        # Update database
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE projects SET name = ?, genre = ?, description = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (name, genre, description, project['id'])
            )

        console.print("\n[green]Project metadata updated![/green]")
        Prompt.ask("\n[dim]Press Enter to continue[/dim]", default="")

    def _view_brainstorm_sessions(self) -> None:
        """View all brainstorm sessions (read-only - populated by BRAINSTORM module)."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    b.id,
                    b.scene_id,
                    s.scene_number,
                    s.title,
                    b.tone,
                    b.bucket_used,
                    b.content,
                    b.created_at
                FROM brainstorm_sessions b
                LEFT JOIN scenes s ON b.scene_id = s.id
                ORDER BY b.created_at DESC
            """)
            rows = cursor.fetchall()

        if not rows:
            console.print("\n[yellow]No brainstorm sessions yet[/yellow]")
            console.print("[dim]Run BRAINSTORM module to generate creative ideas[/dim]")
            console.print("[cyan]  python -m backend.automated_brainstorm[/cyan]")
            Prompt.ask("\n[dim]Press Enter to continue[/dim]", default="")
            return

        # Show summary table
        table = Table(title="Brainstorm Sessions", show_header=True, header_style="bold cyan")
        table.add_column("#", style="dim", width=4)
        table.add_column("Scene", style="cyan")
        table.add_column("Tone", style="yellow")
        table.add_column("Bucket", style="magenta")
        table.add_column("Date", style="dim")

        for row in rows:
            scene_info = f"Scene {row[2]} - {row[3]}" if row[2] else f"Scene ID {row[1]}"
            table.add_row(
                str(row[0]),
                scene_info,
                row[4] or "[dim](none)[/dim]",
                row[5] or "[dim](none)[/dim]",
                row[7][:10] if row[7] else ""  # Just show date
            )

        console.print("\n")
        console.print(table)

        # Ask if user wants to see details
        if Confirm.ask("\nView detailed content for a session?"):
            session_id = int(Prompt.ask(
                "Session #",
                choices=[str(row[0]) for row in rows]
            ))

            # Get full content
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT content FROM brainstorm_sessions WHERE id = ?",
                    (session_id,)
                )
                content = cursor.fetchone()[0]

            console.print("\n[bold cyan]Brainstorm Content:[/bold cyan]\n")
            console.print(Panel(content, border_style="cyan"))

        Prompt.ask("\n[dim]Press Enter to continue[/dim]", default="")

    def _view_drafts(self) -> None:
        """View all drafts (read-only - populated by WRITE module)."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    d.id,
                    d.version,
                    d.scene_id,
                    s.scene_number,
                    s.title,
                    d.created_at,
                    LENGTH(d.content) as content_length
                FROM drafts d
                LEFT JOIN scenes s ON d.scene_id = s.id
                ORDER BY d.version DESC, d.scene_id
            """)
            rows = cursor.fetchall()

        if not rows:
            console.print("\n[yellow]No drafts yet[/yellow]")
            console.print("[dim]Run WRITE module to generate screenplay drafts[/dim]")
            console.print("[cyan]  python -m backend.automated_write[/cyan]")
            Prompt.ask("\n[dim]Press Enter to continue[/dim]", default="")
            return

        # Show summary table
        table = Table(title="Drafts", show_header=True, header_style="bold cyan")
        table.add_column("ID", style="dim", width=4)
        table.add_column("Version", style="green")
        table.add_column("Scope", style="yellow")
        table.add_column("Length", style="cyan")
        table.add_column("Date", style="dim")

        for row in rows:
            if row[2]:  # scene_id exists
                scope = f"Scene {row[3]} - {row[4]}" if row[3] else f"Scene ID {row[2]}"
            else:
                scope = "[bold]Full Draft[/bold]"

            table.add_row(
                str(row[0]),
                f"v{row[1]}",
                scope,
                f"{row[6]:,} chars",
                row[5][:10] if row[5] else ""  # Just show date
            )

        console.print("\n")
        console.print(table)

        # Ask if user wants to see content
        if Confirm.ask("\nView draft content?"):
            draft_id = int(Prompt.ask(
                "Draft ID",
                choices=[str(row[0]) for row in rows]
            ))

            # Get full content
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT content FROM drafts WHERE id = ?",
                    (draft_id,)
                )
                content = cursor.fetchone()[0]

            console.print("\n[bold cyan]Draft Content:[/bold cyan]\n")
            console.print(Panel(content, border_style="cyan"))

        Prompt.ask("\n[dim]Press Enter to continue[/dim]", default="")


def main():
    """
    CLI entrypoint for project editor.

    Usage:
        python -m backend.edit_project              # Interactive project selection
        python -m backend.edit_project "Project Name"  # Direct project access

    Note: To CREATE new projects, use IDEATE instead:
        python -m backend.ideate_web     # Web UI
        python -m backend.ideate --quick # CLI quick mode
    """
    import sys
    import argparse
    from .project_creator import list_projects, get_project_path

    parser = argparse.ArgumentParser(
        description="Edit characters, scenes, and metadata for existing projects"
    )
    parser.add_argument("project_name", nargs='?', help="Project name (optional)")

    args = parser.parse_args()

    # If no project name provided, show selector
    if not args.project_name:
        console.print(Panel.fit(
            "[bold cyan]Lizzy Project Editor[/bold cyan]\n\n"
            "Edit characters, scenes, and metadata for existing projects.\n\n"
            "[dim]To create NEW projects, use:[/dim]\n"
            "  python -m backend.ideate_web",
            border_style="cyan"
        ))

        existing = list_projects()

        if not existing:
            console.print("\n[yellow]No projects found.[/yellow]")
            console.print("\n[cyan]Create one first:[/cyan]")
            console.print("  python -m backend.ideate_web     # Web UI (recommended)")
            console.print("  python -m backend.ideate --quick # CLI quick mode")
            sys.exit(0)

        # Show project table
        table = Table(title="Available Projects", show_header=True, header_style="bold cyan")
        table.add_column("#", style="dim")
        table.add_column("Project Name", style="green")

        for idx, project_name in enumerate(existing, 1):
            table.add_row(str(idx), project_name)

        console.print("\n")
        console.print(table)

        # Select project
        project_idx = int(Prompt.ask(
            "\nChoose project number",
            choices=[str(i) for i in range(1, len(existing) + 1)]
        ))
        project_name = existing[project_idx - 1]
    else:
        project_name = args.project_name

    # Get project database path
    db_path = get_project_path(project_name)

    if not db_path:
        console.print(f"[red]Error:[/red] Project '{project_name}' not found")
        console.print("\n[yellow]Available projects:[/yellow]")
        for project in list_projects():
            console.print(f"  - {project}")
        sys.exit(1)

    # Run editor
    editor = ProjectEditor(db_path)
    editor.run_interactive()


# Backwards compatibility alias
IntakeModule = ProjectEditor


if __name__ == "__main__":
    main()
