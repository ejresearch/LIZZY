"""
Landing Page Server for Lizzy 2.0

Simple FastAPI server that serves the landing page and provides
API endpoints for tracking project progress and launching modules.
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import json
import subprocess
from typing import Dict, List
from pydantic import BaseModel

app = FastAPI(title="Lizzy 2.0 Landing Page")


# Models
class ProjectStatus(BaseModel):
    current_project: str | None
    steps: Dict[str, bool]


class ModuleLaunch(BaseModel):
    module: str
    project_name: str | None = None


# Load landing page HTML
@app.get("/", response_class=HTMLResponse)
async def landing_page():
    """Serve the landing page"""
    html_path = Path("landing_page.html")
    if not html_path.exists():
        raise HTTPException(status_code=404, detail="Landing page not found")

    return html_path.read_text()


# Load manager page HTML (formerly setup)
@app.get("/manager", response_class=HTMLResponse)
async def manager_page():
    """Serve the manager page"""
    html_path = Path("manager_page.html")
    if not html_path.exists():
        raise HTTPException(status_code=404, detail="Manager page not found")

    return html_path.read_text()

# Redirect old /setup to /manager for backward compatibility
@app.get("/setup", response_class=HTMLResponse)
async def setup_redirect():
    """Redirect to manager page"""
    html_path = Path("manager_page.html")
    if not html_path.exists():
        raise HTTPException(status_code=404, detail="Manager page not found")
    return html_path.read_text()


# Get list of projects
@app.get("/api/projects")
async def get_projects():
    """Get list of all projects"""
    projects_dir = Path("projects")

    if not projects_dir.exists():
        return {"projects": []}

    projects = []
    for project_dir in projects_dir.iterdir():
        if project_dir.is_dir():
            db_path = project_dir / f"{project_dir.name}.db"
            if db_path.exists():
                projects.append({
                    "name": project_dir.name,
                    "path": str(project_dir),
                    "has_database": True
                })

    return {"projects": projects}


# Get project status
@app.get("/api/status/{project_name}")
async def get_project_status(project_name: str):
    """Get completion status for a project"""
    from lizzy.database import Database

    db_path = Path(f"projects/{project_name}/{project_name}.db")

    if not db_path.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    db = Database(db_path)

    # Check each step
    status = {
        "current_project": project_name,
        "steps": {
            "start": True,  # If DB exists, start is complete
            "intake": False,
            "brainstorm": False,
            "write": False,
            "export": False
        }
    }

    with db.get_connection() as conn:
        cursor = conn.cursor()

        # Check intake (has characters or scenes)
        cursor.execute("SELECT COUNT(*) FROM characters")
        char_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM scenes WHERE description IS NOT NULL AND description != ''")
        scene_count = cursor.fetchone()[0]

        status["steps"]["intake"] = char_count > 0 or scene_count > 0

        # Check brainstorm (has brainstorm_sessions)
        cursor.execute("SELECT COUNT(*) FROM brainstorm_sessions")
        brainstorm_count = cursor.fetchone()[0]
        status["steps"]["brainstorm"] = brainstorm_count > 0

        # Check write (has scene_drafts)
        cursor.execute("SELECT COUNT(*) FROM scene_drafts")
        draft_count = cursor.fetchone()[0]
        status["steps"]["write"] = draft_count > 0

        # Check export (has files in exports/)
        exports_dir = Path(f"projects/{project_name}/exports")
        if exports_dir.exists():
            export_files = list(exports_dir.glob("*"))
            status["steps"]["export"] = len(export_files) > 0

    return status


# Launch module (returns CLI command for now)
@app.post("/api/launch")
async def launch_module(launch: ModuleLaunch):
    """Get CLI command to launch a module"""

    commands = {
        "start": "python3 -m lizzy.start",
        "intake": "python3 -m lizzy.intake",
        "brainstorm": "python3 -m lizzy.automated_brainstorm",
        "write": "python3 -m lizzy.automated_write",
        "export": "python3 -m lizzy.export",
        "prompt_studio": "./start_prompt_studio.sh"
    }

    if launch.module not in commands:
        raise HTTPException(status_code=400, detail="Invalid module")

    command = commands[launch.module]

    # Add project name if provided
    if launch.project_name and launch.module in ["intake"]:
        command += f' "{launch.project_name}"'

    return {
        "module": launch.module,
        "command": command,
        "message": f"Run this command in your terminal:\n\n{command}"
    }


# Get single project details
@app.get("/api/project/{project_name}")
async def get_project(project_name: str):
    """Get full project details including characters, scenes, notes"""
    from lizzy.database import Database

    db_path = Path(f"projects/{project_name}/{project_name}.db")

    if not db_path.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    db = Database(db_path)
    project_data = db.get_project()

    # Get characters
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name, description, role FROM characters")
        characters = [dict(row) for row in cursor.fetchall()]

        # Get scenes
        cursor.execute("SELECT scene_number, title, description, characters FROM scenes ORDER BY scene_number")
        scenes = []
        for row in cursor.fetchall():
            scene = dict(row)
            # Calculate act based on scene number
            scene_num = scene['scene_number']
            if scene_num <= 6:
                scene['act'] = 1
            elif scene_num <= 24:
                scene['act'] = 2
            else:
                scene['act'] = 3
            scenes.append(scene)

        # Get notes from writer_notes table
        cursor.execute("SELECT theme, tone, comps, inspiration FROM writer_notes LIMIT 1")
        notes_row = cursor.fetchone()
        if notes_row:
            notes = {
                'theme': notes_row['theme'] or '',
                'tone': notes_row['tone'] or '',
                'comparable_films': notes_row['comps'] or '',
                'inspiration': notes_row['inspiration'] or ''
            }
        else:
            notes = {}

    return {
        "name": project_data.get('name'),
        "genre": project_data.get('genre'),
        "logline": project_data.get('description'),
        "characters": characters,
        "scenes": scenes,
        "notes": notes
    }


# Save/create project
@app.post("/api/project/save")
async def save_project(project_data: dict):
    """Save or create a project"""
    from lizzy.start import StartModule
    from lizzy.database import Database

    try:
        name = project_data['name']
        genre = project_data.get('genre', 'Romantic Comedy')
        logline = project_data.get('logline', '')
        template = project_data.get('template', 'beatsheet')
        is_new = project_data.get('is_new', False)
        characters = project_data.get('characters', [])
        scenes = project_data.get('scenes', [])
        notes = project_data.get('notes', {})

        start = StartModule()

        if is_new:
            # Create new project
            if template == 'beatsheet':
                db_path = start.create_from_beat_sheet(name=name, genre=genre)
            else:
                db_path = start.create_project(name=name, genre=genre, description=logline)
        else:
            # Update existing project
            db_path = start.get_project_path(name)
            if not db_path:
                raise HTTPException(status_code=404, detail="Project not found")

        # Update all project data
        db = Database(db_path)
        with db.get_connection() as conn:
            cursor = conn.cursor()

            # Update project metadata
            cursor.execute(
                "UPDATE projects SET genre = ?, description = ? WHERE id = 1",
                (genre, logline)
            )

            # Update characters
            if characters:
                # Clear existing characters
                cursor.execute("DELETE FROM characters")
                # Insert new characters
                for char in characters:
                    cursor.execute(
                        "INSERT INTO characters (name, role, description) VALUES (?, ?, ?)",
                        (char.get('name', ''), char.get('role', ''), char.get('description', ''))
                    )

            # Update scenes
            if scenes:
                for scene in scenes:
                    scene_num = scene.get('scene_number')
                    if scene_num:
                        cursor.execute(
                            """UPDATE scenes
                               SET title = ?, description = ?, characters = ?
                               WHERE scene_number = ?""",
                            (
                                scene.get('title', ''),
                                scene.get('description', ''),
                                scene.get('characters', ''),
                                scene_num
                            )
                        )

            # Update notes
            if notes:
                # Check if writer_notes row exists
                cursor.execute("SELECT COUNT(*) FROM writer_notes")
                count = cursor.fetchone()[0]

                if count > 0:
                    # Update existing row
                    cursor.execute(
                        """UPDATE writer_notes
                           SET theme = ?, tone = ?, comps = ?, inspiration = ?
                           WHERE id = (SELECT id FROM writer_notes LIMIT 1)""",
                        (
                            notes.get('theme', ''),
                            notes.get('tone', ''),
                            notes.get('comparable_films', ''),
                            notes.get('inspiration', '')
                        )
                    )
                else:
                    # Insert new row
                    cursor.execute(
                        "INSERT INTO writer_notes (theme, tone, comps, inspiration) VALUES (?, ?, ?, ?)",
                        (
                            notes.get('theme', ''),
                            notes.get('tone', ''),
                            notes.get('comparable_films', ''),
                            notes.get('inspiration', '')
                        )
                    )

            conn.commit()

        return {"success": True, "project_name": name}

    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {str(e)}"}


# Delete project
@app.delete("/api/project/{project_name}")
async def delete_project(project_name: str):
    """Delete a project"""
    from lizzy.start import StartModule

    try:
        start = StartModule()
        start.delete_project(project_name)
        return {"success": True}
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {str(e)}"}


# Brainstorm page
@app.get("/brainstorm", response_class=HTMLResponse)
async def brainstorm_page():
    """Serve the brainstorm page"""
    html_path = Path("brainstorm_page.html")
    if not html_path.exists():
        raise HTTPException(status_code=404, detail="Brainstorm page not found")

    return html_path.read_text()


# Brainstorm API endpoints
@app.get("/api/brainstorm/chat/history")
async def get_chat_history(project: str):
    """Get chat history for a project"""
    # TODO: Implement chat history storage
    return {"messages": []}


@app.post("/api/brainstorm/chat/query")
async def chat_query(request_data: dict):
    """Send a query to the expert knowledge graphs"""
    from lizzy.interactive_brainstorm import InteractiveBrainstorm

    project_name = request_data.get('project')
    query = request_data.get('query')
    focused_scene = request_data.get('focused_scene')

    if not project_name or not query:
        return {"success": False, "error": "Project name and query required"}

    db_path = Path(f"projects/{project_name}/{project_name}.db")
    if not db_path.exists():
        return {"success": False, "error": "Project not found"}

    try:
        brainstorm = InteractiveBrainstorm(db_path)
        brainstorm.load_project_context()

        # Set focused scene if provided
        if focused_scene:
            brainstorm.focused_scene = focused_scene

        # Query all three buckets
        buckets = ['books', 'plays', 'scripts']
        results = await brainstorm.query_buckets(query, buckets, mode="hybrid")

        # Format results for frontend
        experts = []
        for result in results:
            experts.append({
                'bucket': result['bucket'],
                'content': result['content']
            })

        return {
            "success": True,
            "message_id": len(brainstorm.conversation_history),
            "experts": experts
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": f"Failed to query: {str(e)}"
        }


@app.get("/api/brainstorm/batch/status")
async def get_batch_status(project: str):
    """Get status of all scenes for batch processing"""
    from lizzy.database import Database

    db_path = Path(f"projects/{project}/{project}.db")
    if not db_path.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    db = Database(db_path)

    with db.get_connection() as conn:
        cursor = conn.cursor()

        # Get all scenes
        cursor.execute("""
            SELECT s.scene_number, s.title, s.description,
                   COUNT(DISTINCT bs.id) as blueprint_count
            FROM scenes s
            LEFT JOIN brainstorm_sessions bs ON s.id = bs.scene_id
            GROUP BY s.scene_number
            ORDER BY s.scene_number
        """)

        scenes = []
        for row in cursor.fetchall():
            scene = dict(row)
            scene['status'] = 'done' if scene['blueprint_count'] > 0 else 'pending'
            scenes.append(scene)

    return {"scenes": scenes}


@app.post("/api/brainstorm/batch/start")
async def start_batch_process(request_data: dict):
    """Start batch processing all scenes"""
    import asyncio
    from lizzy.automated_brainstorm import AutomatedBrainstorm

    project_name = request_data.get('project')
    if not project_name:
        return {"success": False, "error": "Project name required"}

    db_path = Path(f"projects/{project_name}/{project_name}.db")
    if not db_path.exists():
        return {"success": False, "error": "Project not found"}

    try:
        # Run automated brainstorm in background
        brainstorm = AutomatedBrainstorm(db_path)

        # Start async processing in background
        async def process_scenes():
            brainstorm.load_project_context()
            await brainstorm.run_batch_processing()

        # Start background task
        asyncio.create_task(process_scenes())

        return {
            "success": True,
            "message": "Batch processing started"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to start batch process: {str(e)}"
        }


@app.post("/api/brainstorm/batch/generate-scene")
async def generate_scene_blueprint(request_data: dict):
    """Generate blueprint for a single scene"""
    from lizzy.automated_brainstorm import AutomatedBrainstorm

    project_name = request_data.get('project')
    scene_number = request_data.get('scene_number')

    if not project_name or not scene_number:
        return {"success": False, "error": "Project name and scene number required"}

    db_path = Path(f"projects/{project_name}/{project_name}.db")
    if not db_path.exists():
        return {"success": False, "error": "Project not found"}

    try:
        brainstorm = AutomatedBrainstorm(db_path)
        brainstorm.load_project_context()

        # Find the scene
        scene = next((s for s in brainstorm.scenes if s['scene_number'] == scene_number), None)
        if not scene:
            return {"success": False, "error": f"Scene {scene_number} not found"}

        # Process single scene (using Rich progress for CLI compatibility)
        from rich.progress import Progress
        with Progress() as progress:
            task_id = progress.add_task(f"Processing Scene {scene_number}", total=1)
            await brainstorm.process_scene(scene, progress, task_id)

        return {
            "success": True,
            "message": f"Scene {scene_number} blueprint generated"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to generate scene: {str(e)}"
        }


@app.get("/api/brainstorm/blueprints/{project_name}")
async def get_blueprints(project_name: str):
    """Get all scene blueprints for a project"""
    from lizzy.database import Database

    db_path = Path(f"projects/{project_name}/{project_name}.db")
    if not db_path.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    db = Database(db_path)

    with db.get_connection() as conn:
        cursor = conn.cursor()

        # Get all scenes with their blueprints
        cursor.execute("""
            SELECT
                s.scene_number,
                s.title,
                s.description,
                s.characters,
                bs.content,
                bs.bucket_used,
                bs.created_at
            FROM scenes s
            LEFT JOIN brainstorm_sessions bs ON s.id = bs.scene_id
            ORDER BY s.scene_number, bs.created_at DESC
        """)

        results = cursor.fetchall()

        # Group by scene
        blueprints = {}
        for row in results:
            scene_num = row['scene_number']
            if scene_num not in blueprints:
                blueprints[scene_num] = {
                    'scene_number': scene_num,
                    'title': row['title'],
                    'description': row['description'],
                    'characters': row['characters'],
                    'blueprint': None,
                    'experts': []
                }

            if row['content']:
                # If bucket_used is 'synthesis', it's the main blueprint
                if row['bucket_used'] == 'synthesis':
                    blueprints[scene_num]['blueprint'] = row['content']
                    blueprints[scene_num]['created_at'] = row['created_at']
                else:
                    # It's an expert consultation
                    blueprints[scene_num]['experts'].append({
                        'bucket': row['bucket_used'],
                        'content': row['content']
                    })

        return {"blueprints": list(blueprints.values())}


# Generate random rom-com
@app.post("/api/generate/random-romcom")
async def generate_random_romcom():
    """Generate a random romantic comedy project using AI"""
    try:
        # Import OpenAI
        from openai import OpenAI
        import os

        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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

        response = client.chat.completions.create(
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
        print(f"Error generating random rom-com: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# Health check
@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "service": "Lizzy 2.0 Landing Page"}


if __name__ == "__main__":
    import uvicorn

    print("\n" + "="*50)
    print("Lizzy 2.0 Landing Page Server")
    print("="*50)
    print("\nStarting server at: http://localhost:8002")
    print("\nAPI Endpoints:")
    print("  - GET  /                      Landing page")
    print("  - GET  /api/projects          List projects")
    print("  - GET  /api/status/{project}  Project status")
    print("  - POST /api/launch            Launch module")
    print("  - GET  /api/health            Health check")
    print("\n" + "="*50 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=8002)
