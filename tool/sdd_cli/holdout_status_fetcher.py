"""HoldoutStatusFetcher – SSE-basierte Status-Abfrage (SPEC-0043, Strategy Pattern)."""
from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass


@dataclass
class HoldoutStatusEvent:
    spec_id: str
    status: str
    updated_at: str | None = None


class HoldoutStatusFetcher:
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        backoff_delays: list[float] | None = None,
    ) -> None:
        self.base_url = base_url
        self._backoff_delays = backoff_delays

    @staticmethod
    def parse_event(raw: str) -> HoldoutStatusEvent | None:
        if not raw:
            return None
        try:
            data = json.loads(raw)
            return HoldoutStatusEvent(
                spec_id=data["spec_id"],
                status=data["status"],
                updated_at=data.get("updated_at"),
            )
        except (json.JSONDecodeError, KeyError, TypeError):
            return None

    def get_backoff_delays(self, attempts: int) -> list[float]:
        if self._backoff_delays is not None:
            return list(self._backoff_delays[:attempts])
        return [2.0 ** i for i in range(attempts)]

    def _open_sse_connection(self, url: str):
        import urllib.request
        return urllib.request.urlopen(url)

    async def fetch(
        self,
        spec_id: str,
        max_retries: int = 3,
    ) -> AsyncIterator[HoldoutStatusEvent]:
        url = f"{self.base_url}/api/holdouts/{spec_id}/stream"
        delays = self.get_backoff_delays(max_retries)
        for attempt in range(max_retries):
            try:
                conn = self._open_sse_connection(url)
                try:
                    for line in conn:
                        text = line.decode("utf-8").strip() if isinstance(line, bytes) else line.strip()
                        if text.startswith("data:"):
                            payload = text[5:].strip()
                            evt = HoldoutStatusFetcher.parse_event(payload)
                            if evt is not None:
                                yield evt
                finally:
                    conn.close()
                return
            except ConnectionError:
                yield HoldoutStatusEvent(spec_id=spec_id, status="unknown")
                if attempt < max_retries - 1 and attempt < len(delays):
                    await asyncio.sleep(delays[attempt])
