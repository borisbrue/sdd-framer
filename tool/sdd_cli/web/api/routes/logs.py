"""WebSocket endpoint /ws/logs/{spec_id} für Live Container-Logs (SPEC-0022)."""
from __future__ import annotations

import asyncio
import json
import re

import sdd_context
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

_SPEC_ID_RE = re.compile(r"^SPEC-\d{4}$")
_CLOSE_INVALID = 4000


@router.websocket("/ws/logs/{spec_id}")
async def ws_logs(websocket: WebSocket, spec_id: str) -> None:
    if not _SPEC_ID_RE.match(spec_id):
        await websocket.close(code=_CLOSE_INVALID)
        return

    await websocket.accept()

    bus = sdd_context.get_log_event_bus()

    if not bus.has_stream(spec_id):
        await websocket.send_text(
            json.dumps({"error": "no_stream", "spec_id": spec_id})
        )
        await websocket.close()
        return

    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[str] = asyncio.Queue()

    for raw_msg in bus.get_buffer(spec_id):
        try:
            data = json.loads(raw_msg)
            data["buffered"] = True
            await websocket.send_text(json.dumps(data))
        except Exception:
            pass

    def on_line(msg: str) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, msg)

    bus.subscribe(spec_id, on_line)
    try:
        while True:
            msg = await queue.get()
            await websocket.send_text(msg)
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        bus.unsubscribe(spec_id, on_line)
