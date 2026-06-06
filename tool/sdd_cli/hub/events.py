from __future__ import annotations

import asyncio
from collections import defaultdict

from .models import StatusEvent


class StatusEventBus:
    def __init__(self) -> None:
        self._queues: dict[str, list[asyncio.Queue[StatusEvent | None]]] = defaultdict(list)

    def publish(self, event: StatusEvent) -> None:
        for q in self._queues[event.id]:
            q.put_nowait(event)

    async def subscribe(self, project_id: str):
        q: asyncio.Queue[StatusEvent | None] = asyncio.Queue()
        self._queues[project_id].append(q)
        try:
            while True:
                item = await q.get()
                if item is None:
                    break
                yield item
        finally:
            self._queues[project_id].remove(q)

    def close(self, project_id: str) -> None:
        for q in self._queues[project_id]:
            q.put_nowait(None)
