from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse

from ..commands import StartProjectCommand, StopProjectCommand
from ..models import ProjectEntry
from ..registry import ProjectNotFoundError

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/projects")
async def list_projects(request: Request) -> dict:
    registry = request.app.state.registry
    manager = request.app.state.manager
    entries = registry.get_all()
    result = []
    for entry in entries:
        live_status, live_pid = manager.get_live_status(entry.id)
        updated = entry.model_copy(update={"status": live_status, "pid": live_pid})
        result.append(updated)
    return {
        "projects": [e.model_dump(mode="json") for e in result],
        "retrievedAt": datetime.now(timezone.utc).isoformat(),
    }


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


@router.get("/projects/{project_id}/qr-payload")
async def get_project_qr_payload(project_id: str, request: Request) -> dict:
    registry = request.app.state.registry
    manager = request.app.state.manager
    try:
        entry = registry.get(project_id)
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    live_status, _ = manager.get_live_status(project_id)
    if live_status != "running":
        raise HTTPException(status_code=409, detail="project_not_running")
    try:
        async with httpx.AsyncClient(verify=False, timeout=5.0) as client:
            r = await client.get(f"http://localhost:{entry.port}/api/auth/qr-payload")
            if r.status_code != 200:
                raise HTTPException(status_code=502, detail="project_qr_error")
            return r.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail="project_unreachable") from e


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
