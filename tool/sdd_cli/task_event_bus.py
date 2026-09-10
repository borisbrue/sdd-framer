"""TaskEventBus – Observer/Pub-Sub für Task-Statuswechsel (SPEC-0034 FR-02/FR-04).

Observer Pattern: Subscriber registrieren sich für task_update-Events.
Entkoppelt TaskLifecycle von SSE-Transport – neue Subscriber ohne OCP-Verletzung.
"""
from __future__ import annotations

import asyncio
import datetime
from collections.abc import AsyncIterator


class TaskEventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[asyncio.Queue]] = {}

    def _now(self) -> str:
        return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def publish(self, spec_id: str, run_id: str, task_dict: dict) -> None:
        event = {
            "run_id": run_id,
            "timestamp": self._now(),
            "task": task_dict,
        }
        for queue in self._subscribers.get(spec_id, []):
            try:
                queue.put_nowait(("task_update", event))
            except asyncio.QueueFull:
                pass

    def publish_run_started(self, spec_id: str, run_id: str) -> None:
        event = {"run_id": run_id, "spec_id": spec_id, "timestamp": self._now()}
        for queue in self._subscribers.get(spec_id, []):
            try:
                queue.put_nowait(("run_started", event))
            except asyncio.QueueFull:
                pass

    def publish_run_completed(self, spec_id: str, run_id: str) -> None:
        event = {"run_id": run_id, "spec_id": spec_id, "timestamp": self._now()}
        for queue in self._subscribers.get(spec_id, []):
            try:
                queue.put_nowait(("run_completed", event))
            except asyncio.QueueFull:
                pass

    def subscribe(self, spec_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._subscribers.setdefault(spec_id, []).append(queue)
        return queue

    def unsubscribe(self, spec_id: str, queue: asyncio.Queue) -> None:
        subscribers = self._subscribers.get(spec_id, [])
        if queue in subscribers:
            subscribers.remove(queue)

    async def stream(self, spec_id: str) -> AsyncIterator[tuple[str, dict]]:
        queue = self.subscribe(spec_id)
        try:
            while True:
                event_type, payload = await queue.get()
                yield event_type, payload
        finally:
            self.unsubscribe(spec_id, queue)


_bus: TaskEventBus | None = None


def get_task_event_bus() -> TaskEventBus:
    global _bus
    if _bus is None:
        _bus = TaskEventBus()
    return _bus
