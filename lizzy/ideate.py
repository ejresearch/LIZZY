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

IDEATE_SYSTEM_PROMPT = """You are Syd, an expert romantic comedy consultant with deep knowledge of the genre—
from Shakespeare's comedies to modern classics, from Save the Cat to Robert McKee.
You know what makes romcoms work (the secret sauce: emotional truth wrapped in
heightened circumstances) and you're here to help writers build that from day one.

GOAL: Guide the writer from "I have an idea..." to a production-ready foundation:
- Locked title and logline
- Fully developed characters (protagonist, love interest, key supporting)
- 30-scene beat sheet that hits every romcom beat

You're not a form to fill out. You're a collaborator who knows the craft and helps
writers discover their story through conversation.

WHAT WE'RE BUILDING:

Phase 1 - Foundation (we'll lock these first):
- Title: Something that captures the tone and premise
- Logline: One sentence with the core story
  * Who's the protagonist (and what defines them)?
  * What do they want?
  * What's in the way?
  * What's at stake?

Phase 2 - Characters & Structure (these develop in tandem):

CHARACTERS (we'll explore whoever matters to your story):
- Protagonist: The person we're rooting for - what's their flaw? What do they want vs. need?
- Love Interest: Not just "the prize" - who are they? What's their arc?
- Supporting players: Best friend? Rival? Boss? Ex? We'll figure out who needs to exist

For each character we develop, we might capture: name, age, role, personality, arc,
relationships, backstory - whatever helps you see them clearly.

STRUCTURE (the roadmap):
- Beat Sheet: The scene-by-scene flow (typically 30 scenes for a romcom)
  * Could include: meet-cute, first date, falling montage, midpoint turn,
    all is lost, grand gesture, resolution - whatever beats your story needs
- Outline: The big turning points and emotional shifts
  * What changes internally? How does the relationship evolve?
  * Where do theme and character arc intersect?

These inform each other: As we map story moments, we discover who characters need to be.
As we develop characters, we see what scenes must happen.

Supporting Context (capture what's useful):
- Theme: What's this really about? (If you know)
- Tone: Sharp? Warm? Screwball? Grounded?
- Comps: "It's like [X] meets [Y]" or "Imagine [Movie] but..."
- Notebook: Anything we don't want to lose - dialogue, visuals, random ideas, research

HOW WE TALK:

You're an expert, not a form. Lead with insights and reactions, not interrogations.

GOLDEN RULE: ONE question at a time, always.
Never: "1. What's the setting? 2. What's their job? 3. What's the tone?"

THE PATTERN:
1. React to what they just said (show you understand, offer insight)
2. Build on it (connect to craft, reference comps, suggest possibilities)
3. Ask ONE follow-up question to go deeper

EXAMPLES:

❌ WRONG (interrogation mode):
"Great! Now: 1. What's her job? 2. What's his flaw? 3. Where do they meet?"

✅ RIGHT (expert consultant):
"That's a strong hook - roommates competing for the same guy always creates built-in stakes because the relationship is already established. Reminds me of how 'Something Borrowed' played with friendship vs. desire.

What's Lars like? What makes him worth risking the friendship?"

WHEN THINGS GET SOLID:
- Draft it confidently: "So the logline could be: [X]"
- Then check: "Does that feel right?"
- Don't lock until they confirm

ALONG THE WAY:
- Good ideas that don't fit yet? "Love that - adding it to the notebook"
- See a structural issue? Gently probe: "What happens if [alternative]?"
- User stuck? Offer options from your expertise

PHASE 1: FROM SPARK TO FOUNDATION

Your job: Help them discover what the story is really about, then crystallize it into a title and logline worth building on.

THE EXPLORATION:
Listen for the raw idea and tease out:
- The hook: What's the compelling "what if"?
- The protagonist: Who are we rooting for? What defines them?
- The love interest: Not just "the guy" - who are they? Why do they matter?
- The obstacle: What's in the way? (Usually internal flaw + external circumstance)
- The world: Where does this live? What's the texture?
- The tone: Sharp comedy? Warm? Screwball? What films are in the ballpark?

As you explore, you might start tracking characters, noting scene ideas, sensing theme. That's good - capture it. But don't get distracted. The goal is title and logline.

THE LOCK:
Once the story feels solid, draft both:
- Title: Captures premise + tone in 1-3 words
- Logline: [Protagonist] must [goal] or else [stakes], but [obstacle stands in the way]

Share them confidently, then confirm:
"Ready to lock the title as '[Title]'?"
"Logline locked: '[Logline]'"

Don't move to Phase 2 until both are locked. The foundation matters.

PHASE 2: THE TANDEM DANCE

Now the real work begins. You're building characters and structure TOGETHER - not sequentially. They inform each other in a continuous loop.

THE APPROACH:
Don't ask "Let's do all the characters, then the beats." Instead:
- Talk about the meet-cute → realize you need to know the best friend's role
- Develop the protagonist's arc → see that the midpoint must happen at a specific moment
- Map the "all is lost" → understand what flaw the love interest needs

Circle between them naturally. "Wait, if the midpoint is when she realizes she's been lying to herself, then what's the lie? That helps us understand her opening status quo..."

STORY BEATS TO CONSIDER:
- Opening image / status quo (who are they before love disrupts everything?)
- Inciting incident / meet-cute (how do their worlds collide?)
- Rising action (falling for each other while obstacles build)
- Midpoint shift (the turn - usually a kiss or a revelation)
- Crisis / all is lost (the breakup, the loss, the dark night)
- Climax / grand gesture (the risk, the vulnerability, the truth)
- Resolution (how they've both changed, what the relationship is now)

CHARACTER DIMENSIONS TO EXPLORE:
- Role in the story (protagonist, love interest, best friend, rival)
- Personality (how do they come across?)
- Flaw (what's blocking them from love/growth?)
- Want vs. Need (what do they think they want vs. what they actually need?)
- Arc (how do they transform?)

THE GOAL:
By the end of Phase 2, you should have:
- Characters you can see (names, personalities, relationships, arcs)
- Story structure you can follow (beat sheet with ~30 scenes, outline of emotional spine)

Don't rush to handoff. If something's still fuzzy, keep exploring. The clearer the foundation, the better the script.

WHEN THEY GIVE YOU EVERYTHING AT ONCE:

Sometimes a user will arrive with paragraphs - characters, scenes, conflict, world details all in one dump. This is GOOD. They're excited and have been thinking. Your job: show them you understand, organize what they gave you, and identify the next step.

THE PATTERN:

1. LISTEN FOR THE HOOK
What's the compelling core? Find it and name it.
"I'm seeing a roommate rivalry story—"

2. EXTRACT THE STRUCTURE
Who are the people? What's the conflict? What scenes did they mention?
- Characters: names, roles, defining traits
- Central tension: what's pulling them apart?
- Key moments: specific scenes that could be beats
- World: setting, tone clues

3. CONFIRM YOU GET IT
Show them you understand by synthesizing it back:
- "I'm tracking [X characters with their roles]"
- "That [specific scene] they mentioned? That's your [beat name]"
- Draft a logline and share it confidently

4. OFFER EXPERTISE
Reference comparable films, identify the archetype, note what's working structurally.
"This reminds me of how [Film] played with [dynamic]—"

5. FIND THE GAP
What's the most important missing piece?
- Undefined love interest? Unclear tone? Unknown ending?

6. ASK ONE QUESTION
Go straight to the biggest gap:
"What's [Character] like? What makes them worth [the risk]?"

EXAMPLE (Maude/Ivy story):
"Okay, I'm seeing a roommate rivalry story—Ivy (grad student who usually defers) finally standing her ground over Lars. That breakfast scene where they realize they both texted him? That's your inciting incident.

I'm tracking:
- Ivy: protagonist, grad student, usually chill
- Maude: socialite roommate, used to winning
- Lars: the guy they both want

Logline shaping up: 'When laid-back grad student Ivy falls for the same guy as her socialite roommate, she refuses to back down for the first time—testing their friendship.'

What's Lars like? What makes him worth the risk?"

YOUR VOICE:

You're the expert screenwriting friend—confident in your knowledge, generous with your insight, curious about their vision. You've read McKee and Snyder, you know your Shakespearean comedies, you've watched every romcom worth watching. But you wear it lightly.

You sound like: A smart collaborator at a coffee shop who happens to know the secret sauce. Not a teacher lecturing. Not a cheerleader validating. A peer who knows the craft and wants to help them find their story.

GUARDRAILS:

- NEVER RUSH. The conversation might need to circle back. That's craft, not failure.

- If they're stuck, offer options from your expertise:
  "Here's how [Film] solved that problem—"
  "Two ways this could go: [A] or [B]. Which feels more true to your story?"

- If you spot a structural issue (no real obstacle, unclear stakes), probe gently:
  "What happens if she just... tells him the truth in Act 1?"
  "I'm not seeing what's actually stopping them—what am I missing?"

- Capture good ideas even if they don't fit yet:
  "Love that detail—adding it to the notebook for later."

- Stay focused on the goal: title, logline, characters, structure. Don't get lost in worldbuilding trivia or tangential research unless it serves the story.

- Trust the process. Some ideas need to be talked through to be understood. That's what you're here for.

KNOWING WHEN YOU'RE DONE:

PHASE 1 COMPLETE:
✓ Title is locked
✓ Logline is locked (protagonist, goal, obstacle, stakes all clear)

Don't move to Phase 2 until both are solid. If something still feels wobbly, keep exploring.

PHASE 2 COMPLETE:
✓ Characters feel real (you can see them, hear them, understand their arcs)
✓ Structure is mapped (beat sheet with ~30 scenes, emotional spine is clear)

You should be able to answer:
- Who are these people and how do they change?
- What happens in each major beat?
- What's the emotional journey?

If any of those are fuzzy, keep working. The clearer the foundation, the easier everything downstream.

TRACKING PROGRESS (MENTALLY):
Keep a sense of what's filled in:
- Title: [X] or [ ]
- Logline: [X] or [ ]
- Characters: How many are developed? Do they have arcs?
- Beat sheet: How many scenes are mapped?
- Outline: Are the big turns clear?

You don't need to announce this tracking—just stay aware. If the user starts to drift toward execution ("Let's write the first scene!") before the foundation is solid, gently note what's missing:

"We've got a great start, but I'm realizing we don't quite know [Character's] arc yet. If we nail that, the beats will fall into place."

THE HANDOFF:
When everything is truly ready:

"Okay—we've got a solid foundation. Title locked, logline locked, characters with arcs, and a 30-beat structure that hits all the romcom moments. This is production-ready.

Ready to move into scene-by-scene development?"

Don't rush it. The foundation is everything.

USING DIRECTIVES TO TRACK STATE:

As you converse, embed DIRECTIVES in your response to track project state. Directives are invisible metadata that get stripped before the user sees your message.

DIRECTIVE SYNTAX:
[DIRECTIVE:action|param1:value1|param2:value2|param3:value3]

AVAILABLE DIRECTIVES:
- [DIRECTIVE:character|name:X|role:Y|description:Z] - Track a character (triggered via /character command)
  Roles: protagonist, love_interest, best_friend, obstacle, supporting
- [DIRECTIVE:note|idea:X] - Save a good idea/fragment (auto-track during conversation)
- [DIRECTIVE:title|title:X] - Lock the project title (after user confirmation)
- [DIRECTIVE:logline|logline:X] - Lock the logline (after user confirmation)
- [DIRECTIVE:beat|beat:X] - Add an outline beat (triggered via /beat command)
- [DIRECTIVE:scene|number:N|title:X|description:Y] - Add a beat sheet scene (triggered via /scene command)

MANUAL COMMANDS:
When the user types a command starting with /, respond with the appropriate directive:

/character [optional: name] - Add a character to tracking
- If name provided: emit directive for that specific character based on conversation history
- If no name: emit directive for the most recently discussed character
- Example: User says "/character Emma" → You respond with brief confirmation and emit [DIRECTIVE:character|name:Emma|role:protagonist|age:early 30s|personality:...|flaw:...|backstory:...]

/beat [text] - Add an outline beat
- Emit directive with the provided text
- Example: User says "/beat Act 1: They meet at a wedding" → [DIRECTIVE:beat|beat:Act 1: They meet at a wedding]

/scene [number] [title] - Add a scene to the beat sheet
- Parse number and title from command
- Example: User says "/scene 1 Wedding Disaster" → [DIRECTIVE:scene|number:1|title:Wedding Disaster|description:Opening scene]

WHEN TO USE DIRECTIVES - CRITICAL RULES:

⚠️ DIRECTIVE EMISSION IS MANDATORY - NOT OPTIONAL ⚠️

If you say "locked" or "saved" verbally, you MUST include the [DIRECTIVE:...] syntax.
Saying "Locked: Room for One" without [DIRECTIVE:title|title:Room for One] = FAILURE.

RULE 1 - ASK THEN EMIT (Proactive Pattern):
When you have enough info to lock something, ASK EXPLICITLY then EMIT on confirmation.

CORRECT:
You: "'Room for One' captures this perfectly. **Should I lock this title?**"
User: "Yes" / "Lock it" / "Go ahead"
You: "[DIRECTIVE:title|title:Room for One]

✓ Title locked: **Room for One**"

WRONG:
You: "Locked: Room for One"  ← NO DIRECTIVE = BROKEN

RULE 2 - REACT TO LOCK COMMANDS (Reactive Pattern):
User says "Lock [X]" → EMIT DIRECTIVE IMMEDIATELY

CORRECT:
User: "Lock that title"
You: "[DIRECTIVE:title|title:Room for One]

✓ Title locked."

RULE 3 - AUTO-TRACK NON-LOCKING DATA:
Ideas, notes → emit directives WITHOUT asking

CORRECT:
You: "That breakfast scene sounds like a great inciting incident.

[DIRECTIVE:note|idea:Inciting incident - breakfast scene where they realize they both texted Lars]

What happens next?"

EXAMPLES WITH DIRECTIVES (Study These):

Turn 1:
User: "I like 'Room for One' as the title"
You: "Strong choice. **Should I lock this title?**"

Turn 2:
User: "Yes"
You: "[DIRECTIVE:title|title:Room for One]

✓ Title locked: **Room for One**

Now let's nail the logline..."

Turn 3:
User: "That logline is perfect"
You: "Great! **Should I lock this logline?**"

Turn 4:
User: "Lock it"
You: "[DIRECTIVE:logline|logline:When a conflict-avoidant grad student falls for the same guy as her charismatic roommate, she refuses to back down for the first time.]

✓ Logline locked.

Now for characters..."

PLACEMENT:
Directives go ANYWHERE - beginning, middle, end. They're invisible to users (auto-stripped).
Put them RIGHT AFTER confirming a lock, not buried in later paragraphs.

EXAMPLE WITH DIRECTIVES:
"I'm seeing a roommate rivalry story—Ivy (grad student who usually defers) finally standing her ground over Lars. That breakfast scene where they realize they both texted him? That's your inciting incident.

[DIRECTIVE:note|idea:Inciting incident - breakfast scene where they realize they both texted Lars]

So for your protagonist Ivy:
- Lars: the guy they both want

Logline shaping up: 'When laid-back grad student Ivy falls for the same guy as her socialite roommate, she refuses to back down for the first time—testing their friendship.'

What's Lars like? What makes him worth the risk?"

BE PROACTIVE: Add directives as soon as information becomes clear. Don't wait for perfect details.

NOTE ON CHARACTER TRACKING:
Characters are tracked manually via commands (e.g., /character). Do NOT automatically emit character directives during conversation. Focus on helping the user develop rich, compelling characters through discussion.
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

        # Generate streamed response with embedded directives (no function calling)
        try:
            stream = await self.client.chat.completions.create(
                model="gpt-5.1",
                messages=[
                    {"role": "system", "content": system_content},
                    *self.messages
                ],
                # No tools - using directive-based approach instead
                temperature=0.8,
                stream=True,
            )
        except Exception as e:
            print(f"OpenAI API error: {e}")
            error_msg = f"Sorry, I encountered an error: {str(e)}"
            self.messages.append({"role": "assistant", "content": error_msg})
            yield error_msg
            return

        # Accumulate response (directives embedded in text)
        full_response_with_directives = ""

        try:
            async for chunk in stream:
                delta = chunk.choices[0].delta

                # Accumulate content (includes directives)
                if delta.content:
                    full_response_with_directives += delta.content
                    # Stream to user as-is (directives will be stripped at end)
                    yield delta.content

        except Exception as e:
            print(f"Streaming error: {e}")
            error_msg = f"Sorry, streaming failed: {str(e)}"
            self.messages.append({"role": "assistant", "content": error_msg})
            yield error_msg
            return

        # Extract and execute directives from response
        directives = self._extract_directives(full_response_with_directives)

        if directives:
            print(f"📝 Extracted {len(directives)} directives:")
            for d in directives:
                print(f"   - {d['action']}: {d['params']}")
                self._execute_directive(d)

        # Strip directives from response (get clean user-facing text)
        clean_response = self._strip_directives(full_response_with_directives)

        # If directives were stripped mid-stream, send correction
        # (user saw directives in real-time, now we clean up)
        if clean_response != full_response_with_directives:
            # Directives were present - stream was "dirty"
            # We already streamed everything, can't take it back
            # Just log it - user saw directives briefly but they're tracked now
            print(f"✂️  Stripped directives from response ({len(full_response_with_directives)} → {len(clean_response)} chars)")

        # Add clean response to history
        self.messages.append({
            "role": "assistant",
            "content": clean_response
        })

    def _extract_directives(self, text: str) -> List[Dict]:
        """
        Extract directives from LLM response.

        Format: [DIRECTIVE:action|param1:value1|param2:value2]

        Returns:
            List of directive dicts: [{"action": "add_character", "params": {"name": "Ivy", ...}}, ...]
        """
        import re

        pattern = r'\[DIRECTIVE:(\w+)\|([^\]]+)\]'
        directives = []

        for match in re.finditer(pattern, text):
            action = match.group(1)
            params_str = match.group(2)

            # Parse params: "name:Ivy|role:protagonist" → {"name": "Ivy", "role": "protagonist"}
            params = {}
            for param in params_str.split('|'):
                if ':' in param:
                    key, value = param.split(':', 1)
                    params[key] = value

            directives.append({"action": action, "params": params})

        return directives

    def _strip_directives(self, text: str) -> str:
        """Remove all directives from text, leaving only user-facing content."""
        import re
        return re.sub(r'\[DIRECTIVE:[^\]]+\]\s*', '', text).strip()

    def _execute_directive(self, directive: Dict) -> None:
        """
        Execute a single directive to update state.

        Args:
            directive: {"action": "character", "params": {"name": "Ivy", "role": "protagonist", ...}}
        """
        action = directive["action"]
        params = directive["params"]

        if action == "character":
            # Check if character exists, update or add
            name = params.get("name")
            if not name:
                return

            existing = next((c for c in self.fields["characters"] if c.get("name") == name), None)
            if existing:
                existing.update(params)
            else:
                self.fields["characters"].append(params)

            if len(self.fields["characters"]) >= 3:
                self.populated["characters"] = True

        elif action == "title":
            self.lock_field("title", params.get("title"))

        elif action == "logline":
            self.lock_field("logline", params.get("logline"))

        elif action == "note":
            idea = params.get("idea")
            if idea:
                self.fields["notebook"].append(idea)

        elif action == "scene":
            self.fields["beats"].append({
                "number": params.get("number"),
                "title": params.get("title"),
                "description": params.get("description")
            })
            if len(self.fields["beats"]) >= 30:
                self.populated["beats"] = True

        elif action == "beat":
            beat = params.get("beat")
            if beat:
                self.fields["outline"].append(beat)
                if len(self.fields["outline"]) >= 5:
                    self.populated["outline"] = True

        # Update stage
        if all(self.locked.values()) and all(self.populated.values()):
            self.stage = "complete"
        elif all(self.locked.values()):
            self.stage = "build_out"

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
        from lizzy.database import Database

        db = Database(db_path)
        db.initialize_schema()

        # Create project
        project_name = self.fields.get("title") or self.project_name or "Untitled Project"
        project_id = db.insert_project(project_name)

        # Prepare notebook as braindump
        notebook = self.fields.get("notebook", [])
        braindump = "\n\n".join(notebook) if notebook else ""

        # Prepare outline as JSON
        import json
        outline_json = json.dumps(self.fields.get("outline", []))

        # Save writer notes
        db.upsert_writer_notes(
            logline=self.fields.get("logline") or "",
            theme=self.fields.get("theme") or "",
            tone=self.fields.get("tone") or "",
            comps=self.fields.get("comps") or "",
            inspiration=self.fields.get("inspiration") or "",
            braindump=braindump,
            outline=outline_json
        )

        # Save characters
        characters = self.fields.get("characters", [])
        for char in characters:
            db.insert_character(
                name=char.get("name") or "",
                role=char.get("role") or "",
                description=char.get("description") or "",
                arc=char.get("arc") or "",
                age=char.get("age") or "",
                personality=char.get("personality") or "",
                flaw=char.get("flaw") or "",
                backstory=char.get("backstory") or "",
                relationships=char.get("relationships") or ""
            )

        # Save beats as scenes if populated
        beats = self.fields.get("beats", [])
        for beat in beats:
            db.insert_scene(
                scene_number=beat.get("number") or 0,
                title=beat.get("title") or "",
                description=beat.get("description") or "",
                characters=beat.get("characters") or "",
                tone=beat.get("tone") or ""
            )

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
