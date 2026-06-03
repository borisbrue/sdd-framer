"""TaskRepository – Persistiert Tasks in .sdd/runs/{spec_id}/{run_id}/tasks.json.

Repository Pattern: kapselt alle File-I/O für Task-Zustand.
SPEC-0034 FR-03.
"""
from __future__ import annotations

import json
from pathlib import Path

from .task_model import Task


class TaskStore:
    def __init__(self, repo_root: Path) -> None:
        self._root = Path(repo_root)

    def _path(self, spec_id: str, run_id: str) -> Path:
        return self._root / ".sdd" / "runs" / spec_id / run_id / "tasks.json"

    def save(self, spec_id: str, run_id: str, tasks: list[Task]) -> None:
        p = self._path(spec_id, run_id)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            json.dumps([t.to_dict() for t in tasks], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def load(self, spec_id: str, run_id: str) -> list[Task]:
        p = self._path(spec_id, run_id)
        if not p.exists():
            return []
        data = json.loads(p.read_text(encoding="utf-8"))
        return [Task.from_dict(d) for d in data]

    def latest_run_id(self, spec_id: str) -> str | None:
        runs_dir = self._root / ".sdd" / "runs" / spec_id
        if not runs_dir.exists():
            return None
        run_dirs = sorted(
            (d for d in runs_dir.iterdir() if d.is_dir() and (d / "tasks.json").exists()),
            key=lambda d: d.name,
        )
        return run_dirs[-1].name if run_dirs else None

    def load_latest(self, spec_id: str) -> tuple[str | None, list[Task]]:
        run_id = self.latest_run_id(spec_id)
        if run_id is None:
            return None, []
        return run_id, self.load(spec_id, run_id)
