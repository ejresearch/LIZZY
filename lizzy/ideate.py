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
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from openai import AsyncOpenAI
from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import openai_embed

from .database import Database


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

IDEATE_SYSTEM_PROMPT = """You are Elle, a warm and collaborative screenwriting partner helping develop romantic comedy ideas.

GOAL: Guide the user from a loose idea to locked fundamentals through natural conversation.

FUNDAMENTALS TO LOCK:
1. Title
2. Logline (one sentence that captures protagonist, goal, obstacle, stakes)
3. Main characters (protagonist, love interest, key supporting - just names and brief descriptions for now)

CONVERSATION APPROACH:
- Ask one question at a time
- Be encouraging but push for specificity
- When something feels solid, reflect it back: "So the logline might be: [X]. Does that capture it?"
- Wait for user confirmation before locking anything
- Use knowledge buckets when they'd help (see BUCKET USAGE below)

BUCKET USAGE:
You have access to three expert knowledge bases. Query them when the conversation would benefit:
- BOOKS: When discussing structure, character arcs, protagonist flaws, story vs situation
- PLAYS: When discussing relationship dynamics, classic patterns, thematic depth
- SCRIPTS: When discussing tone, comparable films, how specific moments might play

Before responding, consider: "Would insight from a bucket help here?"
If yes, query silently and weave the insight into your response naturally.

CONVERSATION STAGES:

STAGE 1: EXPLORE
Draw out the raw idea. Ask about:
- The core concept (what's the hook?)
- The protagonist (who is she/he, what do they want?)
- The love interest (who are they, why are they compelling?)
- The obstacle (what's keeping them apart - internal and external?)
- The world (setting, profession, context)
- The tone (closer to what films?)

STAGE 2: REFINE
Shape what you've learned into fundamentals:
- Propose 2-3 logline options, ask which resonates
- Suggest title ideas based on tone and concept
- Clarify main character dynamics

STAGE 3: LOCK
Confirm each fundamental explicitly:
- "Ready to lock the title as: [X]?"
- "Logline locked: [Y]"
- "Main characters locked: [Z]"

STAGE 4: HANDOFF
Once fundamentals are locked, transition to parallel build-out:
- "Great - we've got our foundation. Now let's develop the outline, beats, and character arcs together."

TONE: Cozy, curious, encouraging. Like a smart friend at a coffee shop who happens to know a lot about screenwriting.

IMPORTANT:
- Never rush to lock. The conversation might need to circle back.
- If user seems stuck, offer options or examples.
- If user's idea has structural issues (e.g., no real obstacle), gently probe - use BOOKS bucket for insight.
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
    # Stage 1-3: Lock Fundamentals
    "title": None,              # projects.name
    "logline": None,            # writer_notes.logline
    "characters": [],           # characters table (name, role, brief description)

    # Stage 4: Parallel Build-out
    "theme": None,              # writer_notes.theme
    "tone": None,               # writer_notes.tone
    "comps": None,              # writer_notes.comps (comparable films)
    "inspiration": None,        # writer_notes.inspiration
    "outline": [],              # 5-8 key moments before full beat sheet
    "beats": [],                # 30 scenes for scenes table
    "character_arcs": {},       # expanded character details (arcs, flaws, relationships)
}


# =============================================================================
# BUCKET QUERY LOGIC
# =============================================================================
# The AI decides when to query buckets based on conversation context.
# This helper determines which bucket might be useful.

BUCKET_TRIGGERS = {
    "books": [
        "structure", "arc", "flaw", "protagonist", "three act", "beat",
        "want vs need", "transformation", "stakes", "obstacle", "setup",
        "midpoint", "climax", "resolution", "story vs situation"
    ],
    "plays": [
        "dynamic", "relationship", "power", "vulnerability", "pattern",
        "archetype", "enemies to lovers", "mistaken identity", "trope",
        "shakespeare", "classic", "theme", "undercurrent", "subtext"
    ],
    "scripts": [
        "tone", "vibe", "feels like", "similar to", "reminds me of",
        "comparable", "reference", "example", "how did they", "execution",
        "dialogue style", "pacing"
    ]
}


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

    def __init__(self, project_name: str = None):
        """
        Initialize ideation session.

        Args:
            project_name: Optional project name (can be set during conversation)
        """
        self.project_name = project_name
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
        self.fields["character_arcs"] = {}

        # Locked status
        self.locked = {
            "title": False,
            "logline": False,
            "characters": False,
        }

        # RAG bucket instances (lazy loaded)
        self._rag_instances = {}
        self.bucket_dir = Path("./rag_buckets")

    # -------------------------------------------------------------------------
    # Main conversation processing
    # -------------------------------------------------------------------------

    async def process_message(self, user_message: str) -> str:
        """
        Process a user message and return AI response.

        This is the main conversation loop. The AI:
        1. Considers the conversation history
        2. Decides if a bucket query would help
        3. Generates a response that advances toward locking fundamentals

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

        # Check if we should query a bucket
        bucket_insight = await self._maybe_query_bucket(user_message)

        # Build the prompt with any bucket insight
        system_content = IDEATE_SYSTEM_PROMPT
        if bucket_insight:
            system_content += f"\n\n[BUCKET INSIGHT - weave naturally into response]\n{bucket_insight}"

        # Generate response
        response = await self.client.chat.completions.create(
            model="gpt-5.1",  # Using 5.1 for main ideation conversation
            messages=[
                {"role": "system", "content": system_content},
                *self.messages
            ],
            temperature=0.8,  # Slightly creative for ideation
        )

        ai_message = response.choices[0].message.content

        # Add AI response to history
        self.messages.append({
            "role": "assistant",
            "content": ai_message
        })

        # Extract any locked fields from the response
        await self._extract_fields(ai_message)

        return ai_message

    async def _extract_fields(self, ai_message: str) -> None:
        """
        Parse AI response for locked fundamentals.

        Looks for explicit lock phrases like:
        - "Title locked: X"
        - "Logline locked: X"
        - "Main characters locked: X"

        Uses GPT to extract structured data when lock phrases are detected.
        """
        message_lower = ai_message.lower()

        # Check for lock indicators
        has_title_lock = "title locked" in message_lower or "lock the title" in message_lower
        has_logline_lock = "logline locked" in message_lower or "lock the logline" in message_lower
        has_character_lock = "characters locked" in message_lower or "lock the characters" in message_lower

        if not (has_title_lock or has_logline_lock or has_character_lock):
            return

        # Use GPT to extract structured fields
        extraction_prompt = f"""Extract any locked fundamentals from this message.

MESSAGE:
{ai_message}

Return a JSON object with only the fields that were explicitly locked:
{{
    "title": "extracted title or null",
    "logline": "extracted logline or null",
    "characters": [
        {{"name": "...", "role": "protagonist/love_interest/supporting", "description": "brief description"}}
    ] or null
}}

Only include fields that were EXPLICITLY LOCKED in the message. Return valid JSON only."""

        response = await self.client.chat.completions.create(
            model="gpt-5.1",
            messages=[{"role": "user", "content": extraction_prompt}],
            temperature=0,
        )

        try:
            import json
            extracted = json.loads(response.choices[0].message.content)

            if extracted.get("title"):
                self.lock_field("title", extracted["title"])
            if extracted.get("logline"):
                self.lock_field("logline", extracted["logline"])
            if extracted.get("characters"):
                self.lock_field("characters", extracted["characters"])

        except json.JSONDecodeError:
            # Extraction failed, continue without locking
            pass

    # -------------------------------------------------------------------------
    # Bucket query logic
    # -------------------------------------------------------------------------

    async def _maybe_query_bucket(self, user_message: str) -> Optional[str]:
        """
        Decide if a bucket query would help and execute if so.

        Looks for trigger words in the user message and conversation context
        to determine which bucket (if any) to query.

        Args:
            user_message: Latest user message

        Returns:
            Bucket insight or None
        """
        message_lower = user_message.lower()

        # Check each bucket for trigger words
        for bucket_name, triggers in BUCKET_TRIGGERS.items():
            for trigger in triggers:
                if trigger in message_lower:
                    # Found a trigger - query this bucket
                    return await self._query_bucket(bucket_name, user_message)

        return None

    async def _query_bucket(self, bucket_name: str, query: str) -> Optional[str]:
        """
        Query a specific bucket for insight.

        Args:
            bucket_name: books, plays, or scripts
            query: The query to send

        Returns:
            Bucket response or None
        """
        bucket_path = self.bucket_dir / bucket_name

        if not bucket_path.exists():
            return None

        # Lazy load RAG instance
        if bucket_name not in self._rag_instances:
            self._rag_instances[bucket_name] = LightRAG(
                working_dir=str(bucket_path),
                embedding_func=openai_embed,
                llm_model_func=gpt_5_1_complete,
            )
            await self._rag_instances[bucket_name].initialize_storages()

        rag = self._rag_instances[bucket_name]

        try:
            response = await rag.aquery(query, param=QueryParam(mode="hybrid"))
            return response
        except Exception as e:
            print(f"Bucket query error: {e}")
            return None

    # -------------------------------------------------------------------------
    # Field extraction and locking
    # -------------------------------------------------------------------------

    def lock_field(self, field_name: str, value) -> None:
        """
        Lock a field value.

        Args:
            field_name: Which field (title, logline, characters)
            value: The value to lock
        """
        if field_name in self.fields:
            self.fields[field_name] = value
        if field_name in self.locked:
            self.locked[field_name] = True

        # Check if all fundamentals are locked
        if all(self.locked.values()):
            self.stage = "build_out"

    def get_state(self) -> Dict:
        """
        Get current session state.

        Returns:
            Dict with stage, fields, locked status
        """
        return {
            "stage": self.stage,
            "fields": self.fields,
            "locked": self.locked,
            "message_count": len(self.messages),
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
    """Simple CLI for testing ideation flow."""
    print("=" * 60)
    print("LIZZY IDEATE - Conversational Pre-Planning")
    print("=" * 60)
    print("\nHi! I'm Elle. Got an idea for a romantic comedy?")
    print("Tell me anything - a character, a situation, a vibe.\n")

    session = IdeateSession()

    while True:
        user_input = input("You: ").strip()

        if user_input.lower() in ["quit", "exit", "q"]:
            break

        if not user_input:
            continue

        response = await session.process_message(user_input)
        print(f"\nElle: {response}\n")

        # Show state for debugging
        state = session.get_state()
        if any(state["locked"].values()):
            locked_items = [k for k, v in state["locked"].items() if v]
            print(f"[Locked: {', '.join(locked_items)}]\n")


if __name__ == "__main__":
    asyncio.run(main())
