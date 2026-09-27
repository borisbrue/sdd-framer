"""JsonFileRepository: Zustand als JSON-Datei (SPEC-0002 FR-04/FR-05, SPEC-0003 FR-08)."""
from __future__ import annotations

import datetime as dt
import json
import os
import tempfile
from pathlib import Path

from todo.domain import StorageError, Todo


class JsonFileRepository:
    def __init__(self, path: str | os.PathLike[str]) -> None:
        self.path = Path(path)

    def load(self) -> tuple[int, list[Todo]]:
        if not self.path.exists():
            return 1, []
        try:
            daten = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise StorageError(f"{self.path}: nicht lesbar ({exc})") from exc
        return self._parse(daten)

    def _parse(self, daten: object) -> tuple[int, list[Todo]]:
        if not isinstance(daten, dict) or not isinstance(daten.get("todos"), list):
            raise StorageError(f"{self.path}: erwartet ein Objekt mit der Liste 'todos'")
        todos = [self._todo(e) for e in daten["todos"]]
        ids = [t.id for t in todos]
        if len(set(ids)) != len(ids):
            raise StorageError(f"{self.path}: doppelte IDs")
        next_id = daten.get("next_id", max(ids, default=0) + 1)
        if not _is_int(next_id):
            raise StorageError(f"{self.path}: 'next_id' ist keine ganze Zahl")
        return max(next_id, max(ids, default=0) + 1), sorted(todos, key=lambda t: t.id)

    def _todo(self, eintrag: object) -> Todo:
        if not isinstance(eintrag, dict):
            raise StorageError(f"{self.path}: Eintrag ist kein Objekt")
        tid, titel, done = eintrag.get("id"), eintrag.get("title"), eintrag.get("done", False)
        tags, due = eintrag.get("tags", []), eintrag.get("due")
        if not _is_int(tid) or not isinstance(titel, str) or not isinstance(done, bool):
            raise StorageError(f"{self.path}: Eintrag mit ungültigem id/title/done")
        if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
            raise StorageError(f"{self.path}: 'tags' von #{tid} ist keine Liste von Texten")
        try:
            datum = None if due is None else dt.date.fromisoformat(due)
        except (TypeError, ValueError) as exc:
            raise StorageError(f"{self.path}: ungültiges Datum {due!r} bei #{tid}") from exc
        return Todo(id=tid, title=titel, done=done, tags=tuple(sorted(set(tags))), due=datum)

    def save(self, next_id: int, todos: list[Todo]) -> None:
        daten = {"next_id": next_id, "todos": [
            {"id": t.id, "title": t.title, "done": t.done, "tags": list(t.tags),
             "due": t.due.isoformat() if t.due else None} for t in todos]}
        text = json.dumps(daten, ensure_ascii=False, indent=2) + "\n"
        verzeichnis = self.path.parent if str(self.path.parent) else Path(".")
        fd, tmp = tempfile.mkstemp(prefix=f".{self.path.name}.", dir=verzeichnis)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as datei:
                datei.write(text)
            os.replace(tmp, self.path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise


def _is_int(wert: object) -> bool:
    return isinstance(wert, int) and not isinstance(wert, bool)
