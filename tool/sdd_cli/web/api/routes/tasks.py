"""Tasks API – GET /api/specs/{spec_id}/tasks + SSE /events (SPEC-0034, CON-0123)."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

sys.path.insert(0, str(Path(__file__).parents[1]))
from sdd_context import get_root

router = APIRouter()


def _get_store():
    from sdd_cli.task_store import TaskStore
    return TaskStore(Path(get_root()))


def _get_bus():
    from sdd_cli.task_event_bus import get_task_event_bus
    return get_task_event_bus()


@router.get("/specs/{spec_id}/tasks", summary="Tasks des letzten Runs (FR-01, CON-0123)")
def get_tasks(spec_id: str):
    store = _get_store()
    specs_dir = Path(get_root()) / ".sdd" / "specs"
    spec_files = list(specs_dir.glob(f"{spec_id}-*.md")) if specs_dir.exists() else []
    if not spec_files:
        raise HTTPException(status_code=404, detail=f"Spec {spec_id} nicht gefunden")

    run_id, tasks = store.load_latest(spec_id)
    return {
        "spec_id": spec_id,
        "run_id": run_id,
        "tasks": [t.to_dict() for t in tasks],
    }


@router.get("/specs/{spec_id}/tasks/events", summary="SSE-Stream für Task-Updates (FR-02, CON-0123)")
async def task_events(spec_id: str):
    specs_dir = Path(get_root()) / ".sdd" / "specs"
    spec_files = list(specs_dir.glob(f"{spec_id}-*.md")) if specs_dir.exists() else []
    if not spec_files:
        raise HTTPException(status_code=404, detail=f"Spec {spec_id} nicht gefunden")

    bus = _get_bus()

    async def event_generator():
        try:
            async for event_type, payload in bus.stream(spec_id):
                data = json.dumps(payload, ensure_ascii=False)
                yield f"event: {event_type}\ndata: {data}\n\n"
        except asyncio.CancelledError:
            return

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
