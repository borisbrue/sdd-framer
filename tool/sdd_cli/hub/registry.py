from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml

from .models import ProjectEntry

def _default_registry_path() -> Path:
    return Path.home() / ".config" / "sdd" / "hub-registry.yaml"


class DuplicateProjectError(Exception):
    pass


class ProjectNotFoundError(Exception):
    pass


class ProjectRegistry:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or _default_registry_path()
        self._entries: dict[str, ProjectEntry] = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            data = yaml.safe_load(self._path.read_text()) or []
            for item in data:
                entry = ProjectEntry.model_validate(item)
                self._entries[entry.id] = entry

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            yaml.dump([e.model_dump(mode="json") for e in self._entries.values()])
        )

    def register(self, entry: ProjectEntry, force: bool = False) -> None:
        if entry.id in self._entries and not force:
            raise DuplicateProjectError(f"Project '{entry.id}' already registered. Use --force to overwrite.")
        self._entries[entry.id] = entry
        self._save()

    def get_all(self) -> list[ProjectEntry]:
        return list(self._entries.values())

    def get(self, project_id: str) -> ProjectEntry:
        if project_id not in self._entries:
            raise ProjectNotFoundError(f"Project '{project_id}' not found in registry.")
        return self._entries[project_id]

    def update_status(
        self,
        project_id: str,
        status: Literal["running", "stopped", "error"],
        pid: int | None = None,
    ) -> None:
        entry = self.get(project_id)
        updated = entry.model_copy(update={"status": status, "pid": pid})
        self._entries[project_id] = updated
        self._save()

    def remove(self, project_id: str) -> None:
        if project_id not in self._entries:
            raise ProjectNotFoundError(f"Project '{project_id}' not found.")
        del self._entries[project_id]
        self._save()
