"""LogEventBus + LogStreamer für SPEC-0022 Live Container-Logs.

Observer Pattern:
  LogStreamer (docker logs --follow) → LogEventBus.publish()
    → [callback-1, callback-2, …] (WebSocket-Clients via sdd_context)
"""
from __future__ import annotations

import collections
import datetime
import json
import threading
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .dev_container import ContainerRuntime

_MAX_MSG_BYTES = 4096


def _make_msg(spec_id: str, line: str, *, buffered: bool = False) -> str:
    now = datetime.datetime.now(datetime.timezone.utc)
    ts = now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"
    payload: dict = {"ts": ts, "line": line, "spec_id": spec_id, "buffered": buffered}
    msg = json.dumps(payload)
    if len(msg.encode()) > _MAX_MSG_BYTES:
        # truncate line to fit within limit
        overhead = len(json.dumps({**payload, "line": "", "truncated": True}).encode())
        allowed = _MAX_MSG_BYTES - overhead
        payload["line"] = line.encode()[:allowed].decode(errors="replace")
        payload["truncated"] = True
        msg = json.dumps(payload)
    return msg


class LogEventBus:
    def __init__(self, max_lines: int = 500) -> None:
        self._max_lines = max_lines
        self._buffers: dict[str, collections.deque] = {}
        self._subscribers: dict[str, list[Callable[[str], None]]] = {}
        self._active_streams: set[str] = set()
        self._lock = threading.Lock()

    def subscribe(self, spec_id: str, callback: Callable[[str], None]) -> None:
        with self._lock:
            self._subscribers.setdefault(spec_id, []).append(callback)

    def unsubscribe(self, spec_id: str, callback: Callable[[str], None]) -> None:
        with self._lock:
            subs = self._subscribers.get(spec_id, [])
            try:
                subs.remove(callback)
            except ValueError:
                pass

    def publish(self, spec_id: str, line: str) -> None:
        msg = _make_msg(spec_id, line, buffered=False)
        with self._lock:
            buf = self._buffers.setdefault(
                spec_id, collections.deque(maxlen=self._max_lines)
            )
            buf.append(msg)
            subs = list(self._subscribers.get(spec_id, []))
        for cb in subs:
            try:
                cb(msg)
            except Exception:
                pass

    def get_buffer(self, spec_id: str) -> list[str]:
        with self._lock:
            return list(self._buffers.get(spec_id, []))

    def clear_buffer(self, spec_id: str) -> None:
        with self._lock:
            if spec_id in self._buffers:
                self._buffers[spec_id].clear()

    def mark_active(self, spec_id: str) -> None:
        with self._lock:
            self._active_streams.add(spec_id)

    def mark_inactive(self, spec_id: str) -> None:
        with self._lock:
            self._active_streams.discard(spec_id)

    def has_stream(self, spec_id: str) -> bool:
        with self._lock:
            return spec_id in self._active_streams


class LogStreamer:
    def __init__(self, bus: LogEventBus, runtime: ContainerRuntime) -> None:
        self._bus = bus
        self._runtime = runtime
        self._threads: dict[str, threading.Thread] = {}
        self._stop_events: dict[str, threading.Event] = {}

    def attach(self, spec_id: str, container_name: str) -> None:
        if spec_id in self._threads and self._threads[spec_id].is_alive():
            return
        stop_event = threading.Event()
        self._stop_events[spec_id] = stop_event
        t = threading.Thread(
            target=self._stream,
            args=(spec_id, container_name, stop_event),
            daemon=True,
            name=f"log-{spec_id}",
        )
        self._threads[spec_id] = t
        self._bus.mark_active(spec_id)
        t.start()

    def detach(self, spec_id: str) -> None:
        if spec_id in self._stop_events:
            self._stop_events[spec_id].set()
        t = self._threads.pop(spec_id, None)
        if t is not None:
            t.join(timeout=5.0)
        self._stop_events.pop(spec_id, None)
        self._bus.mark_inactive(spec_id)

    def _stream(
        self, spec_id: str, cname: str, stop: threading.Event
    ) -> None:
        proc = self._runtime.logs_popen(cname)
        try:
            while not stop.is_set():
                line = proc.stdout.readline()
                if not line:
                    break
                self._bus.publish(spec_id, line.rstrip("\n"))
        finally:
            proc.terminate()
            proc.wait()
