"""Minimaler statischer Server für die SDD PWA (SPA)."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

_dist = Path(__file__).parent / "dist"

app = FastAPI(docs_url=None, redoc_url=None)

if (_dist / "assets").exists():
    app.mount("/assets", StaticFiles(directory=_dist / "assets"), name="assets")

@app.get("/{full_path:path}")
async def spa(full_path: str) -> FileResponse:
    target = _dist / full_path
    if full_path and target.exists() and target.is_file():
        return FileResponse(target)
    return FileResponse(_dist / "index.html")
