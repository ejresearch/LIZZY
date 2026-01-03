"""FastAPI server for lizzy_3."""

import io
import os
from pathlib import Path
from typing import Optional

from docx import Document as DocxDocument
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from dotenv import load_dotenv

# Load API key from parent .env
load_dotenv(Path(__file__).parent.parent.parent / ".env")

from .buckets import BucketManager, BucketInfo
from .graph import GraphService, sync_buckets_to_neo4j

# Hindsight memory system
from hindsight import start_server as start_hindsight_server, HindsightClient

app = FastAPI(title="lizzy_3", version="0.1.0")

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize bucket manager
BUCKETS_DIR = Path(__file__).parent.parent / "buckets"
LEGACY_BUCKETS_DIR = Path(__file__).parent.parent.parent / "legacy" / "rag_buckets"
bucket_manager = BucketManager(str(BUCKETS_DIR))

# Initialize graph service (Neo4j)
graph_service = GraphService()

# Initialize Hindsight memory system
print("Starting Hindsight memory server...")
hindsight_server = start_hindsight_server(
    db_url="pg0",  # Embedded PostgreSQL
    llm_provider="openai",
    llm_api_key=os.environ.get("OPENAI_API_KEY", ""),
    llm_model="gpt-4o-mini",
    port=8888,
    log_level="warning"
)
hindsight_client = HindsightClient(base_url=f"http://127.0.0.1:{hindsight_server.port}")
print(f"Hindsight running on port {hindsight_server.port}")

def get_memory_bank_id() -> str:
    """Get the current project's memory bank ID."""
    project = outline_db.get_project()
    if project and project.get('memory_bank_id'):
        return project['memory_bank_id']
    return "lizzy-default"  # Fallback


# --- Pydantic Models ---

class CreateBucketRequest(BaseModel):
    name: str
    description: Optional[str] = ""


class ImportFolderRequest(BaseModel):
    path: str


class ImportLegacyRequest(BaseModel):
    bucket: str  # 'books', 'plays', or 'scripts'


class QueryRequest(BaseModel):
    query: str
    mode: Optional[str] = "hybrid"


class GraphQueryRequest(BaseModel):
    entity: str
    bucket: Optional[str] = None


class GraphPathRequest(BaseModel):
    entity1: str
    entity2: str
    bucket: Optional[str] = None


class CypherQueryRequest(BaseModel):
    query: str
    params: Optional[dict] = None


class ExpertChatRequest(BaseModel):
    message: str
    bucket: str
    system_prompt: str
    rag_mode: Optional[str] = "hybrid"
    history: Optional[list] = []


class ProjectCreateRequest(BaseModel):
    title: Optional[str] = ""
    logline: Optional[str] = ""
    genre: Optional[str] = "Romantic Comedy"
    use_template: Optional[bool] = False


class ProjectUpdateRequest(BaseModel):
    title: Optional[str] = None
    title_locked: Optional[bool] = None
    logline: Optional[str] = None
    logline_locked: Optional[bool] = None
    genre: Optional[str] = None
    description: Optional[str] = None


class WriterNotesUpdateRequest(BaseModel):
    theme: Optional[str] = None
    tone: Optional[str] = None
    comps: Optional[str] = None
    braindump: Optional[str] = None
    outline: Optional[list] = None


class CharacterRequest(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    description: Optional[str] = None
    arc: Optional[str] = None
    age: Optional[str] = None
    personality: Optional[str] = None
    flaw: Optional[str] = None
    backstory: Optional[str] = None
    relationships: Optional[str] = None
    sort_order: Optional[int] = None


class SceneRequest(BaseModel):
    scene_number: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    characters: Optional[str] = None
    tone: Optional[str] = None
    beats: Optional[list] = None
    canvas_content: Optional[str] = None


# --- Bucket Endpoints ---

@app.get("/api/buckets")
async def list_buckets() -> list[dict]:
    """List all buckets with their stats."""
    buckets = bucket_manager.list_buckets()
    return [
        {
            "name": b.name,
            "status": b.status,
            "nodes": b.nodes,
            "edges": b.edges,
            "size": b.size,
            "description": b.description
        }
        for b in buckets
    ]


@app.post("/api/buckets")
async def create_bucket(request: CreateBucketRequest) -> dict:
    """Create a new empty bucket."""
    try:
        info = await bucket_manager.create_bucket(request.name, request.description)
        return {
            "name": info.name,
            "status": info.status,
            "nodes": info.nodes,
            "edges": info.edges,
            "size": info.size
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/buckets/{name}")
async def delete_bucket(name: str) -> dict:
    """Delete a bucket."""
    try:
        await bucket_manager.delete_bucket(name)
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/buckets/{name}/documents")
async def upload_document(name: str, file: UploadFile = File(...), background: bool = True) -> dict:
    """Upload a document to a bucket. Processing runs in background by default."""
    import asyncio

    try:
        content = await file.read()

        # Handle .docx files (binary format)
        if file.filename and file.filename.lower().endswith('.docx'):
            doc = DocxDocument(io.BytesIO(content))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            text = '\n\n'.join(paragraphs)
        else:
            text = content.decode('utf-8', errors='ignore')

        if background:
            # Fire and forget - returns immediately
            asyncio.create_task(bucket_manager.insert_document(name, text, file.filename))
            return {"success": True, "filename": file.filename, "status": "queued"}
        else:
            # Wait for completion
            await bucket_manager.insert_document(name, text, file.filename)
            return {"success": True, "filename": file.filename, "status": "processed"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/buckets/{name}/import-folder")
async def import_folder(name: str, request: ImportFolderRequest) -> dict:
    """Import all documents from a folder."""
    try:
        count = await bucket_manager.insert_from_folder(name, request.path)
        return {"success": True, "documents_imported": count}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/buckets/import-legacy")
async def import_legacy(request: ImportLegacyRequest) -> dict:
    """Import a legacy bucket from the old LIZZY system."""
    bucket_name = request.bucket

    if bucket_name not in ['books', 'plays', 'scripts']:
        raise HTTPException(status_code=400, detail="Invalid bucket name")

    legacy_path = LEGACY_BUCKETS_DIR / bucket_name

    if not legacy_path.exists():
        raise HTTPException(status_code=404, detail=f"Legacy bucket not found at {legacy_path}")

    try:
        info = await bucket_manager.import_legacy_bucket(str(legacy_path), bucket_name)
        return {
            "name": info.name,
            "status": info.status,
            "nodes": info.nodes,
            "edges": info.edges,
            "size": info.size
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/buckets/{name}/query")
async def query_bucket(name: str, request: QueryRequest) -> dict:
    """Query a bucket."""
    try:
        result = await bucket_manager.query(name, request.query, request.mode)
        return {"result": result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/buckets/{name}/documents")
async def list_documents(name: str) -> list[dict]:
    """List all documents in a bucket."""
    try:
        documents = bucket_manager.list_documents(name)
        return documents
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/buckets/{name}/reset-stuck")
async def reset_stuck_documents(name: str) -> dict:
    """Reset stuck processing/pending documents so they can be re-uploaded."""
    try:
        count = bucket_manager.reset_stuck_documents(name)
        return {"success": True, "reset_count": count}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/buckets/{name}/documents/{doc_id}")
async def delete_document(name: str, doc_id: str) -> dict:
    """Delete a document from a bucket."""
    try:
        bucket_manager.delete_document(name, doc_id)
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Health Check ---

@app.get("/api/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {
        "status": "ok",
        "buckets_dir": str(BUCKETS_DIR),
        "legacy_buckets_dir": str(LEGACY_BUCKETS_DIR)
    }


# --- Expert Chat Endpoint ---

# Tools for Syd to edit the outline
OUTLINE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "update_project",
            "description": "Update project metadata (title, logline, genre, description)",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Project title"},
                    "logline": {"type": "string", "description": "One-sentence story summary"},
                    "genre": {"type": "string", "description": "Genre (e.g., Romantic Comedy, Drama)"},
                    "description": {"type": "string", "description": "Longer synopsis"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_character",
            "description": "Create a new character in the story",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Character name"},
                    "role": {"type": "string", "description": "Role (e.g., Protagonist, Love Interest, Best Friend)"},
                    "description": {"type": "string", "description": "Brief character description"},
                    "arc": {"type": "string", "description": "Character arc/journey"},
                    "flaw": {"type": "string", "description": "Character's main flaw"},
                    "personality": {"type": "string", "description": "Personality traits"}
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_character",
            "description": "Update an existing character by ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "character_id": {"type": "integer", "description": "Character ID to update"},
                    "name": {"type": "string"},
                    "role": {"type": "string"},
                    "description": {"type": "string"},
                    "arc": {"type": "string"},
                    "flaw": {"type": "string"},
                    "personality": {"type": "string"}
                },
                "required": ["character_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_scene",
            "description": "Create a new scene in the outline",
            "parameters": {
                "type": "object",
                "properties": {
                    "scene_number": {"type": "integer", "description": "Scene number/position"},
                    "title": {"type": "string", "description": "Scene title or slug line (e.g., INT. COFFEE SHOP - DAY)"},
                    "description": {"type": "string", "description": "What happens in this scene"},
                    "characters": {"type": "string", "description": "Characters in scene (comma-separated)"},
                    "tone": {"type": "string", "description": "Scene tone/mood"}
                },
                "required": ["scene_number", "title"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_scene",
            "description": "Update an existing scene by ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "scene_id": {"type": "integer", "description": "Scene ID to update"},
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "characters": {"type": "string"},
                    "tone": {"type": "string"}
                },
                "required": ["scene_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_outline",
            "description": "Get the current full outline (project, characters, scenes) to see what exists",
            "parameters": {"type": "object", "properties": {}}
        }
    }
]


def execute_outline_tool(name: str, args: dict) -> dict:
    """Execute an outline tool and return the result."""
    import json

    try:
        if name == "update_project":
            return outline_db.update_project(**args)

        elif name == "create_character":
            return outline_db.create_character(**args)

        elif name == "update_character":
            char_id = args.pop("character_id")
            result = outline_db.update_character(char_id, **args)
            return result or {"error": "Character not found"}

        elif name == "create_scene":
            scene_num = args.pop("scene_number")
            return outline_db.create_scene(scene_num, **args)

        elif name == "update_scene":
            scene_id = args.pop("scene_id")
            result = outline_db.update_scene(scene_id, **args)
            return result or {"error": "Scene not found"}

        elif name == "get_outline":
            return {
                "project": outline_db.get_project(),
                "characters": outline_db.get_characters(),
                "scenes": outline_db.get_scenes()
            }

        else:
            return {"error": f"Unknown tool: {name}"}

    except Exception as e:
        return {"error": str(e)}


@app.post("/api/expert/chat")
async def expert_chat(request: ExpertChatRequest) -> dict:
    """
    Chat with Syd using LLM + Tools + RAG + Memory.

    Syd can now use tools to edit the project outline (characters, scenes, etc.)
    """
    import json
    from openai import AsyncOpenAI

    client = AsyncOpenAI()

    # Step 1: Recall memories from Hindsight
    memory_context = ""
    bank_id = get_memory_bank_id()
    try:
        memories = await hindsight_client.arecall(
            bank_id=bank_id,
            query=request.message,
            max_tokens=2000,
            budget="mid"
        )
        if memories:
            memory_parts = [m.text for m in memories[:5]]
            memory_context = "\n".join(memory_parts)
    except Exception as e:
        print(f"Hindsight recall failed: {e}")

    # Step 2: Query bucket for relevant context (RAG)
    try:
        context = await bucket_manager.query(
            request.bucket,
            request.message,
            request.rag_mode
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        context = ""

    # Step 2.5: Get current outline state from SQLite
    outline_context = ""
    try:
        project = outline_db.get_project()
        characters = outline_db.get_characters()
        scenes = outline_db.get_scenes()

        outline_parts = []
        if project and (project.get('title') or project.get('logline')):
            outline_parts.append(f"Project: {project.get('title', 'Untitled')} - {project.get('logline', '')}")

        if characters:
            char_list = [f"- [id={c['id']}] {c['name'] or 'Unnamed'} ({c['role'] or 'no role'}): {c.get('description', '')[:50]}" for c in characters[:10]]
            outline_parts.append(f"Characters:\n" + "\n".join(char_list))

        if scenes:
            scene_list = [f"- [id={s['id']}] {s['scene_number']}. {s['title']}: {s.get('description', '')[:40]}" for s in scenes if s.get('title')]
            if scene_list:
                outline_parts.append(f"Scenes ({len(scenes)} total):\n" + "\n".join(scene_list[:15]))
                if len(scenes) > 15:
                    outline_parts.append(f"  ... and {len(scenes) - 15} more scenes")

        if outline_parts:
            outline_context = "\n\n".join(outline_parts)
    except Exception as e:
        print(f"Outline fetch failed: {e}")

    # Step 3: Build messages for LLM
    messages = []

    # System prompt with tool instructions
    system_content = request.system_prompt
    system_content += """

You have tools to edit the project outline. Use them when the writer asks you to:
- Create or update characters
- Create or update scenes
- Set the project title, logline, or description

When making changes, use the tools. After using tools, summarize what you did.
If you need to see what exists, use get_outline first.
Character and scene IDs are shown in brackets like [id=5]."""

    if outline_context:
        system_content += f"\n\n---\nCurrent project outline:\n{outline_context}"

    if memory_context:
        system_content += f"\n\n---\nWhat you remember about this project:\n{memory_context}"

    if context:
        system_content += f"\n\n---\nRelevant knowledge from your expertise:\n{context[:3000]}"

    messages.append({"role": "system", "content": system_content})

    # Add conversation history
    for msg in request.history[-10:]:
        if isinstance(msg, dict) and "role" in msg and "content" in msg:
            messages.append({"role": msg["role"], "content": msg["content"]})

    # Add current user message
    messages.append({"role": "user", "content": request.message})

    # Step 4: Call LLM with tools (loop for tool use)
    tools_used = []
    max_iterations = 5

    try:
        for _ in range(max_iterations):
            response = await client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=OUTLINE_TOOLS,
                tool_choice="auto",
                temperature=0.7,
                max_tokens=1500
            )

            assistant_msg = response.choices[0].message

            # Check if we need to execute tools
            if assistant_msg.tool_calls:
                # Add assistant message with tool calls
                messages.append(assistant_msg)

                # Execute each tool call
                for tool_call in assistant_msg.tool_calls:
                    func_name = tool_call.function.name
                    func_args = json.loads(tool_call.function.arguments)

                    print(f"Syd using tool: {func_name}({func_args})")
                    result = execute_outline_tool(func_name, func_args)
                    tools_used.append({"tool": func_name, "args": func_args, "result": result})

                    # Add tool result to messages
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result)
                    })

                # Continue loop to get final response
                continue

            # No tool calls - we have the final response
            assistant_message = assistant_msg.content or ""
            break
        else:
            assistant_message = "I made several changes but ran into a loop. Please check the outline."

        # Step 5: Retain conversation turn to Hindsight
        try:
            await hindsight_client.aretain(
                bank_id=bank_id,
                content=f"User said: {request.message}",
                context="conversation with writer"
            )
            # Include tool use in memory
            if tools_used:
                tool_summary = ", ".join([t["tool"] for t in tools_used])
                await hindsight_client.aretain(
                    bank_id=bank_id,
                    content=f"Syd used tools ({tool_summary}) and responded: {assistant_message[:400]}",
                    context="conversation with writer"
                )
            else:
                await hindsight_client.aretain(
                    bank_id=bank_id,
                    content=f"Syd responded: {assistant_message[:500]}",
                    context="conversation with writer"
                )
        except Exception as e:
            print(f"Hindsight retain failed: {e}")

        return {
            "response": assistant_message,
            "tools_used": tools_used if tools_used else None,
            "context_used": f"{len(context)} chars from RAG" if context else None,
            "memory_used": f"{len(memory_context)} chars from memory" if memory_context else None,
            "model": "gpt-4o"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM error: {str(e)}")


# --- Outline Endpoints (SQLite) ---

from .database import db as outline_db


async def sync_to_memory(content: str):
    """Helper to sync outline changes to Hindsight memory."""
    try:
        await hindsight_client.aretain(
            bank_id=get_memory_bank_id(),
            content=content,
            context="outline update"
        )
    except Exception as e:
        print(f"Memory sync failed: {e}")


@app.get("/api/outline/project")
async def get_project() -> dict:
    """Get project metadata."""
    return outline_db.get_project()


@app.post("/api/outline/project")
async def create_project(request: ProjectCreateRequest) -> dict:
    """Create a new project, optionally with 30-scene + 5-character template."""
    if request.use_template:
        result = outline_db.initialize_project_with_template(
            title=request.title or "",
            logline=request.logline or "",
            genre=request.genre or "Romantic Comedy"
        )
        return result
    else:
        return outline_db.update_project(
            title=request.title or "",
            logline=request.logline or "",
            genre=request.genre or "Romantic Comedy"
        )


@app.put("/api/outline/project")
async def update_project(request: ProjectUpdateRequest) -> dict:
    """Update project metadata."""
    result = outline_db.update_project(**request.model_dump(exclude_none=True))
    # Sync to memory
    parts = []
    if request.title:
        parts.append(f"Project title: {request.title}")
    if request.logline:
        parts.append(f"Logline: {request.logline}")
    if parts:
        await sync_to_memory(" | ".join(parts))
    return result


@app.delete("/api/outline/project")
async def delete_project() -> dict:
    """Delete entire project (all data).

    Note: The old Hindsight memory bank is orphaned (not deleted).
    Each new project gets a fresh bank ID, so old memories won't interfere.
    """
    old_bank_id = outline_db.reset_project()
    if old_bank_id:
        print(f"Project deleted. Orphaned memory bank: {old_bank_id}")
    return {"success": True, "orphaned_memory_bank": old_bank_id}


@app.get("/api/outline/notes")
async def get_writer_notes() -> dict:
    """Get writer notes."""
    return outline_db.get_writer_notes()


@app.put("/api/outline/notes")
async def update_writer_notes(request: WriterNotesUpdateRequest) -> dict:
    """Update writer notes."""
    return outline_db.update_writer_notes(**request.model_dump(exclude_none=True))


@app.get("/api/outline/characters")
async def get_characters() -> list:
    """Get all characters."""
    return outline_db.get_characters()


@app.post("/api/outline/characters")
async def create_character(request: CharacterRequest) -> dict:
    """Create a new character."""
    result = outline_db.create_character(**request.model_dump(exclude_none=True))
    # Sync to memory
    parts = [f"Character: {request.name}"]
    if request.role:
        parts.append(f"role={request.role}")
    if request.description:
        parts.append(request.description)
    if request.flaw:
        parts.append(f"flaw: {request.flaw}")
    await sync_to_memory(" | ".join(parts))
    return result


@app.get("/api/outline/characters/{character_id}")
async def get_character(character_id: int) -> dict:
    """Get a single character."""
    char = outline_db.get_character(character_id)
    if not char:
        raise HTTPException(status_code=404, detail="Character not found")
    return char


@app.put("/api/outline/characters/{character_id}")
async def update_character(character_id: int, request: CharacterRequest) -> dict:
    """Update a character."""
    char = outline_db.update_character(character_id, **request.model_dump(exclude_none=True))
    if not char:
        raise HTTPException(status_code=404, detail="Character not found")
    # Sync to memory
    parts = [f"Character updated: {char.get('name', 'Unknown')}"]
    if request.arc:
        parts.append(f"arc: {request.arc}")
    if request.description:
        parts.append(request.description)
    await sync_to_memory(" | ".join(parts))
    return char


@app.delete("/api/outline/characters/{character_id}")
async def delete_character(character_id: int) -> dict:
    """Delete a character."""
    if outline_db.delete_character(character_id):
        return {"success": True}
    raise HTTPException(status_code=404, detail="Character not found")


@app.get("/api/outline/scenes")
async def get_scenes() -> list:
    """Get all scenes."""
    return outline_db.get_scenes()


@app.post("/api/outline/scenes")
async def create_scene(request: SceneRequest) -> dict:
    """Create a new scene."""
    if request.scene_number is None:
        raise HTTPException(status_code=400, detail="scene_number is required")
    result = outline_db.create_scene(request.scene_number, **request.model_dump(exclude={'scene_number'}, exclude_none=True))
    # Sync to memory
    parts = [f"Scene {request.scene_number}"]
    if request.title:
        parts.append(request.title)
    if request.description:
        parts.append(request.description)
    await sync_to_memory(" | ".join(parts))
    return result


@app.get("/api/outline/scenes/{scene_id}")
async def get_scene(scene_id: int) -> dict:
    """Get a single scene."""
    scene = outline_db.get_scene(scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
    return scene


@app.put("/api/outline/scenes/{scene_id}")
async def update_scene(scene_id: int, request: SceneRequest) -> dict:
    """Update a scene."""
    scene = outline_db.update_scene(scene_id, **request.model_dump(exclude_none=True))
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
    # Sync to memory (only significant updates, not canvas content)
    if request.title or request.description:
        parts = [f"Scene {scene.get('scene_number', '?')} updated"]
        if request.title:
            parts.append(request.title)
        if request.description:
            parts.append(request.description[:200])
        await sync_to_memory(" | ".join(parts))
    return scene


@app.delete("/api/outline/scenes/{scene_id}")
async def delete_scene(scene_id: int) -> dict:
    """Delete a scene."""
    if outline_db.delete_scene(scene_id):
        return {"success": True}
    raise HTTPException(status_code=404, detail="Scene not found")


class SceneReorderRequest(BaseModel):
    new_scene_number: int


@app.put("/api/outline/scenes/{scene_id}/reorder")
async def reorder_scene(scene_id: int, request: SceneReorderRequest) -> dict:
    """Reorder a scene to a new position."""
    scene = outline_db.reorder_scene(scene_id, request.new_scene_number)
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
    return scene


@app.get("/api/outline")
async def get_full_outline() -> dict:
    """Get the complete outline (project + notes + characters + scenes)."""
    return {
        "project": outline_db.get_project(),
        "notes": outline_db.get_writer_notes(),
        "characters": outline_db.get_characters(),
        "scenes": outline_db.get_scenes()
    }


# --- Conversation Endpoints ---

class ConversationRequest(BaseModel):
    title: Optional[str] = None
    messages: Optional[list] = None


@app.get("/api/conversations")
async def list_conversations() -> list:
    """List all conversations (without messages)."""
    return outline_db.get_conversations()


@app.post("/api/conversations")
async def create_conversation(request: ConversationRequest) -> dict:
    """Create a new conversation."""
    return outline_db.create_conversation(
        title=request.title or "New Chat",
        messages=request.messages or []
    )


@app.get("/api/conversations/{conversation_id}")
async def get_conversation(conversation_id: int) -> dict:
    """Get a conversation with messages."""
    conv = outline_db.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@app.put("/api/conversations/{conversation_id}")
async def update_conversation(conversation_id: int, request: ConversationRequest) -> dict:
    """Update a conversation (title and/or messages)."""
    conv = outline_db.update_conversation(
        conversation_id,
        title=request.title,
        messages=request.messages
    )
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: int) -> dict:
    """Delete a conversation."""
    if outline_db.delete_conversation(conversation_id):
        return {"success": True}
    raise HTTPException(status_code=404, detail="Conversation not found")


# --- Graph Endpoints (Neo4j) ---

@app.post("/api/graph/sync")
async def sync_graphs_to_neo4j() -> dict:
    """Sync all bucket graphs to Neo4j."""
    try:
        results = await sync_buckets_to_neo4j(str(BUCKETS_DIR), graph_service)
        return {"success": True, "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/graph/sync/{bucket_name}")
async def sync_bucket_to_neo4j(bucket_name: str) -> dict:
    """Sync a single bucket's graph to Neo4j."""
    bucket_path = BUCKETS_DIR / bucket_name
    graphml_file = bucket_path / "graph_chunk_entity_relation.graphml"

    if not graphml_file.exists():
        raise HTTPException(status_code=404, detail=f"No graph found for bucket '{bucket_name}'")

    try:
        safe_name = bucket_name.replace("-", "_")
        stats = graph_service.import_graphml(str(graphml_file), safe_name)
        return {"success": True, "bucket": bucket_name, **stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/graph/entity")
async def query_entity(request: GraphQueryRequest) -> dict:
    """Get entity info and relationships from Neo4j."""
    try:
        result = graph_service.query_entity(request.entity, request.bucket)
        if not result:
            raise HTTPException(status_code=404, detail=f"Entity '{request.entity}' not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/graph/path")
async def query_path(request: GraphPathRequest) -> dict:
    """Find shortest path between two entities."""
    try:
        path = graph_service.query_path(request.entity1, request.entity2, request.bucket)
        return {"path": path, "length": len(path) - 1 if path else 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/graph/neighbors")
async def query_neighbors(request: GraphQueryRequest) -> dict:
    """Get neighborhood around an entity."""
    try:
        neighbors = graph_service.query_neighbors(request.entity, depth=2, bucket=request.bucket)
        return {"entity": request.entity, "neighbors": neighbors}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/graph/types/{bucket_name}")
async def get_entity_types(bucket_name: str) -> dict:
    """Get all entity types in a bucket."""
    try:
        safe_name = bucket_name.replace("-", "_")
        stats = graph_service.get_graph_stats(safe_name)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/graph/data/{bucket_name}")
async def get_graph_data(bucket_name: str, limit: int = 200) -> dict:
    """Get graph nodes and edges for visualization (from local GraphML)."""
    import networkx as nx

    bucket_path = BUCKETS_DIR / bucket_name
    graphml_file = bucket_path / "graph_chunk_entity_relation.graphml"

    if not graphml_file.exists():
        raise HTTPException(status_code=404, detail=f"No graph found for bucket '{bucket_name}'")

    try:
        G = nx.read_graphml(str(graphml_file))

        # Get top nodes by degree (most connected)
        degrees = dict(G.degree())
        top_nodes = sorted(degrees.keys(), key=lambda x: degrees[x], reverse=True)[:limit]

        nodes = []
        for node_id in top_nodes:
            attrs = G.nodes[node_id]
            nodes.append({
                "id": node_id,
                "label": node_id[:30],
                "type": attrs.get("entity_type", "unknown"),
                "description": attrs.get("description", "")[:200],
                "connections": degrees[node_id]
            })

        # Get edges between top nodes
        top_set = set(top_nodes)
        edges = []
        for source, target, attrs in G.edges(data=True):
            if source in top_set and target in top_set:
                edges.append({
                    "from": source,
                    "to": target,
                    "label": attrs.get("keywords", "")[:20] if attrs.get("keywords") else "",
                    "weight": float(attrs.get("weight", 1))
                })

        return {
            "nodes": nodes,
            "edges": edges,
            "total_nodes": G.number_of_nodes(),
            "total_edges": G.number_of_edges()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/graph/entities/{bucket_name}/{entity_type}")
async def get_entities_by_type(bucket_name: str, entity_type: str, limit: int = 50) -> dict:
    """Get all entities of a specific type."""
    try:
        safe_name = bucket_name.replace("-", "_")
        entities = graph_service.search_by_type(entity_type, safe_name, limit)
        return {"type": entity_type, "entities": entities}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/graph/cypher")
async def run_cypher(request: CypherQueryRequest) -> dict:
    """Execute a raw Cypher query (advanced users)."""
    try:
        results = graph_service.cypher_query(request.query, request.params)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Mount static files for frontend
frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
