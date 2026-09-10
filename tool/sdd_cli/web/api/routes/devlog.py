"""SSE-Endpunkt /api/devlog/stream – streamt Python-Logging in den Browser."""
from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import deque
from collections.abc import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/devlog", tags=["devlog"])

# Ringpuffer: letzte 200 Zeilen für neue Verbindungen
_BUFFER: deque[dict] = deque(maxlen=200)
_SUBSCRIBERS: list[asyncio.Queue] = []
_LOOP: asyncio.AbstractEventLoop | None = None


def _broadcast(record: dict) -> None:
    _BUFFER.append(record)
    if _LOOP and _LOOP.is_running():
        for q in list(_SUBSCRIBERS):
            _LOOP.call_soon_threadsafe(q.put_nowait, record)


class _SseHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            entry = {
                "ts": time.strftime("%H:%M:%S", time.localtime(record.created)),
                "level": record.levelname,
                "name": record.name,
                "msg": self.format(record),
            }
            _broadcast(entry)
        except Exception:
            pass


_handler = _SseHandler()
_handler.setFormatter(logging.Formatter("%(name)s – %(message)s"))
_handler.setLevel(logging.DEBUG)


def setup(loop: asyncio.AbstractEventLoop) -> None:
    """Muss beim App-Start aufgerufen werden, um den Loop zu registrieren."""
    global _LOOP
    _LOOP = loop
    root = logging.getLogger()
    if _handler not in root.handlers:
        root.addHandler(_handler)
        root.setLevel(logging.DEBUG)


async def _event_stream() -> AsyncGenerator[str, None]:
    q: asyncio.Queue = asyncio.Queue()
    _SUBSCRIBERS.append(q)
    try:
        # Ringpuffer zuerst senden
        for entry in list(_BUFFER):
            yield f"data: {json.dumps(entry)}\n\n"
        # Live-Stream
        while True:
            try:
                entry = await asyncio.wait_for(q.get(), timeout=30.0)
                yield f"data: {json.dumps(entry)}\n\n"
            except asyncio.TimeoutError:
                yield ": keepalive\n\n"
    finally:
        _SUBSCRIBERS.remove(q)


@router.get("/stream")
async def stream_log() -> StreamingResponse:
    return StreamingResponse(
        _event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
