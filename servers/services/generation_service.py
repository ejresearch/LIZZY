"""
AI generation business logic.
Handles AI-powered content generation like random rom-com concepts.
"""

import os
import json
from pathlib import Path
from typing import Dict
from openai import OpenAI

from ..config import config
from ..logging_config import get_logger
from lizzy.write import WriteModule

logger = get_logger(__name__)


class GenerationService:
    """Service for AI-powered content generation."""

    def __init__(self, projects_dir: Path = None):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.projects_dir = projects_dir or config.projects_dir

    async def generate_random_romcom(self) -> Dict:
        """Generate a random romantic comedy project using AI."""
        try:
            # AI prompt to generate a complete rom-com concept
            prompt = """Generate a complete romantic comedy screenplay concept in JSON format. Be creative and mindful - create interesting, flawed characters with depth, compelling scene descriptions, and thoughtful thematic notes.

Return ONLY valid JSON with this exact structure:
{
  "name": "A catchy title (2-4 words)",
  "logline": "A one-sentence high-concept logline that captures the romantic premise and central conflict",
  "characters": [
    {
      "name": "Character name",
      "role": "protagonist|love interest|best friend|obstacle|mentor|supporting",
      "description": "Rich character description with personality, flaws, goals, and arc (2-3 sentences)"
    }
  ],
  "scenes": [
    {
      "scene_number": 1,
      "act": 1,
      "title": "Scene title (3-6 words)",
      "description": "Detailed scene description (2-3 sentences)",
      "characters": "Character1, Character2"
    }
  ],
  "notes": {
    "theme": "The deeper meaning - what is this story really about? (2-3 sentences)",
    "tone": "The emotional feel and style of the screenplay (2-3 sentences)",
    "comparable_films": "3-5 similar films with brief explanations of why",
    "inspiration": "Additional creative notes, influences, or unique angles for this story"
  }
}

Create exactly 4-6 well-developed characters and 30 scenes following the standard romantic comedy beat sheet structure (Act 1: scenes 1-6, Act 2: scenes 7-24, Act 3: scenes 25-30). Make it fresh, funny, and emotionally resonant."""

            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an expert romantic comedy screenwriter. Generate creative, emotionally resonant story concepts."},
                    {"role": "user", "content": prompt}
                ],
                temperature=1.0,
                response_format={"type": "json_object"}
            )

            project_data = json.loads(response.choices[0].message.content)

            return {
                "success": True,
                "project": project_data
            }

        except Exception as e:
            logger.error(f"Error generating random rom-com: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    async def export_scene_screenplay(
        self,
        project_name: str,
        scene_number: int,
        version: int = 1,
        output_format: str = "docx"
    ) -> Dict:
        """
        Export a scene draft as formatted screenplay.

        Args:
            project_name: Name of the project
            scene_number: Scene number to export
            version: Draft version (default: 1)
            output_format: Format (txt, docx, or pdf)

        Returns:
            Success status and file details
        """
        try:
            # Initialize WRITE module
            writer = WriteModule(project_name)

            # Get the draft
            drafts = writer.get_all_drafts(scene_number)
            if not drafts:
                return {
                    "success": False,
                    "error": f"No drafts found for scene {scene_number}"
                }

            # Find the requested version
            draft = next((d for d in drafts if d.version == version), None)
            if not draft:
                return {
                    "success": False,
                    "error": f"Version {version} not found for scene {scene_number}"
                }

            # Export
            output_path, is_valid, errors = writer.export_draft(
                draft,
                output_format=output_format,
                validate=True
            )

            # Get filename from path
            filename = Path(output_path).name

            return {
                "success": True,
                "filename": filename,
                "path": output_path,
                "is_valid": is_valid,
                "errors": errors if not is_valid else [],
                "scene_number": scene_number,
                "version": version,
                "format": output_format
            }

        except Exception as e:
            logger.error(f"Error exporting scene: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    async def export_full_screenplay(
        self,
        project_name: str,
        scenes: list,
        output_format: str = "docx"
    ) -> Dict:
        """
        Export full screenplay combining all scenes.

        Args:
            project_name: Name of the project
            scenes: List of dicts with scene_number and version
            output_format: Format (txt, docx, or pdf)

        Returns:
            Success status and file details
        """
        try:
            # Initialize WRITE module
            writer = WriteModule(project_name)

            # Collect all scene drafts
            all_content = []
            for scene_info in scenes:
                scene_number = scene_info['scene_number']
                version = scene_info['version']

                # Get the draft
                drafts = writer.get_all_drafts(scene_number)
                draft = next((d for d in drafts if d.version == version), None)

                if draft:
                    all_content.append(draft.content)

            if not all_content:
                return {
                    "success": False,
                    "error": "No drafts found to export"
                }

            # Combine all scenes with separators
            full_screenplay = '\n\n\n'.join(all_content)

            # Create a temporary draft-like object for export
            from dataclasses import dataclass
            from datetime import datetime

            @dataclass
            class FullScreenplayDraft:
                scene_id: int
                scene_number: int
                content: str
                version: int
                word_count: int
                tokens_used: int
                cost_estimate: float
                created_at: str

            combined_draft = FullScreenplayDraft(
                scene_id=0,
                scene_number=0,  # Special: 0 means full screenplay
                content=full_screenplay,
                version=1,
                word_count=len(full_screenplay.split()),
                tokens_used=0,
                cost_estimate=0.0,
                created_at=datetime.now().isoformat()
            )

            # Export using the writer's export method
            output_path, is_valid, errors = writer.export_draft(
                combined_draft,
                output_format=output_format,
                validate=True
            )

            # Rename file to indicate full screenplay
            from pathlib import Path
            old_path = Path(output_path)
            new_filename = f"{project_name}_FULL_SCREENPLAY.{output_format}"
            new_path = old_path.parent / new_filename

            # Rename the file
            old_path.rename(new_path)

            return {
                "success": True,
                "filename": new_filename,
                "path": str(new_path),
                "is_valid": is_valid,
                "errors": errors if not is_valid else [],
                "scene_count": len(scenes),
                "format": output_format
            }

        except Exception as e:
            logger.error(f"Error exporting full screenplay: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
