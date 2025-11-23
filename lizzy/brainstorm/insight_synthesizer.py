"""
Insight Synthesizer for Automated Brainstorm

Combines expert perspectives from multiple knowledge buckets into unified scene guidance.
"""

from typing import Dict, List, Optional
from datetime import datetime
from openai import AsyncOpenAI
from rich.console import Console

console = Console()


class InsightSynthesizer:
    """Synthesizes insights from expert knowledge buckets."""

    def __init__(self, project_context: Dict):
        """
        Initialize synthesizer with project context.

        Args:
            project_context: Dict containing project, characters, scenes, writer_notes
        """
        self.project = project_context.get('project')
        self.characters = project_context.get('characters', [])
        self.scenes = project_context.get('scenes', [])
        self.writer_notes = project_context.get('writer_notes')

    def build_story_outline(self) -> str:
        """
        Build a comprehensive story outline from project context.

        Returns:
            Formatted story outline string
        """
        outline_parts = []

        # Project metadata
        if self.project:
            outline_parts.append(f"PROJECT: {self.project['name']}")
            outline_parts.append(f"Genre: {self.project.get('genre', 'Unknown')}")
            if self.project.get('description'):
                outline_parts.append(f"Description: {self.project['description']}")

        # Writer notes
        if self.writer_notes:
            outline_parts.append("\nWRITER NOTES:")
            if self.writer_notes.get('logline'):
                outline_parts.append(f"Logline: {self.writer_notes['logline']}")
            if self.writer_notes.get('theme'):
                outline_parts.append(f"Theme: {self.writer_notes['theme']}")
            if self.writer_notes.get('tone'):
                outline_parts.append(f"Tone: {self.writer_notes['tone']}")

        # Characters
        if self.characters:
            outline_parts.append("\nCHARACTERS:")
            for char in self.characters:
                outline_parts.append(f"- {char['name']} ({char.get('role', 'unknown')}): {char.get('description', 'No description')}")

        # Scene count
        if self.scenes:
            outline_parts.append(f"\nTOTAL SCENES: {len(self.scenes)}")

        return "\n".join(outline_parts)

    def get_surrounding_context(self, scene: Dict) -> Dict[str, Optional[str]]:
        """
        Get context from previous and next scenes.

        Args:
            scene: Current scene dictionary

        Returns:
            Dict with 'previous' and 'next' scene descriptions
        """
        scene_num = scene['scene_number']

        # Find previous scene
        previous = None
        for s in self.scenes:
            if s['scene_number'] == scene_num - 1:
                previous = f"Scene {s['scene_number']}: {s['title']} - {s.get('description', '')}"
                break

        # Find next scene
        next_scene = None
        for s in self.scenes:
            if s['scene_number'] == scene_num + 1:
                next_scene = f"Scene {s['scene_number']}: {s['title']} - {s.get('description', '')}"
                break

        return {
            'previous': previous,
            'next': next_scene
        }

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
        metadata = f"""---
SCENE_ID: {scene['id']}
SCENE_NUMBER: {scene['scene_number']}
ACT: {scene.get('act', 'Unknown')}
BUCKET: synthesis
MODEL: "gpt-5"
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
                model="gpt-5",
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
