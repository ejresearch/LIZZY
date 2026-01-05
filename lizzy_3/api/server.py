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

def get_memory_bank_id(project_id: int) -> str:
    """Get a project's memory bank ID."""
    project = outline_db.get_project(project_id)
    if project and project.get('memory_bank_id'):
        return project['memory_bank_id']
    return f"lizzy-project-{project_id}"  # Fallback per project


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
    project_id: int  # Required: which project context to use
    buckets: Optional[list] = []  # List of active buckets to query
    bucket: Optional[str] = None  # Legacy single bucket (fallback)
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
    phase: Optional[str] = None  # intake, brainstorm, write


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
    act_id: Optional[int] = None


class ActRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    sort_order: Optional[int] = None


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
    },
    {
        "type": "function",
        "function": {
            "name": "write_scene",
            "description": "Write a full scene as formatted screenplay. Use when asked to 'write', 'draft', or 'flesh out' a scene. The system will use your conversation as context (the 'blueprint') and generate proper screenplay format to the Canvas. Just provide the scene_id - the backend handles the rest.",
            "parameters": {
                "type": "object",
                "properties": {
                    "scene_id": {
                        "type": "integer",
                        "description": "ID of the scene to write (use get_outline to find scene IDs)"
                    }
                },
                "required": ["scene_id"]
            }
        }
    }
]


# =============================================================================
# SCENE WRITING ENGINE
# =============================================================================


def parse_screenplay_to_elements(raw_text: str) -> list:
    """
    Parse raw screenplay prose into structured elements.

    Returns list of {type, text} dicts for Canvas display.
    """
    import re

    elements = []
    lines = raw_text.strip().split('\n')

    i = 0
    while i < len(lines):
        line = lines[i].rstrip()

        # Skip empty lines
        if not line.strip():
            i += 1
            continue

        # Scene heading: INT./EXT. LOCATION - TIME
        if re.match(r'^(INT\.|EXT\.|INT/EXT\.|I/E\.)', line.strip(), re.IGNORECASE):
            elements.append({"type": "scene-heading", "text": line.strip()})
            i += 1
            continue

        # Transition: CUT TO:, FADE IN:, FADE OUT, DISSOLVE TO:, etc.
        if re.match(r'^(CUT TO:|FADE IN:|FADE OUT|DISSOLVE TO:|SMASH CUT:|MATCH CUT:|JUMP CUT:)', line.strip(), re.IGNORECASE):
            elements.append({"type": "transition", "text": line.strip()})
            i += 1
            continue

        # Character name: ALL CAPS, possibly centered, before dialogue
        # Look ahead to see if next non-empty line is dialogue
        stripped = line.strip()
        if stripped.isupper() and len(stripped) < 40 and not stripped.startswith('INT') and not stripped.startswith('EXT'):
            # Check if this looks like a character name (not a transition or heading)
            if not re.match(r'.*(TO:|IN:|OUT)$', stripped):
                elements.append({"type": "character", "text": stripped})
                i += 1

                # Look for parenthetical and/or dialogue
                while i < len(lines):
                    next_line = lines[i].rstrip()
                    if not next_line.strip():
                        i += 1
                        break

                    # Parenthetical: (text in parentheses)
                    paren_match = re.match(r'^\s*\(([^)]+)\)\s*$', next_line)
                    if paren_match:
                        elements.append({"type": "parenthetical", "text": f"({paren_match.group(1)})"})
                        i += 1
                        continue

                    # If next line is also all caps, it's a new character - stop
                    if next_line.strip().isupper() and len(next_line.strip()) < 40:
                        break

                    # If next line starts with INT/EXT, it's a new scene - stop
                    if re.match(r'^(INT\.|EXT\.)', next_line.strip(), re.IGNORECASE):
                        break

                    # Otherwise it's dialogue
                    elements.append({"type": "dialogue", "text": next_line.strip()})
                    i += 1

                continue

        # Default: action line
        elements.append({"type": "action", "text": line.strip()})
        i += 1

    return elements


async def generate_scene_prose(
    scene_id: int,
    project_id: int,
    conversation_history: list,
    target_words: int = 800
) -> tuple[str, list]:
    """
    Generate screenplay prose for a scene using conversation as blueprint.

    Args:
        scene_id: The scene to write
        project_id: The project context
        conversation_history: Recent conversation (the "blueprint")
        target_words: Target word count (700-900)

    Returns:
        tuple of (raw_prose, parsed_elements)
    """
    from openai import AsyncOpenAI

    client = AsyncOpenAI()

    # Get scene details
    scene = outline_db.get_scene(scene_id)
    if not scene:
        return "", []

    # Get characters for reference
    characters = outline_db.get_characters(project_id)
    char_summary = ", ".join([f"{c['name']} ({c.get('role', 'unknown')})" for c in characters[:5]]) if characters else "No characters defined"

    # Get previous scene for continuity
    all_scenes = outline_db.get_scenes(project_id)
    scene_index = next((i for i, s in enumerate(all_scenes) if s['id'] == scene_id), -1)

    previous_content = ""
    if scene_index > 0:
        prev_scene = all_scenes[scene_index - 1]
        if prev_scene.get('canvas_content'):
            try:
                prev_elements = json.loads(prev_scene['canvas_content'])
                # Extract first 300 chars of text
                prev_text = " ".join([e.get('text', '') for e in prev_elements[:10]])
                previous_content = prev_text[:300] + "..." if len(prev_text) > 300 else prev_text
            except:
                pass

    # Get next scene outline for foreshadowing
    next_outline = ""
    if scene_index >= 0 and scene_index < len(all_scenes) - 1:
        next_scene = all_scenes[scene_index + 1]
        next_outline = next_scene.get('description', '') or next_scene.get('title', '')

    # Build blueprint from conversation history (last 10 messages)
    blueprint_parts = []
    for msg in conversation_history[-10:]:
        if isinstance(msg, dict) and msg.get('content'):
            role = "Writer" if msg.get('role') == 'user' else "Syd"
            blueprint_parts.append(f"{role}: {msg['content'][:500]}")
    blueprint = "\n".join(blueprint_parts) if blueprint_parts else "No conversation context available."

    # Build the prompt (like legacy write.py)
    prompt = f"""**SCENE {scene.get('scene_number', '?')}: {scene.get('title', 'Untitled')}**

Description: {scene.get('description', 'No description')}
Characters in scene: {scene.get('characters', char_summary)}
Tone: {scene.get('tone', 'romantic comedy')}

**BLUEPRINT FROM CONVERSATION:**
{blueprint}

"""

    # Add beats if available
    if scene.get('beats'):
        try:
            beats = json.loads(scene['beats']) if isinstance(scene['beats'], str) else scene['beats']
            if beats:
                prompt += f"**KEY BEATS:**\n" + "\n".join([f"• {b}" for b in beats]) + "\n\n"
        except:
            pass

    # Add continuity context
    if previous_content:
        prompt += f"""**PREVIOUS SCENE (for continuity):**
{previous_content}

"""

    if next_outline:
        prompt += f"""**NEXT SCENE (to foreshadow):**
{next_outline}

"""

    # Instructions
    prompt += f"""**YOUR TASK:**
Write this scene in PROPER SCREENPLAY FORMAT following industry standards.

TARGET: {target_words} words / 2-3 pages (1 page ≈ 1 minute of screen time)

SCREENPLAY FORMAT REQUIREMENTS:
1. Scene heading: INT./EXT. LOCATION - TIME (all caps)
2. Action lines: Present tense, active voice, visual descriptions
3. Character names: ALL CAPS before dialogue
4. Dialogue: Natural, character-specific, advances plot
5. Parentheticals: (brief acting directions) - use sparingly
6. Transitions: CUT TO:, DISSOLVE TO: (only when needed)

CONTENT REQUIREMENTS:
1. Show character emotions through actions, NOT exposition
2. Make dialogue witty, natural, and character-specific
3. Build romantic/comedic tension
4. Maintain continuity with previous scene
5. Include specific visual details and character reactions

Write the complete scene now in proper screenplay format:"""

    # Call GPT-4o
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a screenwriter."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.8,
        max_tokens=2500
    )

    raw_prose = response.choices[0].message.content or ""

    # Parse into elements
    elements = parse_screenplay_to_elements(raw_prose)

    return raw_prose, elements


def execute_outline_tool(name: str, args: dict, project_id: int) -> dict:
    """Execute an outline tool and return the result."""
    import json

    try:
        if name == "update_project":
            return outline_db.update_project(project_id, **args)

        elif name == "create_character":
            return outline_db.create_character(project_id, **args)

        elif name == "update_character":
            char_id = args.pop("character_id")
            result = outline_db.update_character(char_id, **args)
            return result or {"error": "Character not found"}

        elif name == "create_scene":
            scene_num = args.pop("scene_number")
            return outline_db.create_scene(project_id, scene_num, **args)

        elif name == "update_scene":
            scene_id = args.pop("scene_id")
            result = outline_db.update_scene(scene_id, **args)
            return result or {"error": "Scene not found"}

        elif name == "write_scene":
            scene_id = args.pop("scene_id")
            elements = args.get("elements", [])
            # Store as JSON in canvas_content
            canvas_content = json.dumps(elements)
            result = outline_db.update_scene(scene_id, canvas_content=canvas_content)
            if result:
                return {"success": True, "scene_id": scene_id, "elements_count": len(elements)}
            return {"error": "Scene not found"}

        elif name == "get_outline":
            return {
                "project": outline_db.get_project(project_id),
                "characters": outline_db.get_characters(project_id),
                "scenes": outline_db.get_scenes(project_id)
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
    import asyncio
    from openai import AsyncOpenAI

    client = AsyncOpenAI()
    project_id = request.project_id
    bank_id = get_memory_bank_id(project_id)

    # === PARALLEL CONTEXT GATHERING ===
    # Run memory recall, bucket queries, and outline fetch concurrently

    async def recall_memories():
        try:
            memories = await hindsight_client.arecall(
                bank_id=bank_id,
                query=request.message,
                max_tokens=1500,
                budget="low"  # faster
            )
            if memories:
                return "\n".join([m.text for m in memories[:3]])
        except Exception as e:
            print(f"Hindsight recall failed: {e}")
        return ""

    async def query_bucket(bucket_name: str):
        try:
            result = await bucket_manager.query(bucket_name, request.message, request.rag_mode)
            if result:
                label = {'books-final': 'Structure', 'plays-final': 'Dialogue', 'scripts-final': 'Execution'}.get(bucket_name, bucket_name)
                return f"[{label}]\n{result}"
        except Exception as e:
            print(f"Bucket {bucket_name} query failed: {e}")
        return ""

    def get_outline_context():
        try:
            project = outline_db.get_project(project_id)
            characters = outline_db.get_characters(project_id)
            scenes = outline_db.get_scenes(project_id)

            parts = []
            if project and (project.get('title') or project.get('logline')):
                parts.append(f"Project: {project.get('title', 'Untitled')} - {project.get('logline', '')}")
            if characters:
                char_list = [f"- [id={c['id']}] {c['name'] or 'Unnamed'} ({c['role'] or 'no role'})" for c in characters[:8]]
                parts.append(f"Characters:\n" + "\n".join(char_list))
            if scenes:
                scene_list = [f"- [id={s['id']}] {s['scene_number']}. {s['title']}" for s in scenes if s.get('title')][:12]
                if scene_list:
                    parts.append(f"Scenes:\n" + "\n".join(scene_list))
            return "\n\n".join(parts) if parts else ""
        except Exception as e:
            print(f"Outline fetch failed: {e}")
            return ""

    # Build list of parallel tasks
    buckets_to_query = request.buckets if request.buckets else ([request.bucket] if request.bucket else [])

    tasks = [recall_memories()]
    tasks.extend([query_bucket(b) for b in buckets_to_query])

    # Run outline fetch in thread (it's sync SQLite)
    outline_context = await asyncio.get_event_loop().run_in_executor(None, get_outline_context)

    # Gather async tasks in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Parse results
    memory_context = results[0] if isinstance(results[0], str) else ""
    context_parts = [r for r in results[1:] if isinstance(r, str) and r]
    context = "\n\n".join(context_parts) if context_parts else ""

    # Step 3: Build messages for LLM
    messages = []

    # System prompt with tool instructions
    system_content = request.system_prompt
    system_content += """

You have tools to edit the project outline and write scenes. Use them when the writer asks you to:
- Create or update characters
- Create or update scenes (metadata like title, description, beats)
- Set the project title, logline, or description
- WRITE actual screenplay content using write_scene

WRITING SCENES with write_scene:
When asked to "write", "draft", or "flesh out" a scene, just call write_scene(scene_id).
The system will use your conversation as the "blueprint" and automatically:
- Pull scene metadata (title, description, characters, tone, beats)
- Use conversation context to understand what you discussed
- Add continuity from previous scene
- Generate proper screenplay format (700-900 words)
- Save to Canvas

Just provide the scene_id - the backend handles everything else!
Example: write_scene(scene_id=5)

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
                model="gpt-4o-mini",  # Faster for chat; write_scene uses gpt-4o
                messages=messages,
                tools=OUTLINE_TOOLS,
                tool_choice="auto",
                temperature=0.7,
                max_tokens=1000
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

                    # Special handling for write_scene - needs conversation context
                    if func_name == "write_scene":
                        scene_id = func_args.get("scene_id")
                        if scene_id:
                            raw_prose, elements = await generate_scene_prose(
                                scene_id=scene_id,
                                project_id=project_id,
                                conversation_history=request.history
                            )
                            if elements:
                                # Store in database
                                canvas_content = json.dumps(elements)
                                outline_db.update_scene(scene_id, canvas_content=canvas_content)
                                result = {
                                    "success": True,
                                    "scene_id": scene_id,
                                    "elements_count": len(elements),
                                    "word_count": len(raw_prose.split()),
                                    "preview": raw_prose[:200] + "..." if len(raw_prose) > 200 else raw_prose
                                }
                            else:
                                result = {"error": "Failed to generate scene prose"}
                        else:
                            result = {"error": "scene_id is required"}
                    else:
                        result = execute_outline_tool(func_name, func_args, project_id)

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

        # Step 5: Retain conversation turn to Hindsight (fire-and-forget for speed)
        async def retain_memory():
            try:
                await hindsight_client.aretain(
                    bank_id=bank_id,
                    content=f"User: {request.message[:200]} | Syd: {assistant_message[:300]}",
                    context="conversation"
                )
            except Exception as e:
                print(f"Hindsight retain failed: {e}")

        asyncio.create_task(retain_memory())  # Don't wait

        return {
            "response": assistant_message,
            "tools_used": tools_used if tools_used else None,
            "context_used": f"{len(context)} chars from RAG" if context else None,
            "memory_used": f"{len(memory_context)} chars from memory" if memory_context else None,
            "model": "gpt-4o-mini"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM error: {str(e)}")


@app.post("/api/reflect")
async def trigger_reflection() -> dict:
    """
    Trigger Hindsight reflection at end of session.

    Analyzes memories to form new connections, opinions, and observations
    about the project and user preferences.
    """
    bank_id = get_memory_bank_id()
    try:
        await hindsight_client.areflect(bank_id=bank_id)
        print(f"Reflection completed for bank: {bank_id}")
        return {"success": True, "bank_id": bank_id}
    except Exception as e:
        print(f"Reflection failed: {e}")
        return {"success": False, "error": str(e)}


# --- Outline Endpoints (SQLite) ---

from .database import db as outline_db


async def sync_to_memory(project_id: int, content: str):
    """Helper to sync outline changes to Hindsight memory."""
    try:
        await hindsight_client.aretain(
            bank_id=get_memory_bank_id(project_id),
            content=content,
            context="outline update"
        )
    except Exception as e:
        print(f"Memory sync failed: {e}")


# =============================================================================
# PROJECT ENDPOINTS (Multi-project support)
# =============================================================================

@app.get("/api/projects")
async def list_projects() -> list:
    """List all projects."""
    return outline_db.list_projects()


@app.post("/api/projects")
async def create_project(request: ProjectCreateRequest) -> dict:
    """Create a new project, optionally with 30-scene + 5-character template."""
    return outline_db.create_project(
        title=request.title or "",
        logline=request.logline or "",
        genre=request.genre or "Romantic Comedy",
        use_template=request.use_template or False
    )


@app.get("/api/projects/{project_id}")
async def get_project(project_id: int) -> dict:
    """Get a single project."""
    project = outline_db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@app.put("/api/projects/{project_id}")
async def update_project(project_id: int, request: ProjectUpdateRequest) -> dict:
    """Update project metadata."""
    result = outline_db.update_project(project_id, **request.model_dump(exclude_none=True))
    if not result:
        raise HTTPException(status_code=404, detail="Project not found")
    return result


@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: int) -> dict:
    """Delete a project and all its data, including Hindsight memory bank."""
    import httpx

    old_bank_id = outline_db.delete_project(project_id)
    if old_bank_id is None:
        raise HTTPException(status_code=404, detail="Project not found")

    # Delete the Hindsight memory bank
    memory_deleted = False
    if old_bank_id:
        try:
            async with httpx.AsyncClient() as client:
                res = await client.delete(
                    f"http://127.0.0.1:{hindsight_server.port}/v1/default/banks/{old_bank_id}"
                )
                memory_deleted = res.status_code in (200, 204, 404)  # 404 = already gone
        except Exception as e:
            print(f"Failed to delete memory bank {old_bank_id}: {e}")

    return {"success": True, "memory_bank_deleted": memory_deleted}


# =============================================================================
# OUTLINE ENDPOINTS (require project_id query param)
# =============================================================================

@app.get("/api/outline/notes")
async def get_writer_notes(project_id: int) -> dict:
    """Get writer notes for a project."""
    return outline_db.get_writer_notes(project_id) or {}


@app.put("/api/outline/notes")
async def update_writer_notes(project_id: int, request: WriterNotesUpdateRequest) -> dict:
    """Update writer notes for a project."""
    return outline_db.update_writer_notes(project_id, **request.model_dump(exclude_none=True)) or {}


@app.get("/api/outline/characters")
async def get_characters(project_id: int) -> list:
    """Get all characters for a project."""
    return outline_db.get_characters(project_id)


@app.post("/api/outline/characters")
async def create_character(project_id: int, request: CharacterRequest) -> dict:
    """Create a new character in a project."""
    result = outline_db.create_character(project_id, **request.model_dump(exclude_none=True))
    # Sync to memory
    parts = [f"Character: {request.name}"]
    if request.role:
        parts.append(f"role={request.role}")
    if request.description:
        parts.append(request.description)
    await sync_to_memory(project_id, " | ".join(parts))
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
    return char


@app.delete("/api/outline/characters/{character_id}")
async def delete_character(character_id: int) -> dict:
    """Delete a character."""
    if outline_db.delete_character(character_id):
        return {"success": True}
    raise HTTPException(status_code=404, detail="Character not found")


@app.get("/api/outline/acts")
async def get_acts(project_id: int) -> list:
    """Get all acts for a project."""
    return outline_db.get_acts(project_id)


@app.post("/api/outline/acts")
async def create_act(project_id: int, request: ActRequest) -> dict:
    """Create a new act in a project."""
    title = request.title or "New Act"
    return outline_db.create_act(
        project_id,
        title=title,
        description=request.description or "",
        sort_order=request.sort_order
    )


@app.get("/api/outline/acts/{act_id}")
async def get_act(act_id: int) -> dict:
    """Get a single act."""
    act = outline_db.get_act(act_id)
    if not act:
        raise HTTPException(status_code=404, detail="Act not found")
    return act


@app.put("/api/outline/acts/{act_id}")
async def update_act(act_id: int, request: ActRequest) -> dict:
    """Update an act."""
    act = outline_db.update_act(act_id, **request.model_dump(exclude_none=True))
    if not act:
        raise HTTPException(status_code=404, detail="Act not found")
    return act


@app.delete("/api/outline/acts/{act_id}")
async def delete_act(act_id: int) -> dict:
    """Delete an act. Scenes will become unassigned."""
    if outline_db.delete_act(act_id):
        return {"success": True}
    raise HTTPException(status_code=404, detail="Act not found")


@app.get("/api/outline/acts/{act_id}/scenes")
async def get_scenes_by_act(project_id: int, act_id: int) -> list:
    """Get all scenes in an act."""
    return outline_db.get_scenes_by_act(project_id, act_id)


@app.put("/api/outline/scenes/{scene_id}/act")
async def assign_scene_to_act(scene_id: int, act_id: Optional[int] = None) -> dict:
    """Assign a scene to an act (or remove from act if act_id is null)."""
    scene = outline_db.assign_scene_to_act(scene_id, act_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
    return scene


@app.get("/api/outline/scenes")
async def get_scenes(project_id: int) -> list:
    """Get all scenes for a project."""
    return outline_db.get_scenes(project_id)


@app.post("/api/outline/scenes")
async def create_scene(project_id: int, request: SceneRequest) -> dict:
    """Create a new scene in a project."""
    if request.scene_number is None:
        raise HTTPException(status_code=400, detail="scene_number is required")
    result = outline_db.create_scene(project_id, request.scene_number, **request.model_dump(exclude={'scene_number'}, exclude_none=True))
    # Sync to memory
    parts = [f"Scene {request.scene_number}"]
    if request.title:
        parts.append(request.title)
    if request.description:
        parts.append(request.description)
    await sync_to_memory(project_id, " | ".join(parts))
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
async def reorder_scene(project_id: int, scene_id: int, request: SceneReorderRequest) -> dict:
    """Reorder a scene to a new position."""
    scene = outline_db.reorder_scene(project_id, scene_id, request.new_scene_number)
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
    return scene


@app.get("/api/outline")
async def get_full_outline(project_id: int) -> dict:
    """Get the complete outline for a project."""
    project = outline_db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return {
        "project": project,
        "notes": outline_db.get_writer_notes(project_id) or {},
        "characters": outline_db.get_characters(project_id),
        "acts": outline_db.get_acts(project_id),
        "scenes": outline_db.get_scenes(project_id)
    }


# --- Conversation Endpoints ---

class ConversationRequest(BaseModel):
    title: Optional[str] = None
    messages: Optional[list] = None
    active_buckets: Optional[list] = None


@app.get("/api/conversations")
async def list_conversations(project_id: int) -> list:
    """List all conversations for a project."""
    return outline_db.get_conversations(project_id)


@app.post("/api/conversations")
async def create_conversation(project_id: int, request: ConversationRequest) -> dict:
    """Create a new conversation in a project."""
    return outline_db.create_conversation(
        project_id,
        title=request.title or "New Chat",
        messages=request.messages or [],
        active_buckets=request.active_buckets or []
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
    """Update a conversation (title, messages, and/or active_buckets)."""
    conv = outline_db.update_conversation(
        conversation_id,
        title=request.title,
        messages=request.messages,
        active_buckets=request.active_buckets
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


# --- Memory Endpoints (Hindsight proxy) ---

@app.get("/api/memory/banks")
async def list_memory_banks() -> dict:
    """List all Hindsight memory banks."""
    import httpx
    async with httpx.AsyncClient() as client:
        res = await client.get(f"http://127.0.0.1:{hindsight_server.port}/v1/default/banks")
        return res.json()

@app.get("/api/memory/banks/{bank_id}/memories")
async def list_memories(bank_id: str) -> dict:
    """List memories in a bank."""
    import httpx
    async with httpx.AsyncClient() as client:
        res = await client.get(f"http://127.0.0.1:{hindsight_server.port}/v1/default/banks/{bank_id}/memories/list")
        return res.json()

@app.get("/api/memory/banks/{bank_id}/entities")
async def list_entities(bank_id: str) -> dict:
    """List entities in a bank."""
    import httpx
    async with httpx.AsyncClient() as client:
        res = await client.get(f"http://127.0.0.1:{hindsight_server.port}/v1/default/banks/{bank_id}/entities")
        return res.json()

@app.get("/api/memory/banks/{bank_id}/stats")
async def get_memory_stats(bank_id: str) -> dict:
    """Get stats for a memory bank."""
    import httpx
    async with httpx.AsyncClient() as client:
        res = await client.get(f"http://127.0.0.1:{hindsight_server.port}/v1/default/banks/{bank_id}/stats")
        return res.json()


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
