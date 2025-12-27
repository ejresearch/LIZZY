"""
Interactive Brainstorm - Context-aware knowledge graph exploration.
"""

import asyncio
import os
from pathlib import Path
from typing import List, Dict, Optional
from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import openai_embed
from openai import AsyncOpenAI
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from .database import Database
from .reranker import CohereReranker

console = Console()


# Custom GPT-5-mini completion function for LightRAG
async def gpt_5_mini_complete(
    prompt: str,
    system_prompt: str = None,
    history_messages: list = None,
    **kwargs
) -> str:
    """GPT-5-mini completion function compatible with LightRAG."""
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
        max_tokens=kwargs.get("max_tokens", 2000)
    )

    return response.choices[0].message.content


class InteractiveBrainstorm:
    """
    Context-aware micro-search engine for creative exploration.

    Loads full project context (characters, scenes, notes) and uses it
    to enhance queries across knowledge graph buckets.
    """

    def __init__(self, db_path: Path):
        """
        Initialize Interactive Brainstorm.

        Args:
            db_path: Path to project database
        """
        self.db_path = db_path
        self.db = Database(db_path)
        self.project = None
        self.characters = []
        self.scenes = []
        self.writer_notes = None

        # Available buckets
        self.bucket_dir = Path("./rag_buckets")
        self.available_buckets = self._discover_buckets()

        # Conversation history
        self.conversation_history = []
        self.current_buckets = []

        # Scene-specific mode (Improvement #1)
        self.focused_scene = None

        # Query history (Improvement #4)
        self.query_history = []

        # Conversation logging - store in project directory
        self.log_dir = None  # Will be set when project loads
        self.current_log_file = None

        # Initialize reranker
        self.reranker = CohereReranker()

    def _discover_buckets(self) -> List[str]:
        """Find all available RAG buckets."""
        if not self.bucket_dir.exists():
            return []

        buckets = []
        for bucket in self.bucket_dir.iterdir():
            if bucket.is_dir() and not bucket.name.startswith('.'):
                # Check if it has the required graph file
                graphml = bucket / "graph_chunk_entity_relation.graphml"
                if graphml.exists():
                    buckets.append(bucket.name)

        return buckets

    def load_project_context(self) -> None:
        """Load all project context from database."""
        # Project metadata
        self.project = self.db.get_project()

        # Set up project-specific conversation logs directory
        project_dir = self.db_path.parent
        self.log_dir = project_dir / "conversation_logs"
        self.log_dir.mkdir(exist_ok=True)

        # Characters
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name, description, role, arc FROM characters")
            self.characters = [dict(row) for row in cursor.fetchall()]

            # Scenes
            cursor.execute("""
                SELECT scene_number, title, description, characters, tone
                FROM scenes
                ORDER BY scene_number
            """)
            self.scenes = [dict(row) for row in cursor.fetchall()]

        # Writer notes (may not exist in older projects)
        try:
            self.writer_notes = self.db.get_writer_notes()
        except Exception:
            self.writer_notes = None

    def build_context_summary(self) -> str:
        """
        Create a context summary for query enhancement.

        Returns:
            String summarizing project context
        """
        parts = []

        if self.project:
            parts.append(f"PROJECT: {self.project['name']} ({self.project['genre']})")

        if self.writer_notes:
            if self.writer_notes.get('theme'):
                parts.append(f"THEME: {self.writer_notes['theme']}")
            if self.writer_notes.get('tone'):
                parts.append(f"TONE: {self.writer_notes['tone']}")
            if self.writer_notes.get('comps'):
                parts.append(f"COMPS: {self.writer_notes['comps']}")

        if self.characters:
            char_list = ", ".join([f"{c['name']} ({c['role']})" for c in self.characters[:5]])
            parts.append(f"CHARACTERS: {char_list}")

        return "\n".join(parts)

    def get_character_context(self, character_name: str) -> Optional[Dict]:
        """Get context for a specific character."""
        for char in self.characters:
            if char['name'].lower() == character_name.lower():
                return char
        return None

    def get_scene_context(self, scene_number: int) -> Optional[Dict]:
        """Get context for a specific scene."""
        for scene in self.scenes:
            if scene['scene_number'] == scene_number:
                return scene
        return None

    # === IMPROVEMENT #1: Scene-Specific Mode ===

    def enter_scene_focus_mode(self, scene_number: int) -> bool:
        """Lock conversation to specific scene."""
        scene = self.get_scene_context(scene_number)
        if not scene:
            console.print(f"[red]Scene {scene_number} not found[/red]")
            return False

        self.focused_scene = scene
        console.print(f"[cyan]🎬 Now focusing on Scene {scene_number}: {scene['title']}[/cyan]")

        # Load blueprint if it exists
        blueprint = self._get_scene_blueprint(scene_number)
        if blueprint:
            console.print(f"[dim]✓ Existing blueprint loaded for context ({len(blueprint)} chars)[/dim]")

        return True

    def exit_scene_focus_mode(self) -> None:
        """Return to project-wide queries."""
        if self.focused_scene:
            scene_num = self.focused_scene['scene_number']
            self.focused_scene = None
            console.print(f"[cyan]Exited scene focus mode (was on Scene {scene_num})[/cyan]")
        else:
            console.print("[yellow]Not in scene focus mode[/yellow]")

    def _get_scene_blueprint(self, scene_number: int) -> Optional[str]:
        """Get existing blueprint for a scene from brainstorm_sessions."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                # Get the most recent synthesis (bucket_used='all')
                cursor.execute("""
                    SELECT content FROM brainstorm_sessions
                    WHERE scene_id IN (SELECT id FROM scenes WHERE scene_number = ?)
                      AND bucket_used = 'all'
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (scene_number,))
                result = cursor.fetchone()
                return result['content'] if result else None
        except Exception:
            return None

    def show_focused_scene_blueprint(self) -> None:
        """Display the blueprint for the currently focused scene."""
        if not self.focused_scene:
            console.print("[yellow]No scene currently focused. Use /focus <scene_number>[/yellow]")
            return

        scene_num = self.focused_scene['scene_number']
        blueprint = self._get_scene_blueprint(scene_num)

        if blueprint:
            console.print(Panel(
                Markdown(blueprint),
                title=f"Blueprint for Scene {scene_num}: {self.focused_scene['title']}",
                border_style="cyan"
            ))
        else:
            console.print(f"[yellow]No blueprint exists yet for Scene {scene_num}[/yellow]")
            console.print("[dim]Run Automated Brainstorm to generate blueprints[/dim]")

    # === IMPROVEMENT #2: Bucket Comparison Mode ===

    async def query_buckets_comparison(self, query: str, buckets: List[str]) -> Dict:
        """Query all buckets and return side-by-side comparison."""
        results = await self.query_buckets(query, buckets, mode="hybrid")

        # Don't synthesize - keep separate
        comparison = {
            'query': query,
            'books': next((r for r in results if r['bucket'] == 'books'), None),
            'plays': next((r for r in results if r['bucket'] == 'plays'), None),
            'scripts': next((r for r in results if r['bucket'] == 'scripts'), None)
        }

        return comparison

    def display_comparison(self, comparison: Dict) -> None:
        """Display side-by-side bucket comparison."""
        from rich.columns import Columns

        console.print(f"\n[bold]Comparing Expert Perspectives:[/bold] {comparison['query']}\n")

        panels = []
        for bucket in ['books', 'plays', 'scripts']:
            if comparison[bucket]:
                response_text = comparison[bucket]['response']
                # Truncate if too long
                if len(response_text) > 800:
                    response_text = response_text[:800] + "\n\n[dim]...(truncated)[/dim]"

                panel = Panel(
                    Markdown(response_text),
                    title=f"📚 {bucket.upper()} Expert",
                    border_style="cyan",
                    padding=(1, 2)
                )
                panels.append(panel)

        if panels:
            console.print(Columns(panels, equal=True, expand=True))
        else:
            console.print("[yellow]No results to compare[/yellow]")

    # === IMPROVEMENT #3: Export to Blueprint Format ===

    async def export_conversation_to_blueprint(self, scene_number: int) -> Optional[str]:
        """Convert conversation insights into structured blueprint."""
        if not self.conversation_history:
            console.print("[yellow]No conversation to export[/yellow]")
            return None

        scene = self.get_scene_context(scene_number)
        if not scene:
            console.print(f"[red]Scene {scene_number} not found[/red]")
            return None

        # Build prompt for GPT-4o
        conversation_text = "\n\n".join([
            f"{'User' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}"
            for msg in self.conversation_history
        ])

        prompt = f"""Convert this brainstorming conversation into a structured scene blueprint for Scene {scene_number}: {scene['title']}.

SCENE CONTEXT:
{scene['description']}

CONVERSATION:
{conversation_text}

OUTPUT FORMAT (use these exact section headers):

## SCENE_BLUEPRINT

### EXECUTIVE_SUMMARY
[3-5 sentences summarizing the conversation insights]

### STRUCTURAL_FUNCTION
- [Key structural points from conversation]
- [Bullet format only]

### DRAMATIC_BEATS
- [Beats identified in conversation]
- [Bullet format only]

### CHARACTER_DYNAMICS
- [Character insights from conversation]
- [Bullet format only]

### DIALOGUE_APPROACH
- [Dialogue guidance from conversation]
- [Bullet format only]

### VISUAL_STORYTELLING
- [Visual ideas from conversation]
- [Bullet format only]

### EMOTIONAL_TRAJECTORY
- [Emotional arc insights]
- [Bullet format only]

Extract insights from the conversation and organize them into this structure. Use bullet points (5-7 per section).
"""

        console.print("[cyan]Converting conversation to blueprint...[/cyan]")

        try:
            client = AsyncOpenAI()
            response = await client.chat.completions.create(
                model="gpt-5",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=1500
            )

            return response.choices[0].message.content

        except Exception as e:
            console.print(f"[red]Error generating blueprint: {e}[/red]")
            return None

    def save_as_blueprint(self, scene_number: int, blueprint: str) -> bool:
        """Save conversation-derived blueprint to database."""
        scene = self.get_scene_context(scene_number)
        if not scene:
            return False

        # Get scene ID from database
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM scenes WHERE scene_number = ?", (scene_number,))
                result = cursor.fetchone()
                if not result:
                    return False

                scene_id = result['id']

                # Save as brainstorm session
                cursor.execute("""
                    INSERT INTO brainstorm_sessions (scene_id, tone, bucket_used, content)
                    VALUES (?, ?, ?, ?)
                """, (scene_id, 'Interactive Conversation', 'all', blueprint))
                conn.commit()

            return True

        except Exception as e:
            console.print(f"[red]Error saving blueprint: {e}[/red]")
            return False

    # === IMPROVEMENT #4: Query History ===

    def _show_query_history(self) -> None:
        """Display recent queries."""
        if not self.query_history:
            console.print("[yellow]No query history yet[/yellow]")
            return

        table = Table(title="Query History", show_header=True, header_style="bold cyan")
        table.add_column("#", style="dim", width=4)
        table.add_column("Time", style="cyan", width=8)
        table.add_column("Query", style="white")
        table.add_column("Buckets", style="dim", width=20)

        # Show last 10 queries
        for i, query_record in enumerate(self.query_history[-10:], 1):
            time_str = query_record['timestamp'].strftime("%H:%M")
            query_text = query_record['query']
            if len(query_text) > 60:
                query_text = query_text[:60] + "..."
            buckets_str = ", ".join(query_record['buckets'])

            table.add_row(str(i), time_str, query_text, buckets_str)

        console.print(table)

    # === IMPROVEMENT #5: Suggested Questions ===

    async def generate_follow_up_questions(self, query: str, response: str) -> List[str]:
        """Generate 3 suggested follow-up questions."""
        prompt = f"""Based on this Q&A about screenplay writing, suggest 3 natural follow-up questions a screenwriter might ask.

QUERY: {query}

RESPONSE: {response[:500]}...

Provide 3 specific, actionable follow-up questions (one per line, no numbering):
"""

        try:
            client = AsyncOpenAI()
            result = await client.chat.completions.create(
                model="gpt-5.1",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=150
            )

            questions = result.choices[0].message.content.strip().split('\n')
            return [q.strip('- ').strip() for q in questions if q.strip()][:3]

        except Exception:
            return []

    async def query_buckets(
        self,
        query: str,
        buckets: List[str],
        mode: str = "hybrid",
        use_reranking: bool = True
    ) -> List[Dict]:
        """
        Query multiple buckets with the same query.

        Args:
            query: Search query
            buckets: List of bucket names to query
            mode: Query mode (naive/local/global/hybrid)
            use_reranking: Whether to use Cohere reranking (default: True)

        Returns:
            List of results from each bucket
        """
        results = []

        for bucket_name in buckets:
            bucket_path = self.bucket_dir / bucket_name

            if not bucket_path.exists():
                console.print(f"[yellow]⚠️  Bucket '{bucket_name}' not found[/yellow]")
                continue

            try:
                console.print(f"[cyan]Querying {bucket_name}...[/cyan]")

                # Initialize LightRAG for this bucket
                rag = LightRAG(
                    working_dir=str(bucket_path),
                    embedding_func=openai_embed,
                    llm_model_func=gpt_5_mini_complete,
                )

                # Initialize storage before querying
                await rag.initialize_storages()

                # Query with specified mode
                response = await rag.aquery(query, param=QueryParam(mode=mode))

                # Apply reranking if enabled and response exists
                if response and use_reranking and self.reranker.is_available():
                    # Split response into chunks (paragraphs)
                    chunks = [p.strip() for p in response.split('\n\n') if p.strip()]

                    if len(chunks) > 1:
                        console.print(f"[dim]  Reranking {len(chunks)} chunks...[/dim]")

                        # Rerank chunks
                        reranked = self.reranker.rerank(
                            query=query,
                            documents=chunks,
                            top_n=min(10, len(chunks))
                        )

                        # Reconstruct response from top reranked chunks
                        response = '\n\n'.join([r['text'] for r in reranked])
                        console.print(f"[dim]  ✓ Reranked to top {len(reranked)} chunks[/dim]")

                # Only add if we got a response
                if response:
                    results.append({
                        'bucket': bucket_name,
                        'response': response,
                        'mode': mode,
                        'reranked': use_reranking and self.reranker.is_available()
                    })
                    console.print(f"[green]✓ {bucket_name} complete[/green]\n")
                else:
                    console.print(f"[yellow]⚠️  {bucket_name} returned no results[/yellow]\n")

            except Exception as e:
                console.print(f"[red]✗ Error querying {bucket_name}: {e}[/red]\n")
                continue

        return results

    def enhance_query_with_context(
        self,
        user_query: str,
        context_elements: Optional[Dict] = None
    ) -> str:
        """
        Enhance user query with project context.

        Args:
            user_query: Original user query
            context_elements: Optional specific context (characters, scenes, etc.)

        Returns:
            Enhanced query string
        """
        enhanced_parts = []

        # Add project context
        if self.project or self.writer_notes:
            context_summary = self.build_context_summary()
            enhanced_parts.append(f"CONTEXT:\n{context_summary}\n")

        # IMPROVEMENT #1: If focused_scene is set, inject scene-specific context
        if self.focused_scene:
            enhanced_parts.append(
                f"FOCUSED SCENE: Scene {self.focused_scene['scene_number']}: {self.focused_scene['title']}"
            )
            enhanced_parts.append(f"Description: {self.focused_scene['description']}")

            # Load blueprint if exists
            blueprint = self._get_scene_blueprint(self.focused_scene['scene_number'])
            if blueprint:
                # Truncate to save tokens
                blueprint_preview = blueprint[:500] + "..." if len(blueprint) > 500 else blueprint
                enhanced_parts.append(f"EXISTING BLUEPRINT:\n{blueprint_preview}")

        # Add specific element context if provided
        if context_elements:
            if 'character' in context_elements:
                char = self.get_character_context(context_elements['character'])
                if char:
                    enhanced_parts.append(
                        f"CHARACTER FOCUS: {char['name']} - {char['description']} "
                        f"(Role: {char['role']})"
                    )

            if 'scene' in context_elements:
                scene = self.get_scene_context(context_elements['scene'])
                if scene:
                    enhanced_parts.append(
                        f"SCENE FOCUS: Scene {scene['scene_number']} - {scene['title']}\n"
                        f"Description: {scene['description']}"
                    )

        # Add user query
        enhanced_parts.append(f"QUERY: {user_query}")

        return "\n\n".join(enhanced_parts)

    def display_results(self, results: List[Dict]) -> None:
        """Display query results in a nice format."""
        if not results:
            console.print("[yellow]No results found[/yellow]")
            return

        for result in results:
            bucket_name = result['bucket']
            response = result['response']
            reranked = result.get('reranked', False)

            # Skip if no response
            if not response:
                continue

            # Create panel for each bucket's response
            console.print(f"\n[bold cyan]Results from {bucket_name}:[/bold cyan]")

            # Build title with mode and reranking indicator
            title = f"{bucket_name} ({result['mode']} mode)"
            if reranked:
                title += " [reranked ✨]"

            try:
                # Try to display as Markdown
                console.print(Panel(
                    Markdown(response),
                    border_style="cyan",
                    title=title,
                    title_align="left"
                ))
            except Exception as e:
                # Fallback to plain text
                console.print(Panel(
                    str(response),
                    border_style="cyan",
                    title=title,
                    title_align="left"
                ))

    async def run_conversation_mode(self) -> None:
        """Run continuous conversation mode."""
        # Start conversation log
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_log_file = self.log_dir / f"conversation_{timestamp}.md"

        console.print(Panel.fit(
            "[bold green]Conversation Mode[/bold green]\n\n"
            "Chat naturally with your knowledge graphs.\n\n"
            "[bold cyan]Commands:[/bold cyan]\n"
            "  /focus <N>    - Focus on Scene N\n"
            "  /unfocus      - Exit scene focus mode\n"
            "  /blueprint    - Show focused scene blueprint\n"
            "  /compare <Q>  - Compare expert perspectives\n"
            "  /export <N>   - Export conversation to Scene N blueprint\n"
            "  /history      - Show query history\n"
            "  /rerun <N>    - Re-run query from history\n"
            "  save          - Save to writer notes\n"
            "  clear         - Clear conversation history\n"
            "  exit          - End conversation\n\n"
            f"[dim]Log: {self.current_log_file.relative_to(Path.cwd())}[/dim]",
            border_style="green"
        ))

        # Select buckets once
        console.print("\n[bold]Select bucket(s) for this conversation:[/bold]")
        for i, bucket in enumerate(self.available_buckets, 1):
            console.print(f"[{i}] {bucket}")

        bucket_input = Prompt.ask(
            "Bucket numbers (comma-separated, or 'all')",
            default="all"
        )

        if bucket_input.lower() == "all":
            self.current_buckets = self.available_buckets
        else:
            indices = [int(i.strip()) - 1 for i in bucket_input.split(",")]
            self.current_buckets = [self.available_buckets[i] for i in indices
                               if 0 <= i < len(self.available_buckets)]

        console.print(f"\n[dim]Using buckets: {', '.join(self.current_buckets)}[/dim]")
        console.print("[dim]Type your questions naturally. I'll remember our conversation.[/dim]\n")

        # Initialize log file
        self._init_conversation_log(self.current_buckets)

        # Conversation loop
        last_suggestions = []  # Store suggestions for numeric selection

        while True:
            # Get user input
            if self.focused_scene:
                prompt_text = f"\n[bold cyan]You[/bold cyan] [dim][Scene {self.focused_scene['scene_number']}][/dim]"
            else:
                prompt_text = "\n[bold cyan]You[/bold cyan]"

            user_input = Prompt.ask(prompt_text)

            # Check if numeric selection of suggestion
            if user_input.isdigit() and last_suggestions:
                suggestion_idx = int(user_input) - 1
                if 0 <= suggestion_idx < len(last_suggestions):
                    user_input = last_suggestions[suggestion_idx]
                    console.print(f"[cyan]→ {user_input}[/cyan]\n")

            # Exit command
            if user_input.lower() in ['exit', 'quit', 'bye']:
                console.print(f"\n[green]Conversation ended[/green]")
                console.print(f"[dim]Saved to: {self.current_log_file}[/dim]")
                break

            # Save command
            if user_input.lower() == 'save':
                if self.conversation_history:
                    self._save_conversation()
                    console.print("[green]✓ Conversation saved to writer notes[/green]")
                else:
                    console.print("[yellow]No conversation to save[/yellow]")
                continue

            # Clear command
            if user_input.lower() == 'clear':
                self.conversation_history = []
                console.print("[yellow]Conversation history cleared[/yellow]")
                continue

            # NEW COMMANDS

            # /focus command (Improvement #1)
            if user_input.lower().startswith('/focus'):
                parts = user_input.split()
                if len(parts) == 2 and parts[1].isdigit():
                    scene_num = int(parts[1])
                    self.enter_scene_focus_mode(scene_num)
                else:
                    console.print("[red]Usage: /focus <scene_number>[/red]")
                continue

            # /unfocus command (Improvement #1)
            if user_input.lower() == '/unfocus':
                self.exit_scene_focus_mode()
                continue

            # /blueprint command (Improvement #1)
            if user_input.lower() == '/blueprint':
                self.show_focused_scene_blueprint()
                continue

            # /compare command (Improvement #2)
            if user_input.lower().startswith('/compare '):
                query = user_input[9:].strip()  # Remove '/compare '
                if query:
                    console.print(f"\n[dim]Comparing expert perspectives...[/dim]")
                    comparison = await self.query_buckets_comparison(query, self.current_buckets)
                    self.display_comparison(comparison)
                else:
                    console.print("[red]Usage: /compare <your question>[/red]")
                continue

            # /export command (Improvement #3)
            if user_input.lower().startswith('/export'):
                parts = user_input.split()
                if len(parts) == 2 and parts[1].isdigit():
                    scene_num = int(parts[1])
                elif self.focused_scene:
                    scene_num = self.focused_scene['scene_number']
                else:
                    console.print("[red]Usage: /export <scene_number> or focus on a scene first[/red]")
                    continue

                blueprint = await self.export_conversation_to_blueprint(scene_num)
                if blueprint:
                    console.print(Panel(Markdown(blueprint), title=f"Scene {scene_num} Blueprint", border_style="green"))
                    if Confirm.ask("\nSave this blueprint to database?"):
                        if self.save_as_blueprint(scene_num, blueprint):
                            console.print(f"[green]✓ Blueprint saved for Scene {scene_num}[/green]")
                        else:
                            console.print("[red]Failed to save blueprint[/red]")
                continue

            # /history command (Improvement #4)
            if user_input.lower() == '/history':
                self._show_query_history()
                continue

            # /rerun command (Improvement #4)
            if user_input.lower().startswith('/rerun'):
                parts = user_input.split()
                if len(parts) == 2 and parts[1].isdigit():
                    index = int(parts[1]) - 1
                    if 0 <= index < len(self.query_history):
                        user_input = self.query_history[index]['query']
                        console.print(f"[dim]Re-running: {user_input}[/dim]\n")
                    else:
                        console.print(f"[red]Invalid history index. Use /history to see available queries.[/red]")
                        continue
                else:
                    console.print("[red]Usage: /rerun <number>[/red]")
                    continue

            # IMPROVEMENT #4: Save to query history
            from datetime import datetime
            self.query_history.append({
                'timestamp': datetime.now(),
                'query': user_input,
                'buckets': self.current_buckets.copy()
            })

            # Add to history and log
            self.conversation_history.append({
                'role': 'user',
                'content': user_input
            })
            self._log_conversation_turn('user', user_input)

            # Build query with conversation context
            conversation_context = self._build_conversation_context()
            enhanced_query = self.enhance_query_with_context(
                user_input + "\n\nCONVERSATION HISTORY:\n" + conversation_context
            )

            # Query buckets
            console.print(f"\n[dim]Searching {', '.join(self.current_buckets)}...[/dim]")
            results = await self.query_buckets(enhanced_query, self.current_buckets, "hybrid")

            if results:
                # Use conversational LLM to synthesize RAG results
                console.print(f"[dim]Synthesizing response...[/dim]")
                conversational_response = await self._conversational_synthesis(user_input, results)

                # Display response
                console.print(f"\n[bold magenta]Assistant[/bold magenta]")
                try:
                    console.print(Markdown(conversational_response))
                except:
                    console.print(conversational_response)

                # Add to history and log
                self.conversation_history.append({
                    'role': 'assistant',
                    'content': conversational_response
                })
                self._log_conversation_turn('assistant', conversational_response)

                # IMPROVEMENT #5: Generate follow-up suggestions
                suggestions = await self.generate_follow_up_questions(user_input, conversational_response)
                if suggestions:
                    last_suggestions = suggestions  # Update for numeric selection
                    console.print("\n[dim]💡 You might also ask:[/dim]")
                    for i, suggestion in enumerate(suggestions, 1):
                        console.print(f"[dim]  {i}. {suggestion}[/dim]")
                    console.print("[dim]Type 1/2/3 to ask, or your own question[/dim]")

            else:
                console.print("\n[yellow]No results found. Try rephrasing your question.[/yellow]")

    def _log_conversation_turn(self, role: str, content: str) -> None:
        """Log a conversation turn to file."""
        if not self.current_log_file:
            return

        with open(self.current_log_file, 'a', encoding='utf-8') as f:
            if role == 'user':
                f.write(f"\n## You\n\n{content}\n")
            else:
                f.write(f"\n## Assistant\n\n{content}\n")

    def _init_conversation_log(self, buckets: List[str]) -> None:
        """Initialize conversation log file with metadata."""
        if not self.current_log_file:
            return

        from datetime import datetime
        project_context = self.build_context_summary()

        with open(self.current_log_file, 'w', encoding='utf-8') as f:
            f.write(f"# Brainstorm Conversation Log\n\n")
            f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**Buckets:** {', '.join(buckets)}\n\n")
            f.write(f"## Project Context\n\n```\n{project_context}\n```\n\n")
            f.write(f"---\n")

    def _build_conversation_context(self) -> str:
        """Build conversation history for context."""
        if not self.conversation_history:
            return ""

        # Last 3 exchanges (6 messages)
        recent = self.conversation_history[-6:]

        context_parts = []
        for msg in recent:
            role = "User" if msg['role'] == 'user' else "Assistant"
            context_parts.append(f"{role}: {msg['content'][:200]}")  # Truncate long messages

        return "\n".join(context_parts)

    async def _conversational_synthesis(
        self,
        user_input: str,
        rag_results: List[Dict]
    ) -> str:
        """
        Use GPT-4 to synthesize RAG results into natural conversation.

        Args:
            user_input: User's current question
            rag_results: Results from LightRAG queries

        Returns:
            Natural conversational response
        """
        # Build system prompt with project context
        project_context = self.build_context_summary()

        system_prompt = f"""You are a helpful screenplay writing assistant with deep knowledge of romantic comedies, story structure, and dramatic writing.

PROJECT CONTEXT:
{project_context}

You have access to knowledge from multiple sources:
- Books: Screenplay theory, structure, and craft
- Plays: Classic dramatic works (Shakespeare, etc.)
- Scripts: Modern film screenplays

Your role is to:
1. Answer questions about story structure, character development, and screenplay craft
2. Provide specific examples from the knowledge base
3. Relate answers back to the user's project context
4. Be conversational and helpful
5. Ask clarifying questions when needed

Always cite which source (books/plays/scripts) your information comes from."""

        # Combine RAG results into context
        rag_context = "\n\n".join([
            f"=== From {result['bucket']} ===\n{result['response']}"
            for result in rag_results
            if result.get('response')
        ])

        # Build messages for conversation
        messages = [
            {"role": "system", "content": system_prompt}
        ]

        # Add conversation history (last 6 messages)
        for msg in self.conversation_history[-6:]:
            messages.append({
                "role": msg['role'],
                "content": msg['content'][:500]  # Truncate to save tokens
            })

        # Add current query with RAG context
        messages.append({
            "role": "user",
            "content": f"{user_input}\n\n---RAG KNOWLEDGE BASE RESULTS---\n{rag_context}"
        })

        # Call GPT-4
        try:
            client = AsyncOpenAI()
            response = await client.chat.completions.create(
                model="gpt-5",  # Using GPT-4o for better quality
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )

            return response.choices[0].message.content

        except Exception as e:
            console.print(f"[red]Error in conversational synthesis: {e}[/red]")
            # Fallback to raw RAG results
            return rag_context

    def _save_conversation(self) -> None:
        """Save conversation to writer notes."""
        current_notes = self.writer_notes or {}
        braindump = current_notes.get('braindump', '')

        # Format conversation
        convo_text = "\n\n--- Brainstorm Conversation ---\n"
        for msg in self.conversation_history:
            role = "Q" if msg['role'] == 'user' else "A"
            convo_text += f"{role}: {msg['content']}\n\n"

        updated_braindump = braindump + convo_text

        self.db.upsert_writer_notes(
            logline=current_notes.get('logline', ''),
            theme=current_notes.get('theme', ''),
            inspiration=current_notes.get('inspiration', ''),
            tone=current_notes.get('tone', ''),
            comps=current_notes.get('comps', ''),
            braindump=updated_braindump
        )

    async def run_interactive_session(self) -> None:
        """Run interactive brainstorming session."""
        console.clear()

        # Load project context
        console.print("[cyan]Loading project context...[/cyan]")
        self.load_project_context()

        if not self.project:
            console.print("[red]Error: No project found in database[/red]")
            return

        # Show header
        console.print(Panel.fit(
            f"[bold cyan]Interactive Brainstorm[/bold cyan]\n\n"
            f"Project: {self.project['name']}\n"
            f"Available Buckets: {', '.join(self.available_buckets)}",
            border_style="cyan"
        ))

        while True:
            console.print("\n[bold]What would you like to do?[/bold]")
            console.print("[1] Conversation mode (chat back and forth)")
            console.print("[2] Query with project context")
            console.print("[3] Query specific character/scene")
            console.print("[4] Free-form query")
            console.print("[5] View project context")
            console.print("[6] Exit")

            choice = Prompt.ask(
                "\nChoose an option",
                choices=["1", "2", "3", "4", "5", "6"],
                default="1"
            )

            if choice == "6":
                console.print("\n[green]Brainstorm session complete![/green]")
                break

            elif choice == "1":
                # Conversation mode
                await self.run_conversation_mode()
                continue

            elif choice == "5":
                # Show project context
                context = self.build_context_summary()
                console.print(Panel(context, title="Project Context", border_style="cyan"))
                continue

            # Get user query
            if choice == "2":
                # Context-enhanced query
                query = Prompt.ask("\n[cyan]Your question[/cyan]")
                enhanced_query = self.enhance_query_with_context(query)

            elif choice == "3":
                # Specific character/scene query
                console.print("\n[dim]Available characters:[/dim]")
                for char in self.characters[:10]:
                    console.print(f"  • {char['name']} ({char['role']})")

                char_name = Prompt.ask("\nCharacter name (or press Enter to skip)", default="")
                scene_num = Prompt.ask("Scene number (or press Enter to skip)", default="")

                query = Prompt.ask("\n[cyan]Your question[/cyan]")

                context_elements = {}
                if char_name:
                    context_elements['character'] = char_name
                if scene_num:
                    context_elements['scene'] = int(scene_num)

                enhanced_query = self.enhance_query_with_context(query, context_elements)

            else:  # choice == "4"
                # Free-form query
                query = Prompt.ask("\n[cyan]Your question[/cyan]")
                enhanced_query = query

            # Show enhanced query
            if choice not in ["4", "1"]:
                console.print(f"\n[dim]Enhanced query:[/dim]")
                console.print(Panel(enhanced_query, border_style="dim"))

            # Select buckets
            console.print("\n[bold]Select bucket(s) to query:[/bold]")
            for i, bucket in enumerate(self.available_buckets, 1):
                console.print(f"[{i}] {bucket}")

            bucket_input = Prompt.ask(
                "Bucket numbers (comma-separated, or 'all')",
                default="all"
            )

            if bucket_input.lower() == "all":
                selected_buckets = self.available_buckets
            else:
                indices = [int(i.strip()) - 1 for i in bucket_input.split(",")]
                selected_buckets = [self.available_buckets[i] for i in indices
                                   if 0 <= i < len(self.available_buckets)]

            # Select query mode
            mode = Prompt.ask(
                "\nQuery mode",
                choices=["naive", "local", "global", "hybrid"],
                default="hybrid"
            )

            # Execute query
            console.print(f"\n[bold cyan]Querying {len(selected_buckets)} bucket(s)...[/bold cyan]\n")

            results = await self.query_buckets(enhanced_query, selected_buckets, mode)

            # Display results
            self.display_results(results)

            # Ask if user wants to save insights
            if Confirm.ask("\n[cyan]Save these insights to writer notes?[/cyan]"):
                # Append to braindump
                current_notes = self.writer_notes or {}
                braindump = current_notes.get('braindump', '')

                new_insight = f"\n\n--- Brainstorm Session ---\nQ: {query}\n\n"
                for result in results:
                    new_insight += f"[{result['bucket']}]\n{result['response']}\n\n"

                updated_braindump = braindump + new_insight

                self.db.upsert_writer_notes(
                    logline=current_notes.get('logline', ''),
                    theme=current_notes.get('theme', ''),
                    inspiration=current_notes.get('inspiration', ''),
                    tone=current_notes.get('tone', ''),
                    comps=current_notes.get('comps', ''),
                    braindump=updated_braindump
                )

                console.print("[green]✓ Saved to writer notes[/green]")


async def main():
    """CLI entrypoint."""
    import sys
    from .start import StartModule

    start = StartModule()

    # If project name provided, use it directly
    if len(sys.argv) > 1:
        project_name = sys.argv[1]
    else:
        # Show project selector
        console.print(Panel.fit(
            "[bold cyan]Interactive Brainstorm[/bold cyan]\n\n"
            "Context-aware micro-search engine for your screenplay",
            border_style="cyan"
        ))

        existing = start.list_projects()

        if not existing:
            console.print("\n[yellow]No projects found.[/yellow]")
            console.print("\n[cyan]Create one first:[/cyan]")
            console.print("  python -m backend.start")
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

    # Run interactive session
    brainstorm = InteractiveBrainstorm(db_path)
    await brainstorm.run_interactive_session()


if __name__ == "__main__":
    asyncio.run(main())
