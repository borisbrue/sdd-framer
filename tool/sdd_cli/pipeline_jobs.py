"""Job-Status-Tracking für laufende Pipeline-Aktionen (FR-11 SPEC-0028).

Schreibt/liest .sdd/pipeline/{spec_id}-job.json.
Das Frontend pollt GET /api/specs/{id}/job für Fortschrittsupdates.
"""
from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import SddConfig


@dataclass
class JobStatus:
    spec_id: str
    command: str
    status: str  # "running" | "done" | "failed"
    started_at: str
    output: str = ""
    finished_at: str | None = None
    result: dict[str, Any] | None = None


class JobManager:
    _lock = threading.Lock()

    def __init__(self, cfg: SddConfig) -> None:
        self._dir = cfg.sdd_dir / "pipeline"

    def _path(self, spec_id: str) -> Path:
        return self._dir / f"{spec_id}-job.json"

    def start(self, spec_id: str, command: str) -> JobStatus:
        job = JobStatus(
            spec_id=spec_id,
            command=command,
            status="running",
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        self._write(spec_id, job)
        return job

    def append(self, spec_id: str, line: str) -> None:
        with self._lock:
            job = self.get(spec_id)
            if job:
                job.output = (job.output + "\n" + line).lstrip("\n")
                self._write(spec_id, job)

    def finish(self, spec_id: str, *, ok: bool, result: dict[str, Any] | None = None) -> None:
        with self._lock:
            job = self.get(spec_id)
            if job:
                job.status = "done" if ok else "failed"
                job.finished_at = datetime.now(timezone.utc).isoformat()
                job.result = result
                self._write(spec_id, job)

    def get(self, spec_id: str) -> JobStatus | None:
        p = self._path(spec_id)
        if not p.exists():
            return None
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            return JobStatus(**data)
        except Exception:
            return None

    def _write(self, spec_id: str, job: JobStatus) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        self._path(spec_id).write_text(
            json.dumps(asdict(job), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
