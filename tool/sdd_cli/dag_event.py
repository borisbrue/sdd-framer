"""DagEvent-Schema und DagEventBus für SPEC-0037 Agent-DAG-Monitor.

Observer Pattern (CON-0130/CON-0131): DagScheduler publiziert, SSE-Handler subscribiert.
run_id-Isolation: jeder Run hat seine eigene asyncio.Queue.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import AsyncIterator, Literal

from pydantic import BaseModel, Field


class DagEvent(BaseModel):
    run_id: str
    task_id: str
    status: Literal["pending", "running", "done", "failed", "skipped", "paused"]
    agent: Literal["local", "cloud", "none"] = "none"
    model: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    details: str = ""


class EscalationEvent(DagEvent):
    """Sonderfall: Autopilot-Eskalation (FR-10). status ist immer 'failed'."""
    phase: str = ""
    iteration: int = 0
    reason: str = ""
    options: list[str] = Field(default_factory=lambda: ["retry", "skip", "abort"])


_SENTINEL = object()
_QUEUE_MAXSIZE = 256


class DagEventBus:
    """Pub/Sub-Bus mit run_id-isolierten asyncio.Queues (CON-0130).

    Thread-sicher für publish() aus Threads (ThreadPoolExecutor in DagScheduler).
    subscribe() läuft im asyncio-Event-Loop des SSE-Handlers.
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, list[asyncio.Queue]] = {}
        self._loop: asyncio.AbstractEventLoop | None = None

    def _get_loop(self) -> asyncio.AbstractEventLoop:
        if self._loop is None or self._loop.is_closed():
            try:
                self._loop = asyncio.get_event_loop()
            except RuntimeError:
                self._loop = asyncio.new_event_loop()
        return self._loop

    def publish(self, event: DagEvent) -> None:
        """Thread-safe publish. Kann aus Thread oder Coroutine aufgerufen werden."""
        queues = self._subscribers.get(event.run_id, [])
        for q in queues:
            try:
                loop = self._get_loop()
                if loop.is_running():
                    loop.call_soon_threadsafe(q.put_nowait, event)
                else:
                    q.put_nowait(event)
            except asyncio.QueueFull:
                pass

    async def subscribe(self, run_id: str) -> AsyncIterator[DagEvent]:
        """Async-Generator: liefert Events für einen run_id bis close() gerufen wird."""
        q: asyncio.Queue = asyncio.Queue(maxsize=_QUEUE_MAXSIZE)
        self._subscribers.setdefault(run_id, []).append(q)
        try:
            while True:
                item = await q.get()
                if item is _SENTINEL:
                    return
                yield item
        finally:
            subs = self._subscribers.get(run_id, [])
            if q in subs:
                subs.remove(q)
            if not subs:
                self._subscribers.pop(run_id, None)

    def close(self, run_id: str) -> None:
        """Signalisiert allen Subscribern des run_id das Ende."""
        for q in self._subscribers.get(run_id, []):
            try:
                q.put_nowait(_SENTINEL)
            except asyncio.QueueFull:
                pass

    def has_subscribers(self, run_id: str) -> bool:
        return bool(self._subscribers.get(run_id))


# Prozess-weiter Singleton — DagScheduler und SSE-Handler teilen dieselbe Instanz.
_bus: DagEventBus | None = None


def get_event_bus() -> DagEventBus:
    global _bus
    if _bus is None:
        _bus = DagEventBus()
    return _bus
