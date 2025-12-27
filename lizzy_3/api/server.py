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

@app.post("/api/expert/chat")
async def expert_chat(request: ExpertChatRequest) -> dict:
    """
    Chat with an expert using the LLM + System Prompt + Bucket pattern.

    1. Query the bucket for relevant context (RAG)
    2. Build prompt with system prompt + context + conversation history
    3. Call LLM and return response
    """
    from openai import AsyncOpenAI

    client = AsyncOpenAI()

    # Step 1: Query bucket for relevant context
    try:
        context = await bucket_manager.query(
            request.bucket,
            request.message,
            request.rag_mode
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        # If RAG fails, continue without context
        context = ""

    # Step 2: Build messages for LLM
    messages = []

    # System prompt with context injection
    system_content = request.system_prompt
    if context:
        system_content += f"\n\n---\nRelevant knowledge from your expertise:\n{context[:3000]}"

    messages.append({"role": "system", "content": system_content})

    # Add conversation history
    for msg in request.history[-10:]:  # Last 10 messages
        if isinstance(msg, dict) and "role" in msg and "content" in msg:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

    # Add current user message
    messages.append({"role": "user", "content": request.message})

    # Step 3: Call LLM
    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.7,
            max_tokens=1500
        )

        assistant_message = response.choices[0].message.content

        # Summarize context used
        context_summary = None
        if context:
            context_preview = context[:200].replace("\n", " ")
            context_summary = f"{len(context)} chars retrieved"

        return {
            "response": assistant_message,
            "context_used": context_summary,
            "model": "gpt-4o"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM error: {str(e)}")


# --- Outline Endpoints (SQLite) ---

from .database import db as outline_db


@app.get("/api/outline/project")
async def get_project() -> dict:
    """Get project metadata."""
    return outline_db.get_project()


@app.put("/api/outline/project")
async def update_project(request: ProjectUpdateRequest) -> dict:
    """Update project metadata."""
    return outline_db.update_project(**request.model_dump(exclude_none=True))


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
    return outline_db.create_character(**request.model_dump(exclude_none=True))


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


@app.get("/api/outline/scenes")
async def get_scenes() -> list:
    """Get all scenes."""
    return outline_db.get_scenes()


@app.post("/api/outline/scenes")
async def create_scene(request: SceneRequest) -> dict:
    """Create a new scene."""
    if request.scene_number is None:
        raise HTTPException(status_code=400, detail="scene_number is required")
    return outline_db.create_scene(request.scene_number, **request.model_dump(exclude={'scene_number'}, exclude_none=True))


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


@app.get("/api/outline")
async def get_full_outline() -> dict:
    """Get the complete outline (project + notes + characters + scenes)."""
    return {
        "project": outline_db.get_project(),
        "notes": outline_db.get_writer_notes(),
        "characters": outline_db.get_characters(),
        "scenes": outline_db.get_scenes()
    }


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
