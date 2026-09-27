"""Export der Aufgaben als JSON- und CSV-Text (SPEC-0003 FR-06)."""
from __future__ import annotations

import csv
import io
import json

from todo.domain import Todo


def to_json(todos: list[Todo]) -> str:
    daten = [{"id": t.id, "title": t.title, "done": t.done, "tags": list(t.tags),
              "due": t.due.isoformat() if t.due else None} for t in todos]
    return json.dumps(daten, ensure_ascii=False, indent=2) + "\n"


def to_csv(todos: list[Todo]) -> str:
    puffer = io.StringIO()
    writer = csv.writer(puffer)
    writer.writerow(["id", "title", "done", "tags", "due"])
    for t in todos:
        writer.writerow([t.id, t.title, "true" if t.done else "false", ";".join(t.tags),
                         t.due.isoformat() if t.due else ""])
    return puffer.getvalue()
