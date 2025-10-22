"""
AI Block Composer

Takes natural language input and automatically builds prompt blocks.

Example:
    "Jenny in scene 4 dealing with disappointment, check scripts bucket"

    → Parses to: {character: "Jenny", scene: 4, topic: "disappointment", bucket: "scripts"}
    → Builds blocks: [SceneBlock(4), ScriptsQueryBlock("disappointment scenes")]
    → Returns assembled prompt
"""

import os
import json
import sqlite3
from typing import Dict, List, Optional, Any
from openai import AsyncOpenAI

from .engine import PromptEngine, PromptResult
from .blocks import (
    SceneBlock,
    CharacterBiosBlock,
    BooksQueryBlock,
    PlaysQueryBlock,
    ScriptsQueryBlock,
    MultiExpertQueryBlock,
    TextBlock,
    SectionHeaderBlock,
    PreviousSceneBlock,
    NextSceneBlock,
)


class EntityParser:
    """
    Uses LLM to parse natural language and extract entities.
    """

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        self.client = AsyncOpenAI(api_key=api_key)

    async def parse(self, user_input: str, project_name: str) -> Dict[str, Any]:
        """
        Parse natural language input to extract entities.

        Args:
            user_input: Natural language from user
            project_name: Current project name

        Returns:
            Dictionary with extracted entities
        """

        system_prompt = """You are an entity extraction system for a screenplay writing tool.

Extract the following entities from user input:
- scene_reference: Any mention of scene numbers, acts (e.g., "scene 4", "act 1 scene 4")
- character_names: Any character names mentioned
- topic: What the user is asking about or working on
- buckets: Which knowledge buckets to query (books, plays, scripts, or "all")
- include_context: Whether to include surrounding scenes (true/false)
- intent: What the user wants (get_inspiration, analyze_scene, get_feedback, explore_idea)

Return ONLY a JSON object with these fields. If a field is not mentioned, omit it or use null.

Examples:

Input: "Jenny in scene 4 dealing with disappointment, check scripts bucket"
Output: {
  "scene_reference": "scene 4",
  "character_names": ["Jenny"],
  "topic": "dealing with disappointment",
  "buckets": ["scripts"],
  "intent": "get_inspiration"
}

Input: "I'm stuck on the wedding scene where Mark confesses, what do the plays say about dramatic confessions?"
Output: {
  "topic": "wedding scene where Mark confesses",
  "character_names": ["Mark"],
  "buckets": ["plays"],
  "intent": "get_inspiration"
}

Input: "Help me with act 2 scene 12, need all three experts"
Output: {
  "scene_reference": "act 2 scene 12",
  "buckets": ["all"],
  "intent": "get_inspiration"
}
"""

        user_prompt = f"""Project: {project_name}

User input: {user_input}

Extract entities and return JSON:"""

        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            max_tokens=500
        )

        # Parse JSON response
        content = response.choices[0].message.content.strip()

        # Remove markdown code blocks if present
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        try:
            parsed = json.loads(content)
            return parsed
        except json.JSONDecodeError as e:
            # Fallback: return raw content as topic
            return {
                "topic": user_input,
                "intent": "get_inspiration",
                "error": f"Failed to parse LLM response: {e}"
            }


class SQLLookup:
    """
    Looks up entities in the project database.
    """

    def __init__(self, project_name: str):
        self.project_name = project_name
        self.db_path = f"projects/{project_name}/{project_name}.db"

    def find_scene_number(self, scene_reference: str) -> Optional[int]:
        """
        Find scene number from natural language reference.

        Args:
            scene_reference: e.g., "scene 4", "act 1 scene 4", "the wedding scene"

        Returns:
            Scene number or None
        """
        if not os.path.exists(self.db_path):
            return None

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Try exact number match first
        import re
        numbers = re.findall(r'\d+', scene_reference)
        if numbers:
            scene_num = int(numbers[-1])  # Take last number (handles "act 1 scene 4")
            cursor.execute("SELECT scene_number FROM scenes WHERE scene_number = ?", (scene_num,))
            result = cursor.fetchone()
            if result:
                conn.close()
                return result[0]

        # Try fuzzy match on title
        cursor.execute("SELECT scene_number, title FROM scenes")
        scenes = cursor.fetchall()
        conn.close()

        # Simple fuzzy matching
        scene_ref_lower = scene_reference.lower()
        for scene_num, title in scenes:
            if title and scene_ref_lower in title.lower():
                return scene_num

        return None

    def find_characters(self, character_names: List[str]) -> List[Dict]:
        """
        Find character data from names.

        Args:
            character_names: List of character names

        Returns:
            List of character dicts with name, description, role, arc
        """
        if not os.path.exists(self.db_path):
            return []

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        characters = []
        for name in character_names:
            cursor.execute(
                "SELECT name, description, role, arc FROM characters WHERE name LIKE ?",
                (f"%{name}%",)
            )
            result = cursor.fetchone()
            if result:
                characters.append(dict(result))

        conn.close()
        return characters

    def get_all_scene_titles(self) -> List[Dict]:
        """Get all scenes with their numbers and titles"""
        if not os.path.exists(self.db_path):
            return []

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT scene_number, title FROM scenes ORDER BY scene_number")
        scenes = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return scenes


class BlockBuilder:
    """
    Builds blocks from parsed entities.
    """

    def __init__(self, project_name: str):
        self.project_name = project_name
        self.sql_lookup = SQLLookup(project_name)

    def build(self, parsed: Dict[str, Any]) -> List:
        """
        Build blocks from parsed entities.

        Args:
            parsed: Parsed entities from EntityParser

        Returns:
            List of Block instances
        """
        blocks = []

        # Add scene block if scene reference found
        if "scene_reference" in parsed and parsed["scene_reference"]:
            scene_num = self.sql_lookup.find_scene_number(parsed["scene_reference"])
            if scene_num:
                blocks.append(SectionHeaderBlock(title=f"SCENE {scene_num}"))
                blocks.append(SceneBlock(scene_number=scene_num))

                # Add context if requested
                if parsed.get("include_context", False):
                    if scene_num > 1:
                        blocks.append(SectionHeaderBlock(title="PREVIOUS SCENE"))
                        blocks.append(PreviousSceneBlock(scene_number=scene_num))
                    if scene_num < 30:
                        blocks.append(SectionHeaderBlock(title="NEXT SCENE"))
                        blocks.append(NextSceneBlock(scene_number=scene_num))

        # Add character info if character names found
        if "character_names" in parsed and parsed["character_names"]:
            characters = self.sql_lookup.find_characters(parsed["character_names"])
            if characters:
                blocks.append(SectionHeaderBlock(title="CHARACTERS"))
                char_info = []
                for char in characters:
                    char_info.append(f"\n{char['name']}:")
                    if char.get('role'):
                        char_info.append(f"  Role: {char['role']}")
                    if char.get('description'):
                        char_info.append(f"  {char['description']}")
                blocks.append(TextBlock("\n".join(char_info)))

        # Add topic as context
        if "topic" in parsed and parsed["topic"]:
            blocks.append(SectionHeaderBlock(title="WORKING ON"))
            blocks.append(TextBlock(parsed["topic"]))

        # Add RAG queries based on buckets
        if "buckets" in parsed and parsed["buckets"]:
            query = self._build_query(parsed)

            blocks.append(SectionHeaderBlock(title="EXPERT GUIDANCE"))

            if "all" in parsed["buckets"]:
                blocks.append(MultiExpertQueryBlock(query=query))
            else:
                for bucket in parsed["buckets"]:
                    if bucket == "books":
                        blocks.append(BooksQueryBlock(query=query))
                    elif bucket == "plays":
                        blocks.append(PlaysQueryBlock(query=query))
                    elif bucket == "scripts":
                        blocks.append(ScriptsQueryBlock(query=query))

        # If no blocks were built, add a fallback
        if not blocks:
            blocks.append(TextBlock(f"Query: {parsed.get('topic', 'General question')}"))

        return blocks

    def _build_query(self, parsed: Dict[str, Any]) -> str:
        """Build RAG query from parsed entities"""
        parts = []

        if "topic" in parsed:
            parts.append(parsed["topic"])

        if "character_names" in parsed and parsed["character_names"]:
            char_str = ", ".join(parsed["character_names"])
            parts.append(f"focusing on characters: {char_str}")

        if not parts:
            parts.append("general screenplay writing advice")

        return " ".join(parts)


class AIBlockComposer:
    """
    Main AI Block Composer class.

    Takes natural language input and automatically builds + executes blocks.
    """

    def __init__(self, project_name: str):
        self.project_name = project_name
        self.parser = EntityParser()
        self.block_builder = BlockBuilder(project_name)
        self.engine = PromptEngine()

    async def compose(self, user_input: str) -> PromptResult:
        """
        Compose and execute blocks from natural language.

        Args:
            user_input: Natural language input

        Returns:
            PromptResult with assembled prompt and metadata
        """
        # Step 1: Parse entities
        parsed = await self.parser.parse(user_input, self.project_name)

        # Step 2: Build blocks
        blocks = self.block_builder.build(parsed)

        # Step 3: Assemble prompt
        result = self.engine.assemble(blocks, self.project_name)

        # Attach parsed entities to result for debugging
        result.parsed_entities = parsed
        result.blocks_used = [b.get_description() for b in blocks]

        return result

    async def compose_prompt_only(self, user_input: str) -> str:
        """
        Quick helper that returns just the assembled prompt string.

        Args:
            user_input: Natural language input

        Returns:
            Assembled prompt string
        """
        result = await self.compose(user_input)
        return result.prompt
