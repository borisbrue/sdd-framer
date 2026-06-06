from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse

from ..commands import StartProjectCommand, StopProjectCommand
from ..models import ProjectEntry
from ..registry import ProjectNotFoundError

router = APIRouter(prefix="/hub")


@router.get("/projects", response_model=list[ProjectEntry])
async def list_projects(request: Request) -> list[ProjectEntry]:
    registry = request.app.state.registry
    manager = request.app.state.manager
    entries = registry.get_all()
    result = []
    for entry in entries:
        live_status, live_pid = manager.get_live_status(entry.id)
        result.append(entry.model_copy(update={"status": live_status, "pid": live_pid}))
    return result


@router.post("/projects/{project_id}/start")
async def start_project(project_id: str, request: Request) -> dict:
    manager = request.app.state.manager
    try:
        cmd = StartProjectCommand(project_id)
        cmd.execute(manager)
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    registry = request.app.state.registry
    entry = registry.get(project_id)
    return {"status": "starting", "pid": entry.pid}


@router.post("/projects/{project_id}/stop")
async def stop_project(project_id: str, request: Request) -> dict:
    manager = request.app.state.manager
    try:
        cmd = StopProjectCommand(project_id)
        cmd.execute(manager)
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return {"status": "stopped"}


@router.get("/projects/stream")
async def stream_project_events(request: Request) -> StreamingResponse:
    bus = request.app.state.bus
    registry = request.app.state.registry

    async def generator():
        project_ids = [e.id for e in registry.get_all()]
        merged: asyncio.Queue = asyncio.Queue()
        tasks = []

        for pid in project_ids:
            async def feed(project_id=pid):
                async for event in bus.subscribe(project_id):
                    await merged.put(event)

            tasks.append(asyncio.create_task(feed()))

        yield ": connected\n\n"
        heartbeat_tick = 0
        while True:
            try:
                item = await asyncio.wait_for(merged.get(), timeout=0.5)
                yield f"data: {json.dumps(item.model_dump(mode='json'))}\n\n"
                heartbeat_tick = 0
            except asyncio.TimeoutError:
                if await request.is_disconnected():
                    for t in tasks:
                        t.cancel()
                    break
                heartbeat_tick += 1
                if heartbeat_tick >= 30:
                    yield ": heartbeat\n\n"
                    heartbeat_tick = 0

    return StreamingResponse(generator(), media_type="text/event-stream")


@router.get("/", response_class=HTMLResponse)
async def hub_projects_ui(request: Request) -> HTMLResponse:
    templates = request.app.state.templates
    registry = request.app.state.registry
    manager = request.app.state.manager
    entries = registry.get_all()
    projects = []
    for entry in entries:
        live_status, live_pid = manager.get_live_status(entry.id)
        projects.append(entry.model_copy(update={"status": live_status, "pid": live_pid}))
    return templates.TemplateResponse(request, "hub_projects.html", {"projects": projects})
