"""
Executes Syd's tool calls against SQLite and LightRAG.
When a tool is executed, it also syncs to Hindsight.
"""

import json
from typing import Any
from api.database import db


class SydToolExecutor:
    """Executes tool calls from Syd and syncs to Hindsight."""

    def __init__(self, hindsight_client=None, bank_id: str = None, bucket_manager=None):
        """
        Args:
            hindsight_client: Optional Hindsight client for memory sync
            bank_id: The Hindsight bank ID for this project
            bucket_manager: Optional BucketManager for LightRAG queries
        """
        self.hindsight = hindsight_client
        self.bank_id = bank_id
        self.bucket_manager = bucket_manager

    async def execute(self, tool_name: str, arguments: dict[str, Any]) -> dict:
        """
        Execute a tool call and return the result.
        Also syncs changes to Hindsight if configured.
        """
        handlers = {
            # Bucket tools
            "query_bucket": self._query_bucket,
            # Outline tools
            "update_project": self._update_project,
            "update_notes": self._update_notes,
            "create_character": self._create_character,
            "update_character": self._update_character,
            "delete_character": self._delete_character,
            "create_scene": self._create_scene,
            "update_scene": self._update_scene,
            "delete_scene": self._delete_scene,
        }

        handler = handlers.get(tool_name)
        if not handler:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}

        try:
            result = await handler(arguments)
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}

    # =========================================================================
    # BUCKET QUERIES
    # =========================================================================

    async def _query_bucket(self, args: dict) -> dict:
        """Query a LightRAG bucket for domain expertise."""
        bucket = args.get("bucket")
        query = args.get("query")

        if not self.bucket_manager:
            return {"success": False, "error": "Bucket manager not configured"}

        try:
            # Query the bucket using LightRAG
            result = await self.bucket_manager.query_bucket(
                bucket_name=bucket,
                query=query,
                mode="hybrid"
            )

            # Optionally retain the query to Hindsight for context
            await self._sync_to_hindsight(
                f"Queried {bucket} for: {query}"
            )

            return {
                "success": True,
                "bucket": bucket,
                "query": query,
                "result": result
            }
        except Exception as e:
            return {"success": False, "error": f"Bucket query failed: {str(e)}"}

    async def _sync_to_hindsight(self, content: str):
        """Sync a piece of information to Hindsight memory."""
        if self.hindsight and self.bank_id:
            try:
                await self.hindsight.retain(bank_id=self.bank_id, content=content)
            except Exception as e:
                print(f"Hindsight sync failed: {e}")

    # =========================================================================
    # PROJECT
    # =========================================================================

    async def _update_project(self, args: dict) -> dict:
        db.update_project(**args)

        # Sync to Hindsight
        parts = []
        if args.get("title"):
            parts.append(f"Project title: {args['title']}")
        if args.get("logline"):
            parts.append(f"Logline: {args['logline']}")
        if args.get("genre"):
            parts.append(f"Genre: {args['genre']}")
        if args.get("description"):
            parts.append(f"Project description: {args['description']}")

        if parts:
            await self._sync_to_hindsight("\n".join(parts))

        return {"success": True, "message": "Project updated"}

    # =========================================================================
    # WRITER NOTES
    # =========================================================================

    async def _update_notes(self, args: dict) -> dict:
        db.update_writer_notes(**args)

        # Sync to Hindsight
        parts = []
        if args.get("theme"):
            parts.append(f"Theme: {args['theme']}")
        if args.get("tone"):
            parts.append(f"Tone: {args['tone']}")
        if args.get("comps"):
            parts.append(f"Comparable films: {args['comps']}")
        if args.get("braindump"):
            parts.append(f"Writer notes: {args['braindump']}")

        if parts:
            await self._sync_to_hindsight("\n".join(parts))

        return {"success": True, "message": "Notes updated"}

    # =========================================================================
    # CHARACTERS
    # =========================================================================

    async def _create_character(self, args: dict) -> dict:
        char = db.create_character(**args)

        # Sync to Hindsight
        char_summary = self._format_character_summary(char)
        await self._sync_to_hindsight(f"New character created: {char_summary}")

        return {"success": True, "character_id": char.get("id"), "message": f"Created character: {char.get('name')}"}

    async def _update_character(self, args: dict) -> dict:
        char_id = args.pop("character_id")
        db.update_character(char_id, **args)

        # Sync to Hindsight
        char = db.get_character(char_id)
        if char:
            char_summary = self._format_character_summary(char)
            await self._sync_to_hindsight(f"Character updated: {char_summary}")

        return {"success": True, "message": f"Updated character ID {char_id}"}

    async def _delete_character(self, args: dict) -> dict:
        char_id = args["character_id"]
        char = db.get_character(char_id)
        name = char.get("name", "Unknown") if char else "Unknown"

        db.delete_character(char_id)

        await self._sync_to_hindsight(f"Character deleted: {name}")

        return {"success": True, "message": f"Deleted character: {name}"}

    def _format_character_summary(self, char: dict) -> str:
        """Format character info for Hindsight retention."""
        parts = [char.get("name", "Unnamed")]
        if char.get("role"):
            parts.append(f"({char['role']})")
        if char.get("age"):
            parts.append(f"age {char['age']}")
        if char.get("description"):
            parts.append(f"- {char['description']}")
        if char.get("flaw"):
            parts.append(f"Flaw: {char['flaw']}")
        if char.get("arc"):
            parts.append(f"Arc: {char['arc']}")
        if char.get("personality"):
            parts.append(f"Personality: {char['personality']}")
        if char.get("backstory"):
            parts.append(f"Backstory: {char['backstory']}")
        if char.get("relationships"):
            parts.append(f"Relationships: {char['relationships']}")
        return " ".join(parts)

    # =========================================================================
    # SCENES
    # =========================================================================

    async def _create_scene(self, args: dict) -> dict:
        # db.create_scene handles beats array -> JSON conversion
        scene = db.create_scene(**args)

        # Sync to Hindsight
        scene_summary = self._format_scene_summary(scene)
        await self._sync_to_hindsight(f"New scene created: {scene_summary}")

        return {"success": True, "scene_id": scene.get("id"), "message": f"Created scene {scene.get('scene_number')}"}

    async def _update_scene(self, args: dict) -> dict:
        scene_id = args.pop("scene_id")
        # db.update_scene handles beats array -> JSON conversion
        db.update_scene(scene_id, **args)

        # Sync to Hindsight
        scene = db.get_scene(scene_id)
        if scene:
            scene_summary = self._format_scene_summary(scene)
            await self._sync_to_hindsight(f"Scene updated: {scene_summary}")

        return {"success": True, "message": f"Updated scene ID {scene_id}"}

    async def _delete_scene(self, args: dict) -> dict:
        scene_id = args["scene_id"]
        scene = db.get_scene(scene_id)
        title = scene.get("title", f"Scene {scene.get('scene_number', '?')}") if scene else "Unknown"

        db.delete_scene(scene_id)

        await self._sync_to_hindsight(f"Scene deleted: {title}")

        return {"success": True, "message": f"Deleted scene: {title}"}

    def _format_scene_summary(self, scene: dict) -> str:
        """Format scene info for Hindsight retention."""
        parts = []
        if scene.get("scene_number"):
            parts.append(f"Scene {scene['scene_number']}")
        if scene.get("title"):
            parts.append(f"'{scene['title']}'")
        if scene.get("description"):
            parts.append(f"- {scene['description']}")
        if scene.get("characters"):
            parts.append(f"Characters: {scene['characters']}")
        if scene.get("tone"):
            parts.append(f"Tone: {scene['tone']}")
        if scene.get("beats"):
            beats = scene["beats"]
            if isinstance(beats, str):
                try:
                    beats = json.loads(beats)
                except:
                    pass
            if isinstance(beats, list) and beats:
                parts.append(f"Beats: {', '.join(beats)}")
        return " ".join(parts)
