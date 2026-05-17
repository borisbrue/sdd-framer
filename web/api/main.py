"""FastAPI-Server für die SDD Web UI.

Bedient die sdd-CLI per REST-Endpunkte und serviert das React-Build.
"""
from __future__ import annotations

import argparse
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# sdd_cli aus dem tool/-Verzeichnis importierbar machen
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tool"))
sys.path.insert(0, str(Path(__file__).parent))

import sdd_context  # noqa: E402
from routes.ai import router as ai_router  # noqa: E402
from routes.analyze import router as analyze_router  # noqa: E402
from routes.analyze_async import router as analyze_async_router  # noqa: E402
from routes.auth import router as auth_router  # noqa: E402
from routes.commands import router as commands_router  # noqa: E402
from routes.contracts import router as contracts_router  # noqa: E402
from routes.copilot import router as copilot_router  # noqa: E402
from routes.gate import router as gate_router  # noqa: E402
from routes.logs import router as logs_router  # noqa: E402
from routes.orchestrate import router as orchestrate_router  # noqa: E402
from routes.projects import router as projects_router  # noqa: E402
from routes.specs import router as specs_router  # noqa: E402
from routes.tests import router as tests_router  # noqa: E402

# SPEC-0025: CORS-Origins aus Umgebungsvariable (gesetzt via --allowed-origins)
_raw_origins = os.environ.get("SDD_ALLOWED_ORIGINS", "")
_ALLOWED_ORIGINS: list[str] = (
    [o.strip() for o in _raw_origins.split(",") if o.strip()]
    if _raw_origins
    else ["http://localhost:5173", "http://localhost:8000"]
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    sdd_context.init()
    yield


app = FastAPI(title="SDD Web API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects_router,      prefix="/api")
app.include_router(specs_router,         prefix="/api")
app.include_router(contracts_router,     prefix="/api")
app.include_router(tests_router,         prefix="/api")
app.include_router(commands_router,      prefix="/api")
app.include_router(gate_router,          prefix="/api")
app.include_router(orchestrate_router,   prefix="/api")
app.include_router(ai_router,            prefix="/api")
app.include_router(analyze_router,       prefix="/api")
app.include_router(analyze_async_router, prefix="/api")
app.include_router(copilot_router,       prefix="/api")
app.include_router(auth_router,          prefix="/api")  # SPEC-0025
app.include_router(logs_router)  # WebSocket /ws/logs/{spec_id} – kein /api-Prefix

# React-Build servieren (nach `npm run build`)
UI_DIST = Path(__file__).parent.parent / "ui" / "dist"
if UI_DIST.exists():
    app.mount("/assets", StaticFiles(directory=UI_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str) -> FileResponse:
        return FileResponse(UI_DIST / "index.html")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SDD Web API")
    parser.add_argument("--project", default=".", help="Pfad zum SDD-Projekt")
    parser.add_argument("--port", type=int, default=8000)
    # SPEC-0025: FR-01 — externe URL und CORS-Origins konfigurierbar
    parser.add_argument(
        "--external-url",
        default="",
        help="Externe URL des Servers für QR-Code (z.B. http://rechner.tail.ts.net:8000)",
    )
    parser.add_argument(
        "--allowed-origins",
        default="http://localhost:5173,http://localhost:8000",
        help="Kommaseparierte Liste erlaubter CORS-Origins (FR-10)",
    )
    args = parser.parse_args()

    os.environ["SDD_PROJECT_ROOT"] = str(Path(args.project).resolve())
    os.environ["SDD_EXTERNAL_URL"] = args.external_url
    os.environ["SDD_ALLOWED_ORIGINS"] = args.allowed_origins

    uvicorn.run("main:app", host="0.0.0.0", port=args.port, reload=True)
