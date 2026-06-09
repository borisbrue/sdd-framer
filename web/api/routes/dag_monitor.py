"""Agent-DAG-Monitor API für SPEC-0037.

FR-01: GET /api/orchestrate/runs — Run-Liste
FR-02: GET /api/orchestrate/stream/{run_id} — SSE DagEvent-Stream
FR-04: POST /api/orchestrate/command/{run_id} — SchedulerCommand
"""
from __future__ import annotations

import asyncio
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parents[1]))
from sdd_cli.dag_event import get_event_bus
from sdd_cli.dag_command import build_command, get_command_queue

router = APIRouter()

# ─── Run registry ─────────────────────────────────────────────────────────────

@dataclass
class DagRunEntry:
    run_id: str
    spec_id: str
    status: str = "running"
    started_at: float = field(default_factory=time.time)


_runs: dict[str, DagRunEntry] = {}
_TTL = 3600.0


def register_run(run_id: str, spec_id: str) -> None:
    _cleanup()
    _runs[run_id] = DagRunEntry(run_id=run_id, spec_id=spec_id)


def finish_run(run_id: str, status: str = "done") -> None:
    entry = _runs.get(run_id)
    if entry:
        entry.status = status


def _cleanup() -> None:
    now = time.time()
    stale = [k for k, v in _runs.items() if now - v.started_at > _TTL]
    for k in stale:
        _runs.pop(k, None)


def _runs_list(max_history: int = 5) -> list[dict]:
    _cleanup()
    entries = sorted(_runs.values(), key=lambda e: e.started_at, reverse=True)
    running = [e for e in entries if e.status == "running"]
    done = [e for e in entries if e.status != "running"][:max_history]
    return [
        {"run_id": e.run_id, "spec_id": e.spec_id, "status": e.status, "started_at": e.started_at}
        for e in running + done
    ]


# ─── Schema ───────────────────────────────────────────────────────────────────

class CommandRequest(BaseModel):
    command_type: str
    task_id: str


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/orchestrate/runs", summary="Laufende + abgeschlossene DAG-Runs (SPEC-0037 FR-01)")
def list_runs() -> list[dict]:
    try:
        from sdd_context import get_config
        max_h = get_config().raw.get("dag_monitor", {}).get("max_runs_history", 5)
    except Exception:
        max_h = 5
    return _runs_list(max_h)


@router.get("/orchestrate/stream/{run_id}", summary="SSE DagEvent-Stream (SPEC-0037 FR-02)")
async def stream_dag_events(run_id: str) -> StreamingResponse:
    bus = get_event_bus()

    try:
        from sdd_context import get_config
        heartbeat = get_config().raw.get("dag_monitor", {}).get("sse_heartbeat_seconds", 15)
    except Exception:
        heartbeat = 15

    async def _generate_with_heartbeat():
        yield ": connected\n\n"

        hb_queue: asyncio.Queue = asyncio.Queue()

        async def _send_heartbeats():
            while True:
                await asyncio.sleep(heartbeat)
                await hb_queue.put(None)

        hb_task = asyncio.create_task(_send_heartbeats())
        try:
            async for event in bus.subscribe(run_id):
                yield f"data: {event.model_dump_json()}\n\n"
                while not hb_queue.empty():
                    hb_queue.get_nowait()
                    yield ": heartbeat\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            hb_task.cancel()

    return StreamingResponse(
        _generate_with_heartbeat(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


@router.post(
    "/orchestrate/command/{run_id}",
    status_code=202,
    summary="SchedulerCommand an laufenden Run senden (SPEC-0037 FR-04)",
)
def send_command(run_id: str, body: CommandRequest) -> dict[str, Any]:
    try:
        cmd = build_command(run_id=run_id, task_id=body.task_id, command_type=body.command_type)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    q = get_command_queue()
    try:
        q.enqueue_sync(cmd)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"queued": True, "run_id": run_id, "command_type": body.command_type, "task_id": body.task_id}
