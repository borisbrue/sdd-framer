"""Pipeline-Monitor der Web-UI (SPEC-0037, umgebaut in SPEC-0058 FR-06, CON-0211).

GET  /api/orchestrate/runs              — Runs von `sdd pipeline run`
GET  /api/orchestrate/stream/{run_id}   — SSE mit Task-Ereignissen im DagEvent-Format
POST /api/orchestrate/command/{run_id}  — abgelöst (410), Entscheidungen über `sdd pipeline decide`

Die Route liest Runs ausschließlich über `sdd_cli.pipeline.monitor` (ADR-0003); Pfade und
Antwortformate bleiben, damit die gebaute Web-UI unverändert funktioniert.
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

sys.path.insert(0, str(Path(__file__).parents[4]))
from sdd_cli.pipeline import monitor

router = APIRouter()

# CON-0211 INV-04: neue Ereignisse erscheinen spätestens nach diesem Abstand im Stream.
POLL_SECONDS = 1.0


def _root() -> Path:
    from sdd_context import get_config

    return get_config().root


def _dag_setting(key: str, default: int) -> int:
    try:
        from sdd_context import get_config

        return int(get_config().raw.get("dag_monitor", {}).get(key, default))
    except Exception:
        return default


@router.get("/orchestrate/runs", summary="Pipeline-Runs (SPEC-0058 FR-06)")
def list_runs() -> list[dict]:
    runs = monitor.list_runs(_root())
    laufend = [r for r in runs if r["status"] in ("running", "paused")]
    fertig = [r for r in runs if r["status"] not in ("running", "paused")]
    return laufend + fertig[:_dag_setting("max_runs_history", 5)]


@router.get("/orchestrate/stream/{run_id}", summary="SSE-Stream der Task-Ereignisse eines Runs")
async def stream_dag_events(run_id: str) -> StreamingResponse:
    root = _root()
    try:
        monitor.task_events(root, run_id, 0)
    except monitor.RunNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    heartbeat = _dag_setting("sse_heartbeat_seconds", 15)

    def _daten(ereignisse: list[dict]) -> str:
        return "".join(f"data: {json.dumps(e, ensure_ascii=False)}\n\n" for e in ereignisse)

    async def _generate():
        yield ": connected\n\n"
        offset, still = 0, 0.0
        while True:
            ereignisse, offset = monitor.task_events(root, run_id, offset)
            if ereignisse:
                yield _daten(ereignisse)
            if not monitor.is_active(root, run_id):
                # Ereignisse, die nach dem Lesen und vor dem Statuswechsel kamen, noch senden.
                rest, offset = monitor.task_events(root, run_id, offset)
                if rest:
                    yield _daten(rest)
                return
            await asyncio.sleep(POLL_SECONDS)
            still = 0.0 if ereignisse else still + POLL_SECONDS
            if still >= heartbeat:
                still = 0.0
                yield ": heartbeat\n\n"

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


@router.post("/orchestrate/command/{run_id}", summary="Abgelöst: sdd pipeline decide")
def send_command(run_id: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    raise HTTPException(
        status_code=410,
        detail=f"Befehle an laufende Runs gibt es nicht mehr (SPEC-0058). Entscheidungen der "
               f"Pipeline: sdd pipeline decide {run_id} --json '…'",
    )
