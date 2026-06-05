"""FastAPI-Server für die SDD Web UI.

Bedient die sdd-CLI per REST-Endpunkte und serviert das React-Build.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

# sdd_cli aus dem tool/-Verzeichnis importierbar machen
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tool"))
sys.path.insert(0, str(Path(__file__).parent))

import sdd_context
from routes.hub import router as hub_router, hub_health_loop
from routes.ai import router as ai_router
from routes.analyze import router as analyze_router
from routes.analyze_async import router as analyze_async_router
from routes.auth import router as auth_router
from routes.chat import router as chat_router
from routes.commands import router as commands_router
from routes.contracts import router as contracts_router
from routes.copilot import router as copilot_router
from routes.gate import router as gate_router
from routes.logs import router as logs_router
from routes.orchestrate import router as orchestrate_router
from routes.pipeline import router as pipeline_router
from routes.remote import router as remote_router
from routes.agent_flow import router as agent_flow_router  # SPEC-0032
from routes.interactive import router as interactive_router
from routes.specs import router as specs_router
from routes.tasks import router as tasks_router  # SPEC-0034
from routes.tests import router as tests_router
from routes.dag_monitor import router as dag_monitor_router  # SPEC-0037

# SPEC-0025: CORS-Origins aus Umgebungsvariable (gesetzt via --allowed-origins)
_raw_origins = os.environ.get("SDD_ALLOWED_ORIGINS", "")
_ALLOWED_ORIGINS: list[str] = (
    [o.strip() for o in _raw_origins.split(",") if o.strip()]
    if _raw_origins
    else ["http://localhost:5173", "http://localhost:8000"]
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not os.environ.get("SDD_HUB_MODE"):
        sdd_context.init()
    asyncio.create_task(hub_health_loop())
    yield


app = FastAPI(title="SDD Web API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(hub_router,           prefix="/api")  # Hub – vor SPA-Fallback
app.include_router(agent_flow_router,    prefix="/api")  # SPEC-0032
app.include_router(interactive_router,   prefix="/api")  # SPEC-0028
app.include_router(specs_router,         prefix="/api")
app.include_router(tasks_router,         prefix="/api")  # SPEC-0034
app.include_router(dag_monitor_router,   prefix="/api")  # SPEC-0037
app.include_router(pipeline_router,      prefix="/api")
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
app.include_router(remote_router,        prefix="/api")  # SPEC-0023
app.include_router(logs_router)          # WebSocket /ws/logs/{spec_id} – kein /api-Prefix
app.include_router(chat_router)          # WebSocket /ws/chat – kein /api-Prefix (SPEC-0023)

# Static assets (vor dem Catch-All registrieren)
UI_DIST = Path(__file__).parent.parent / "ui" / "dist"
if UI_DIST.exists():
    app.mount("/assets", StaticFiles(directory=UI_DIST / "assets"), name="assets")


# Catch-All: Hub-Dashboard auf / oder React-SPA
@app.get("/{full_path:path}", include_in_schema=False, response_model=None)
async def spa_fallback(full_path: str) -> FileResponse | HTMLResponse:
    if os.environ.get("SDD_HUB_MODE"):
        from routes.hub import _HUB_HTML
        return HTMLResponse(_HUB_HTML)
    if UI_DIST.exists():
        return FileResponse(UI_DIST / "index.html")
    return HTMLResponse("<h1>SDD API</h1><p>Web UI nicht gebaut.</p>", status_code=200)


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
    os.environ["SDD_PORT"] = str(args.port)

    uvicorn.run("main:app", host="0.0.0.0", port=args.port, reload=True)
