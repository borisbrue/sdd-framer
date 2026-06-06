from __future__ import annotations

import asyncio
import os
import signal
import subprocess
from datetime import datetime

from .events import StatusEventBus
from .models import ProjectEntry, StatusEvent
from .registry import ProjectRegistry


class ProcessManager:
    def __init__(self, registry: ProjectRegistry, event_bus: StatusEventBus) -> None:
        self._registry = registry
        self._bus = event_bus
        self._processes: dict[str, subprocess.Popen] = {}
        self._watch_task: asyncio.Task | None = None

    def start_watching(self) -> None:
        if self._watch_task is None or self._watch_task.done():
            self._watch_task = asyncio.create_task(self._watch_processes())

    def stop_watching(self) -> None:
        if self._watch_task and not self._watch_task.done():
            self._watch_task.cancel()

    def start(self, project_id: str) -> subprocess.Popen:
        entry = self._registry.get(project_id)
        if project_id in self._processes and self._processes[project_id].poll() is None:
            from fastapi import HTTPException
            raise HTTPException(status_code=409, detail=f"Project '{project_id}' is already running.")
        proc = subprocess.Popen(
            entry.start_cmd,
            cwd=str(entry.path),
            start_new_session=True,
        )
        self._processes[project_id] = proc
        now = datetime.utcnow()
        updated = entry.model_copy(update={"status": "running", "pid": proc.pid, "last_started": now})
        self._registry._entries[project_id] = updated
        self._registry._save()
        self._bus.publish(StatusEvent(id=project_id, status="running", pid=proc.pid))
        return proc

    def stop(self, project_id: str) -> None:
        entry = self._registry.get(project_id)
        proc = self._processes.get(project_id)
        if proc is None or proc.poll() is not None:
            from fastapi import HTTPException
            raise HTTPException(status_code=409, detail=f"Project '{project_id}' is not running.")
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            pass
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
            proc.wait()
        del self._processes[project_id]
        self._registry.update_status(project_id, "stopped", None)
        self._bus.publish(StatusEvent(id=project_id, status="stopped", pid=None))

    def get_live_status(self, project_id: str) -> tuple[str, int | None]:
        proc = self._processes.get(project_id)
        if proc is not None and proc.poll() is None:
            return "running", proc.pid
        return "stopped", None

    async def _watch_processes(self) -> None:
        while True:
            await asyncio.sleep(2)
            for project_id, proc in list(self._processes.items()):
                if proc.poll() is not None:
                    del self._processes[project_id]
                    self._registry.update_status(project_id, "error", None)
                    self._bus.publish(StatusEvent(id=project_id, status="error", pid=None))
