"""
IDEATE Module - Conversational Pre-Planning for Romantic Comedies

This module guides writers from a loose idea to locked fundamentals through
AI-driven conversation before moving to scene-by-scene brainstorming.

Flow:
1. IDEA DUMP - User gives raw idea (any format)
2. AI CONVERSATION - Draw out and refine through questions
3. LOCK FUNDAMENTALS - Title, logline, main characters
4. PARALLEL BUILD-OUT - Outline, beats, character arcs (developed together)
5. HANDOFF - Transition to BRAINSTORM phase
"""

import os
import json
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional, AsyncGenerator
from datetime import datetime
from openai import AsyncOpenAI
from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import openai_embed

from .database import Database

# Suppress verbose logs
logging.getLogger("nano-vectordb").setLevel(logging.ERROR)
logging.getLogger("lightrag").setLevel(logging.ERROR)
logging.getLogger("pipmaster").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger().setLevel(logging.ERROR)  # Root logger

# Suppress LightRAG's print-based INFO messages
import builtins
_original_print = builtins.print
def _filtered_print(*args, **kwargs):
    msg = " ".join(str(a) for a in args)
    if "INFO:" in msg or "Process" in msg and "initialized" in msg:
        return
    if "pipmaster" in msg or "graspologic" in msg:
        return
    _original_print(*args, **kwargs)
builtins.print = _filtered_print


# =============================================================================
# GPT-5-mini completion function for LightRAG bucket queries
# =============================================================================

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


# =============================================================================
# SYSTEM PROMPT
# =============================================================================
# This is the core personality and instructions for the ideation AI.
# Uses GPT-5.1 for the main conversation, with bucket queries as needed.

IDEATE_SYSTEM_PROMPT = """You are Syd, a warm and collaborative screenwriting partner helping develop romantic comedy ideas.

GOAL: Guide the user from a loose idea to a fully developed story foundation through natural conversation.

WHAT WE'RE BUILDING:
Phase 1 (Lock First):
- Title
- Logline (one sentence: protagonist, goal, obstacle, stakes)

Phase 2 (Build Together):
- Outline (5-8 key story moments / plot pyramid)
- Beat sheet (30 scenes)
- Characters (protagonist, love interest, supporting - with arcs and flaws)

Supporting Context (capture along the way):
- Theme, tone, comps
- Notebook (misc ideas, fragments, inspirations)

CONVERSATION APPROACH:
- Ask ONE question at a time - never multiple numbered questions
- Be conversational, not form-like - offer ideas and reactions, not interrogations
- React to what they said first, then gently guide with a single follow-up
- When something feels solid, reflect it back: "So the logline might be: [X]. Does that capture it?"
- Wait for user confirmation before locking anything
- Capture stray good ideas in the notebook - "Love that detail, adding it to the notebook"
- Use knowledge buckets when they'd help (see BUCKET USAGE below)

WRONG (too many questions):
"1. What's the setting? 2. What's their job? 3. What's the tone?"

RIGHT (conversational):
"Love that she's the overlooked one - that's such a relatable place to start. What does 'overlooked' look like for her day-to-day? Like, does her roommate always get the guy's attention at parties, or is it more that she makes all the decisions?"

BUCKET USAGE:
You have access to three expert knowledge bases. Query them when the conversation would benefit:
- BOOKS: Structure, beat positioning, plot pyramid, pacing
- PLAYS: Relationship dynamics, classic patterns, archetypal tropes
- SCRIPTS: Tone, comparable films, how specific moments might play

Before responding, consider: "Would insight from a bucket help here?"
If yes, query silently and weave the insight into your response naturally.

PHASE 1: IDEA TO LOGLINE
Draw out the raw idea and shape it:
- The core concept (what's the hook?)
- The protagonist (who are they, what do they want?)
- The love interest (who are they, why compelling?)
- The obstacle (internal flaw + external circumstance)
- The world (setting, profession, context)
- The tone (closer to what films?)

Then lock:
- "Ready to lock the title as: [X]?"
- "Logline locked: [Y]"

PHASE 2: BUILD THE STORY
Once title and logline are locked, develop outline/beats/characters TOGETHER through conversation. These inform each other:
- As you map the plot pyramid, characters emerge
- As you develop characters, new beats become clear
- Keep circling between them naturally

Work through:
- Opening image / status quo
- Inciting incident / meet cute
- Rising action beats
- Midpoint shift
- Crisis / all is lost
- Climax / grand gesture
- Resolution

For characters, develop:
- Role (protagonist, love interest, best friend, obstacle)
- Brief description
- Flaw (what holds them back)
- Arc (how they transform)

TRACKING PROGRESS:
Keep mental track of what's populated:
- [ ] Title
- [ ] Logline
- [ ] Outline (5-8 moments)
- [ ] Beats (30 scenes)
- [ ] Characters (with arcs)

Don't rush to handoff until all are filled. If user tries to move on too fast, gently note what's missing.

HANDOFF:
Once everything is populated:
- "We've got a solid foundation - title, logline, 30 beats, and fleshed-out characters. Ready to move to scene-by-scene brainstorming?"

TONE: Cozy, curious, encouraging. Like a smart friend at a coffee shop who happens to know a lot about screenwriting.

IMPORTANT:
- Never rush. The conversation might need to circle back.
- If user seems stuck, offer options or examples.
- If the idea has structural issues (e.g., no real obstacle), gently probe.
- Capture good fragments in the notebook even if they don't fit yet.

TOOL USAGE - BE PROACTIVE:
You have tools to track project state. USE THEM as information becomes clear:
- When user confirms a title → call lock_title
- When user confirms a logline → call lock_logline
- When a character is defined (name + role) → call add_character immediately
- When user mentions a good idea/detail → call add_to_notebook
- When theme/tone/comps are discussed → call set_theme/set_tone/set_comps

Don't wait for everything to be perfect. If Emma is the protagonist law student, call add_character right away with what you know. You can update characters later as more details emerge.
"""


# =============================================================================
# ROMCOM FRAMEWORK
# =============================================================================
# Same framework used in brainstorm - provides consistent genre guidance

ROMCOM_FRAMEWORK = """ROMANTIC COMEDY FRAMEWORK:
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
- Pride getting in the way
"""


# =============================================================================
# FIELDS TO EXTRACT
# =============================================================================
# These are the structured fields that get populated from the conversation
# and saved to the database.

IDEATE_FIELDS = {
    # Phase 1: Lock First
    "title": None,              # projects.name
    "logline": None,            # writer_notes.logline

    # Phase 2: Build Together (conversationally)
    "outline": [],              # 5-8 key moments (plot pyramid)
    "beats": [],                # 30 scenes for scenes table
    "characters": [],           # characters table (name, role, description, arc, flaw)

    # Supporting Context
    "theme": None,              # writer_notes.theme
    "tone": None,               # writer_notes.tone
    "comps": None,              # writer_notes.comps (comparable films)
    "notebook": [],             # misc ideas, fragments, inspiration that come up
}


# =============================================================================
# TOOL DEFINITIONS
# =============================================================================
# Tools Syd can call to update fields during conversation.

IDEATE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "lock_title",
            "description": "Lock the title after user confirms",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "The confirmed title"}
                },
                "required": ["title"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "lock_logline",
            "description": "Lock the logline after user confirms",
            "parameters": {
                "type": "object",
                "properties": {
                    "logline": {"type": "string", "description": "One sentence: protagonist, goal, obstacle, stakes"}
                },
                "required": ["logline"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_outline_beat",
            "description": "Add a key story moment to the outline (aim for 5-8 total)",
            "parameters": {
                "type": "object",
                "properties": {
                    "beat": {"type": "string", "description": "Description of this story moment"}
                },
                "required": ["beat"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_scene",
            "description": "Add a scene to the beat sheet (30 total)",
            "parameters": {
                "type": "object",
                "properties": {
                    "number": {"type": "integer", "description": "Scene number 1-30"},
                    "title": {"type": "string", "description": "Short evocative title"},
                    "description": {"type": "string", "description": "What happens, what changes"}
                },
                "required": ["number", "title", "description"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_character",
            "description": "Add or update a character",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "role": {"type": "string", "enum": ["protagonist", "love_interest", "best_friend", "obstacle", "supporting"]},
                    "description": {"type": "string", "description": "Who they are"},
                    "flaw": {"type": "string", "description": "What holds them back"},
                    "arc": {"type": "string", "description": "How they transform"}
                },
                "required": ["name", "role"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_to_notebook",
            "description": "Capture a good idea or fragment for later",
            "parameters": {
                "type": "object",
                "properties": {
                    "idea": {"type": "string"}
                },
                "required": ["idea"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_theme",
            "description": "Set the theme",
            "parameters": {
                "type": "object",
                "properties": {
                    "theme": {"type": "string"}
                },
                "required": ["theme"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_tone",
            "description": "Set the tone",
            "parameters": {
                "type": "object",
                "properties": {
                    "tone": {"type": "string"}
                },
                "required": ["tone"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_comps",
            "description": "Set comparable films",
            "parameters": {
                "type": "object",
                "properties": {
                    "comps": {"type": "string", "description": "Comparable films"}
                },
                "required": ["comps"]
            }
        }
    }
]

# =============================================================================
# BUCKET SYSTEM PROMPTS
# =============================================================================

SCRIPTS_BUCKET_PROMPT = """You are a romcom reference expert. Given the current idea development, provide:
- Comparable films or specific scenes that tackle similar beats
- Tone and execution notes
- What to borrow or avoid
Keep response focused and under 400 words."""

BOOKS_BUCKET_PROMPT = """You are a screenplay structure expert. Given the current idea development, provide:
- Plot pyramid positioning and beat suggestions
- Structural considerations for this story
- Pacing and momentum guidance
Keep response focused and under 400 words."""

PLAYS_BUCKET_PROMPT = """You are a patterns and dynamics expert drawing from Shakespeare and timeless drama. Given the current idea development, provide:
- Archetypal patterns that fit (enemies to lovers, mistaken identity, etc.)
- Relationship dynamics to explore
- Classic tropes to deploy or subvert
Keep response focused and under 400 words."""


# =============================================================================
# IDEATE SESSION CLASS
# =============================================================================

class IdeateSession:
    """
    Manages a single ideation conversation from raw idea to locked fundamentals.

    Usage:
        session = IdeateSession(project_name="My Romcom")

        # User submits idea
        response = await session.process_message("I have this idea about a baker...")

        # Continue conversation
        response = await session.process_message("She's a perfectionist...")

        # Get current state
        state = session.get_state()

        # Save to database when fundamentals are locked
        session.save_to_database()
    """

    def __init__(self, project_name: str = None, debug: bool = False):
        """
        Initialize ideation session.

        Args:
            project_name: Optional project name (can be set during conversation)
            debug: If True, print bucket query results
        """
        self.project_name = project_name
        self.debug = debug
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # Conversation history
        self.messages = []

        # Current stage: explore, refine, lock, build_out, complete
        self.stage = "explore"

        # Extracted fields
        self.fields = IDEATE_FIELDS.copy()
        self.fields["characters"] = []  # Reset mutable defaults
        self.fields["outline"] = []
        self.fields["beats"] = []
        self.fields["notebook"] = []

        # Locked status for Phase 1
        self.locked = {
            "title": False,
            "logline": False,
        }

        # Populated status for Phase 2
        self.populated = {
            "outline": False,
            "beats": False,
            "characters": False,
        }

        # RAG bucket instances (lazy loaded)
        self._rag_instances = {}
        self._initialized_buckets = set()
        self.bucket_dir = Path("./rag_buckets")

    # -------------------------------------------------------------------------
    # Main conversation processing
    # -------------------------------------------------------------------------

    async def process_message(self, user_message: str) -> str:
        """
        Process a user message and return AI response.

        Architecture:
        1. Add user message to history
        2. Shape queries based on current state (no LLM)
        3. Query all 3 buckets in parallel (LightRAG)
        4. Synthesize with Syd + tool calling
        5. Execute any tool calls
        6. Return response

        Args:
            user_message: What the user said

        Returns:
            AI response
        """
        # Add user message to history
        self.messages.append({
            "role": "user",
            "content": user_message
        })

        # Shape bucket-specific queries based on state (programmatic, no LLM)
        queries = self._shape_bucket_queries(user_message)

        # Query all 3 buckets in parallel with tailored queries
        insights = await self._get_all_bucket_insights(queries)

        # Build system prompt with current state
        system_content = self._build_system_prompt(insights)

        # Generate response with tool calling
        response = await self.client.chat.completions.create(
            model="gpt-5.1",
            messages=[
                {"role": "system", "content": system_content},
                *self.messages
            ],
            tools=IDEATE_TOOLS,
            temperature=0.8,
        )

        response_message = response.choices[0].message

        # Execute any tool calls
        if response_message.tool_calls:
            for tool_call in response_message.tool_calls:
                self._execute_tool(tool_call)

        ai_message = response_message.content or ""

        # Add AI response to history
        self.messages.append({
            "role": "assistant",
            "content": ai_message
        })

        return ai_message

    async def process_message_stream(self, user_message: str) -> AsyncGenerator[str, None]:
        """
        Process a user message and stream AI response for low latency.

        Same architecture as process_message but yields chunks as they arrive.
        Tool calls are executed after streaming completes.

        Args:
            user_message: What the user said

        Yields:
            Response text chunks
        """
        # Add user message to history
        self.messages.append({
            "role": "user",
            "content": user_message
        })

        # Shape bucket-specific queries based on state (programmatic, no LLM)
        queries = self._shape_bucket_queries(user_message)

        # Query all 3 buckets in parallel with tailored queries (~2-3s)
        insights = await self._get_all_bucket_insights(queries)

        # Build system prompt with current state
        system_content = self._build_system_prompt(insights)

        # Debug: print full prompt
        if self.debug:
            self._debug_print_full_prompt(system_content)

        # Generate streamed response with tool calling
        try:
            stream = await self.client.chat.completions.create(
                model="gpt-5.1",
                messages=[
                    {"role": "system", "content": system_content},
                    *self.messages
                ],
                tools=IDEATE_TOOLS,
                temperature=0.8,
                stream=True,
            )
        except Exception as e:
            print(f"OpenAI API error: {e}")
            error_msg = f"Sorry, I encountered an error: {str(e)}"
            self.messages.append({"role": "assistant", "content": error_msg})
            yield error_msg
            return

        # Accumulate response and tool calls
        full_content = ""
        tool_calls = []
        current_tool_call = None

        try:
            async for chunk in stream:
                delta = chunk.choices[0].delta

                # Handle content
                if delta.content:
                    full_content += delta.content
                    yield delta.content

                # Handle tool calls (accumulate from stream)
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        if tc.index is not None:
                            # New tool call or continuation
                            while len(tool_calls) <= tc.index:
                                tool_calls.append({
                                    "id": "",
                                    "function": {"name": "", "arguments": ""}
                                })
                            if tc.id:
                                tool_calls[tc.index]["id"] = tc.id
                            if tc.function:
                                if tc.function.name:
                                    tool_calls[tc.index]["function"]["name"] = tc.function.name
                                if tc.function.arguments:
                                    tool_calls[tc.index]["function"]["arguments"] += tc.function.arguments
        except Exception as e:
            print(f"Streaming error: {e}")
            error_msg = f"Sorry, streaming failed: {str(e)}"
            self.messages.append({"role": "assistant", "content": error_msg})
            yield error_msg
            return

        # Execute accumulated tool calls
        for tc in tool_calls:
            if tc["function"]["name"]:
                self._execute_tool_from_dict(tc)

        # Add AI response to history
        self.messages.append({
            "role": "assistant",
            "content": full_content
        })

    def _execute_tool_from_dict(self, tool_call_dict: Dict) -> None:
        """Execute a tool call from dictionary format (for streaming)."""
        name = tool_call_dict["function"]["name"]
        try:
            args = json.loads(tool_call_dict["function"]["arguments"])
        except json.JSONDecodeError:
            return

        if name == "lock_title":
            self.lock_field("title", args.get("title"))
        elif name == "lock_logline":
            self.lock_field("logline", args.get("logline"))
        elif name == "add_outline_beat":
            self.fields["outline"].append(args.get("beat"))
            if len(self.fields["outline"]) >= 5:
                self.populated["outline"] = True
        elif name == "add_scene":
            self.fields["beats"].append({
                "number": args.get("number"),
                "title": args.get("title"),
                "description": args.get("description")
            })
            if len(self.fields["beats"]) >= 30:
                self.populated["beats"] = True
        elif name == "add_character":
            existing = next((c for c in self.fields["characters"] if c.get("name") == args.get("name")), None)
            if existing:
                existing.update(args)
            else:
                self.fields["characters"].append(args)
            if len(self.fields["characters"]) >= 3:
                self.populated["characters"] = True
        elif name == "add_to_notebook":
            self.fields["notebook"].append(args.get("idea"))
        elif name == "set_theme":
            self.fields["theme"] = args.get("theme")
        elif name == "set_tone":
            self.fields["tone"] = args.get("tone")
        elif name == "set_comps":
            self.fields["comps"] = args.get("comps")

        # Update stage
        if all(self.locked.values()) and all(self.populated.values()):
            self.stage = "complete"
        elif all(self.locked.values()):
            self.stage = "build_out"

    def _shape_bucket_queries(self, user_message: str) -> Dict[str, str]:
        """
        Shape bucket-specific queries based on current state.
        Each bucket gets a tailored query for what it's best at.

        Returns dict with 'scripts', 'books', 'plays' queries.
        """
        # Extract key concepts from current state
        logline = self.fields.get('logline') or ''
        title = self.fields.get('title') or ''

        # Extract character info
        chars = self.fields.get('characters', [])
        protagonist = next((c for c in chars if c.get('role') == 'protagonist'), {})
        love_interest = next((c for c in chars if c.get('role') == 'love_interest'), {})

        protagonist_desc = protagonist.get('description', '') or protagonist.get('flaw', '')
        love_interest_desc = love_interest.get('description', '')

        # Build core concept from user message + logline
        core_concept = f"{user_message} {logline}".strip()

        # Determine phase
        in_phase_1 = not self.locked['title'] or not self.locked['logline']

        if in_phase_1:
            # Phase 1: Exploring concept - need comparable films, archetypes, premise patterns

            # Scripts: Find similar films and tone references
            scripts_query = f"romantic comedy films with premise: {core_concept}"

            # Books: Character archetypes and story structure for this type
            if protagonist_desc:
                books_query = f"protagonist character arc: {protagonist_desc} romantic comedy structure"
            else:
                books_query = f"romantic comedy story structure premise: {core_concept}"

            # Plays: Relationship dynamics and classic patterns
            plays_query = f"romantic comedy relationship dynamics patterns: {core_concept}"

        else:
            # Phase 2: Building beats - need structural guidance, scene examples, specific patterns

            outline_count = len(self.fields.get('outline', []))
            beats_count = len(self.fields.get('beats', []))

            # Scripts: Specific scene examples and execution
            if beats_count < 10:
                scripts_query = f"romantic comedy opening scenes meet cute examples: {logline}"
            elif beats_count < 20:
                scripts_query = f"romantic comedy midpoint scenes turning point examples: {logline}"
            else:
                scripts_query = f"romantic comedy climax resolution grand gesture scenes: {logline}"

            # Books: Beat sheet structure and pacing
            if outline_count < 5:
                books_query = f"romantic comedy plot structure key beats outline: {logline}"
            else:
                books_query = f"romantic comedy 30 scene beat sheet pacing: {logline}"

            # Plays: Character dynamics for current development
            if protagonist_desc and love_interest_desc:
                plays_query = f"romantic comedy character dynamics: {protagonist_desc} and {love_interest_desc}"
            else:
                plays_query = f"romantic comedy relationship arc transformation: {logline}"

        return {
            'scripts': scripts_query,
            'books': books_query,
            'plays': plays_query
        }

    async def _get_all_bucket_insights(self, queries: Dict[str, str]) -> Dict[str, str]:
        """
        Query all three buckets in parallel using LightRAG.
        Each bucket gets its own tailored query.

        Args:
            queries: Dict with 'scripts', 'books', 'plays' query strings

        Returns:
            Dict with insights from each bucket
        """
        async def query_bucket(bucket_name: str, query: str) -> str:
            rag = self._get_rag_instance(bucket_name)
            if not rag:
                return ""

            try:
                # Initialize only if not already done
                if bucket_name not in self._initialized_buckets:
                    await rag.initialize_storages()
                    self._initialized_buckets.add(bucket_name)

                # Query with bucket-specific query (30s timeout)
                response = await asyncio.wait_for(
                    rag.aquery(query, param=QueryParam(mode="local")),
                    timeout=30.0
                )
                return response or ""
            except asyncio.TimeoutError:
                print(f"Bucket query timeout ({bucket_name})")
                return ""
            except Exception as e:
                print(f"Bucket query error ({bucket_name}): {e}")
                return ""

        # Run all three in parallel with their specific queries
        scripts, books, plays = await asyncio.gather(
            query_bucket("scripts", queries.get('scripts', '')),
            query_bucket("books", queries.get('books', '')),
            query_bucket("plays", queries.get('plays', ''))
        )

        if self.debug:
            _original_print("\n" + "="*60)
            _original_print("BUCKET DEBUG")
            _original_print("="*60)
            _original_print(f"\nSCRIPTS QUERY: {queries.get('scripts', '')}")
            _original_print(f"BOOKS QUERY: {queries.get('books', '')}")
            _original_print(f"PLAYS QUERY: {queries.get('plays', '')}\n")
            _original_print("-"*60)
            _original_print(f"SCRIPTS ({len(scripts)} chars):")
            _original_print("-"*60)
            _original_print(scripts if scripts else "(empty)")
            _original_print("\n" + "-"*60)
            _original_print(f"BOOKS ({len(books)} chars):")
            _original_print("-"*60)
            _original_print(books if books else "(empty)")
            _original_print("\n" + "-"*60)
            _original_print(f"PLAYS ({len(plays)} chars):")
            _original_print("-"*60)
            _original_print(plays if plays else "(empty)")
            _original_print("="*60 + "\n")

        return {
            "scripts": scripts,
            "books": books,
            "plays": plays
        }

    def _debug_print_full_prompt(self, system_content: str):
        """Print the full assembled system prompt for debugging."""
        _original_print("\n" + "="*60)
        _original_print("FULL SYSTEM PROMPT SENT TO GPT-5.1")
        _original_print("="*60)
        _original_print(system_content)
        _original_print("="*60 + "\n")

    def _build_system_prompt(self, insights: Dict[str, str]) -> str:
        """
        Build the full system prompt with Syd's personality,
        current state, and bucket insights.
        """
        # Current progress
        progress = f"""
CURRENT PROGRESS:
- Title: {'✓ ' + self.fields['title'] if self.locked['title'] else '○ not locked'}
- Logline: {'✓ locked' if self.locked['logline'] else '○ not locked'}
- Outline: {len(self.fields.get('outline', []))}/8 beats
- Scenes: {len(self.fields.get('beats', []))}/30
- Characters: {len(self.fields.get('characters', []))} defined
"""

        # Bucket insights
        insights_section = f"""
YOUR EXPERT KNOWLEDGE:

You have deep expertise in screenwriting. Below is relevant context from your knowledge of films, craft, and dramatic patterns. Draw on this naturally as an expert would—mentioning comparable films, structural principles, or character dynamics when they genuinely illuminate the conversation. Don't force references, but don't hold back your expertise either. You're not just asking questions; you're a knowledgeable collaborator who brings real insight.

SCRIPTS (films, tone, execution):
{insights.get('scripts', 'No insight available')[:2000]}

BOOKS (structure, beats, craft):
{insights.get('books', 'No insight available')[:2000]}

PLAYS (patterns, dynamics, archetypes):
{insights.get('plays', 'No insight available')[:2000]}
"""

        return IDEATE_SYSTEM_PROMPT + progress + insights_section

    def _execute_tool(self, tool_call) -> None:
        """Execute a tool call and update session state."""
        import json

        name = tool_call.function.name
        args = json.loads(tool_call.function.arguments)

        if name == "lock_title":
            self.lock_field("title", args["title"])
        elif name == "lock_logline":
            self.lock_field("logline", args["logline"])
        elif name == "add_outline_beat":
            self.fields["outline"].append(args["beat"])
            if len(self.fields["outline"]) >= 5:
                self.populated["outline"] = True
        elif name == "add_scene":
            self.fields["beats"].append({
                "number": args["number"],
                "title": args["title"],
                "description": args["description"]
            })
            if len(self.fields["beats"]) >= 30:
                self.populated["beats"] = True
        elif name == "add_character":
            # Check if character exists, update or add
            existing = next((c for c in self.fields["characters"] if c.get("name") == args["name"]), None)
            if existing:
                existing.update(args)
            else:
                self.fields["characters"].append(args)
            if len(self.fields["characters"]) >= 3:
                self.populated["characters"] = True
        elif name == "add_to_notebook":
            self.fields["notebook"].append(args["idea"])
        elif name == "set_theme":
            self.fields["theme"] = args["theme"]
        elif name == "set_tone":
            self.fields["tone"] = args["tone"]
        elif name == "set_comps":
            self.fields["comps"] = args["comps"]

        # Update stage
        if all(self.locked.values()) and all(self.populated.values()):
            self.stage = "complete"
        elif all(self.locked.values()):
            self.stage = "build_out"

    def _get_rag_instance(self, bucket_name: str) -> Optional[LightRAG]:
        """Get or create a LightRAG instance for a bucket (lazy loading)."""
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

    # -------------------------------------------------------------------------
    # Field locking
    # -------------------------------------------------------------------------

    def lock_field(self, field_name: str, value) -> None:
        """
        Lock or populate a field value.

        Args:
            field_name: Which field
            value: The value to set
        """
        if field_name in self.fields:
            self.fields[field_name] = value

        # Update locked status (Phase 1)
        if field_name in self.locked:
            self.locked[field_name] = True

        # Update populated status (Phase 2)
        if field_name in self.populated:
            # Check if actually has content
            if isinstance(value, list) and len(value) > 0:
                self.populated[field_name] = True
            elif value:
                self.populated[field_name] = True

        # Update stage based on progress
        if all(self.locked.values()) and self.stage == "explore":
            self.stage = "build_out"
        if all(self.locked.values()) and all(self.populated.values()):
            self.stage = "complete"

    def get_state(self) -> Dict:
        """
        Get current session state.

        Returns:
            Dict with stage, fields, locked/populated status
        """
        return {
            "stage": self.stage,
            "fields": self.fields,
            "locked": self.locked,
            "populated": self.populated,
            "message_count": len(self.messages),
            "ready_for_handoff": all(self.locked.values()) and all(self.populated.values()),
        }

    # -------------------------------------------------------------------------
    # Database integration
    # -------------------------------------------------------------------------

    def save_to_database(self, db_path: Path) -> int:
        """
        Save locked fields to database.

        Creates project and populates:
        - projects table (name/title)
        - writer_notes table (logline, theme, tone, comps)
        - characters table (name, role, description, arc)
        - scenes table (if beats are populated)

        Args:
            db_path: Path to project database

        Returns:
            Project ID
        """
        db = Database(db_path)

        # Create project
        project_name = self.fields.get("title") or self.project_name or "Untitled Project"
        project_id = db.create_project(project_name)

        # Save writer notes
        writer_notes = {
            "logline": self.fields.get("logline"),
            "theme": self.fields.get("theme"),
            "tone": self.fields.get("tone"),
            "comps": self.fields.get("comps"),
            "inspiration": self.fields.get("inspiration"),
        }
        # Filter out None values
        writer_notes = {k: v for k, v in writer_notes.items() if v}
        if writer_notes:
            db.save_writer_notes(project_id, writer_notes)

        # Save characters
        characters = self.fields.get("characters", [])
        for char in characters:
            char_data = {
                "name": char.get("name"),
                "role": char.get("role"),
                "description": char.get("description"),
            }
            # Add arc info if we have it from character_arcs
            arc_info = self.fields.get("character_arcs", {}).get(char.get("name"), {})
            if arc_info:
                char_data["flaw"] = arc_info.get("flaw")
                char_data["arc"] = arc_info.get("arc")

            db.save_character(project_id, char_data)

        # Save beats as scenes if populated
        beats = self.fields.get("beats", [])
        for beat in beats:
            scene_data = {
                "scene_number": beat.get("scene_number"),
                "title": beat.get("title"),
                "description": beat.get("description"),
                "characters": beat.get("characters", []),
            }
            db.save_scene(project_id, scene_data)

        return project_id

    # -------------------------------------------------------------------------
    # Parallel build-out (Stage 4)
    # -------------------------------------------------------------------------

    async def build_outline(self) -> List[str]:
        """
        Generate 5-8 key story moments from locked fundamentals.

        Uses the logline and characters to propose major beats
        before expanding to full 30-scene beat sheet.

        Returns:
            List of key moments
        """
        # Query BOOKS bucket for structure guidance
        structure_insight = await self._query_bucket(
            "books",
            f"What are the key structural beats for a romantic comedy with this logline: {self.fields.get('logline')}"
        )

        outline_prompt = f"""Based on these locked fundamentals, generate 5-8 key story moments.

TITLE: {self.fields.get('title')}
LOGLINE: {self.fields.get('logline')}
CHARACTERS: {self.fields.get('characters')}

{ROMCOM_FRAMEWORK}

{f"STRUCTURE INSIGHT: {structure_insight}" if structure_insight else ""}

Generate 5-8 key moments that form the spine of this story. Each should be a single sentence describing a major turning point or beat.

Format as a numbered list:
1. [Opening situation/status quo]
2. [Inciting incident/meet cute]
...etc

Return ONLY the numbered list."""

        response = await self.client.chat.completions.create(
            model="gpt-5.1",
            messages=[{"role": "user", "content": outline_prompt}],
            temperature=0.7,
        )

        # Parse numbered list
        outline_text = response.choices[0].message.content
        outline = []
        for line in outline_text.strip().split('\n'):
            line = line.strip()
            if line and line[0].isdigit():
                # Remove number prefix
                moment = line.split('.', 1)[-1].strip()
                outline.append(moment)

        self.fields["outline"] = outline
        return outline

    async def expand_to_beats(self, outline: List[str]) -> List[Dict]:
        """
        Expand outline to 30-scene beat sheet.

        Args:
            outline: The 5-8 key moments

        Returns:
            List of 30 scene dicts (scene_number, title, description, characters)
        """
        beats_prompt = f"""Expand this outline into a 30-scene beat sheet for a romantic comedy.

TITLE: {self.fields.get('title')}
LOGLINE: {self.fields.get('logline')}
CHARACTERS: {self.fields.get('characters')}

OUTLINE:
{chr(10).join(f"{i+1}. {moment}" for i, moment in enumerate(outline))}

{ROMCOM_FRAMEWORK}

Generate exactly 30 scenes. For each scene provide:
- Scene number (1-30)
- Title (short, evocative)
- Description (2-3 sentences: what happens, what changes)
- Characters present

Format as JSON array:
[
  {{"scene_number": 1, "title": "...", "description": "...", "characters": ["Name1", "Name2"]}},
  ...
]

Return ONLY the JSON array."""

        response = await self.client.chat.completions.create(
            model="gpt-5.1",
            messages=[{"role": "user", "content": beats_prompt}],
            temperature=0.7,
        )

        try:
            import json
            beats = json.loads(response.choices[0].message.content)
            self.fields["beats"] = beats
            return beats
        except json.JSONDecodeError:
            return []

    async def develop_character_arcs(self) -> Dict:
        """
        Develop full character arcs from brief descriptions.

        Expands initial character briefs into:
        - Full description
        - Flaw
        - Arc (transformation)
        - Relationships to other characters

        Returns:
            Dict of character name -> expanded details
        """
        # Query PLAYS bucket for relationship dynamics
        dynamics_insight = await self._query_bucket(
            "plays",
            f"What relationship dynamics work well for characters like: {self.fields.get('characters')}"
        )

        characters = self.fields.get("characters", [])
        character_names = [c.get("name") for c in characters]

        arcs_prompt = f"""Develop full character arcs for this romantic comedy.

TITLE: {self.fields.get('title')}
LOGLINE: {self.fields.get('logline')}
CHARACTERS: {self.fields.get('characters')}

{f"RELATIONSHIP INSIGHT: {dynamics_insight}" if dynamics_insight else ""}

For each character, provide:
- Full description (2-3 sentences)
- Flaw (what holds them back)
- Arc (how they transform)
- Relationships (to other main characters)

Format as JSON object:
{{
  "Character Name": {{
    "description": "...",
    "flaw": "...",
    "arc": "...",
    "relationships": {{"Other Character": "nature of relationship"}}
  }}
}}

Return ONLY the JSON object."""

        response = await self.client.chat.completions.create(
            model="gpt-5.1",
            messages=[{"role": "user", "content": arcs_prompt}],
            temperature=0.7,
        )

        try:
            import json
            arcs = json.loads(response.choices[0].message.content)
            self.fields["character_arcs"] = arcs
            return arcs
        except json.JSONDecodeError:
            return {}

    async def run_parallel_build_out(self) -> Dict:
        """
        Run the full Stage 4 build-out in parallel.

        Generates outline and character arcs simultaneously,
        then expands to full beat sheet.

        Returns:
            Dict with outline, beats, and character_arcs
        """
        # Run outline and character arcs in parallel
        outline_task = asyncio.create_task(self.build_outline())
        arcs_task = asyncio.create_task(self.develop_character_arcs())

        outline, character_arcs = await asyncio.gather(outline_task, arcs_task)

        # Then expand to beats (needs outline)
        beats = await self.expand_to_beats(outline)

        self.stage = "complete"

        return {
            "outline": outline,
            "beats": beats,
            "character_arcs": character_arcs
        }


# =============================================================================
# CLI INTERFACE (for testing)
# =============================================================================

async def main():
    """Simple CLI for testing ideation flow with streaming."""
    import sys
    import os

    # Suppress LightRAG noise
    os.environ["LIGHTRAG_LOG_LEVEL"] = "ERROR"

    print("=" * 60)
    print("LIZZY IDEATE - Conversational Pre-Planning")
    print("=" * 60)
    print("\nHi! I'm Syd. Got an idea for a romantic comedy?")
    print("Tell me anything - a character, a situation, a vibe.\n")

    session = IdeateSession(debug=False)

    while True:
        user_input = input("You: ").strip()

        if user_input.lower() in ["quit", "exit", "q"]:
            break

        if not user_input:
            continue

        # Stream response for low latency
        print("\nSyd: ", end="", flush=True)
        async for chunk in session.process_message_stream(user_input):
            print(chunk, end="", flush=True)
        print("\n")

        # Show state for debugging
        state = session.get_state()
        if any(state["locked"].values()):
            locked_items = [k for k, v in state["locked"].items() if v]
            print(f"[Locked: {', '.join(locked_items)}]")
            # Show actual locked values
            fields = state["fields"]
            if fields.get("title"):
                print(f"  Title: {fields['title']}")
            if fields.get("logline"):
                print(f"  Logline: {fields['logline']}")
        if any(state["populated"].values()):
            populated_items = [k for k, v in state["populated"].items() if v]
            print(f"[Populated: {', '.join(populated_items)}]")
            # Show counts
            fields = state["fields"]
            if fields.get("outline"):
                print(f"  Outline: {len(fields['outline'])} beats")
            if fields.get("beats"):
                print(f"  Beats: {len(fields['beats'])} scenes")
            if fields.get("characters"):
                print(f"  Characters: {[c.get('name') for c in fields['characters']]}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
