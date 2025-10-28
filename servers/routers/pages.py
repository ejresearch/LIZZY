"""
Routes for serving HTML pages.
"""

from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def landing_page():
    """Serve the landing page."""
    html_path = Path("frontend/landing_page.html")
    if not html_path.exists():
        raise HTTPException(status_code=404, detail="Landing page not found")
    return html_path.read_text()


@router.get("/manager", response_class=HTMLResponse)
async def manager_page():
    """Serve the manager page."""
    html_path = Path("frontend/manager_page.html")
    if not html_path.exists():
        raise HTTPException(status_code=404, detail="Manager page not found")
    return html_path.read_text()


@router.get("/setup", response_class=HTMLResponse)
async def setup_redirect():
    """Redirect to manager page (backward compatibility)."""
    html_path = Path("frontend/manager_page.html")
    if not html_path.exists():
        raise HTTPException(status_code=404, detail="Manager page not found")
    return html_path.read_text()


@router.get("/brainstorm", response_class=HTMLResponse)
async def brainstorm_page():
    """Serve the brainstorm page."""
    html_path = Path("frontend/brainstorm_page.html")
    if not html_path.exists():
        raise HTTPException(status_code=404, detail="Brainstorm page not found")
    return html_path.read_text()


@router.get("/brainstorm/generate", response_class=HTMLResponse)
async def brainstorm_generation_page():
    """Serve the brainstorm generation page with live progress."""
    html_path = Path("frontend/brainstorm_generation.html")
    if not html_path.exists():
        raise HTTPException(status_code=404, detail="Brainstorm generation page not found")
    return html_path.read_text()


@router.get("/write", response_class=HTMLResponse)
async def write_page():
    """Serve the write page."""
    html_path = Path("frontend/write_page.html")
    if not html_path.exists():
        raise HTTPException(status_code=404, detail="Write page not found")
    return html_path.read_text()


@router.get("/write/generate", response_class=HTMLResponse)
async def write_generation_page():
    """Serve the write generation page with live progress."""
    html_path = Path("frontend/write_generation.html")
    if not html_path.exists():
        raise HTTPException(status_code=404, detail="Write generation page not found")
    return html_path.read_text()
