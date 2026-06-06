from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .config import HubConfig
from .events import StatusEventBus
from .process_manager import ProcessManager
from .registry import ProjectRegistry

_TEMPLATES_DIR = Path(__file__).parent / "templates"


def create_app(
    registry: ProjectRegistry | None = None,
    event_bus: StatusEventBus | None = None,
    config: HubConfig | None = None,
) -> FastAPI:
    cfg = config or HubConfig.load()
    reg = registry or ProjectRegistry()
    bus = event_bus or StatusEventBus()
    manager = ProcessManager(reg, bus)
    templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        manager.start_watching()
        yield
        manager.stop_watching()

    app = FastAPI(title="SDD Hub", lifespan=lifespan)
    app.state.registry = reg
    app.state.manager = manager
    app.state.bus = bus
    app.state.templates = templates

    from .routes.projects import router as projects_router
    app.include_router(projects_router)

    return app
