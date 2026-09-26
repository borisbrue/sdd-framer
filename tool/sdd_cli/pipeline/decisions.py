"""Supervisor-Entscheidungen als Commands (SPEC-0053 FR-08, FR-15, CON-0201).

Eine `DecisionSource` liefert zu einer Anfrage entweder ein Command (dict) oder `Pending`.
`inline` fragt die Supervisor-Rolle über ihren Provider, `session` meldet `Pending`; die Antwort
kommt dann über `sdd pipeline decide`. Validierung, Ausführung und Protokoll sind für beide
Quellen identisch (CON-0205 INV-04).
"""
from __future__ import annotations

import json
import secrets
from dataclasses import dataclass
from typing import Any, Protocol

from .schemas import errors as schema_errors
from .store import now

ALLOWED = {
    "S1": ("approve", "revise", "halt"),
    "S2": ("retry_with_hint", "reassign", "redecompose", "halt"),
    "S3": ("accept_frs", "reopen", "halt"),  # reopen: SPEC-0061 FR-09
}


def new_request(point: str, facts: dict, task_id: str | None = None) -> dict:
    request = {"request_id": f"req-{secrets.token_hex(4)}", "point": point, "created_at": now(),
               "allowed_commands": list(ALLOWED[point]),
               "facts": {"gate_results": [], **facts}}
    if task_id:
        request["task_id"] = task_id
    return request


def validate_command(command: Any, request: dict, task_ids: set[str] | None = None) -> list[str]:
    """Fehler eines Commands gegenüber Schema (CON-0201), offener Anfrage und Tasks des Runs."""
    if not isinstance(command, dict):
        return ["Command ist kein JSON-Objekt"]
    fehler = schema_errors("supervisor-decision", command)
    if fehler:
        return ["Command verletzt CON-0201"]
    if command["point"] != request["point"]:
        return [f"Anfrage ist {request['point']}, Command nennt {command['point']}"]
    if command["command"] not in request["allowed_commands"]:
        return [f"{command['command']} ist an {request['point']} nicht erlaubt"]
    task_id = command.get("task_id")
    if task_id is not None and task_id != request.get("task_id"):
        return [f"task_id {task_id} passt nicht zur Anfrage ({request.get('task_id')})"]
    if task_ids is not None:
        unbekannt = [t for t in command.get("task_ids", []) if t not in task_ids]
        if unbekannt:
            return [f"unbekannte Tasks: {', '.join(unbekannt)}"]
    return []


def parse_command(text: str) -> Any:
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None


@dataclass(frozen=True)
class Pending:
    request: dict


@dataclass(frozen=True)
class Answer:
    command: Any  # dict bei gültiger Syntax, sonst Rohwert
    raw: str = ""
    call_id: str | None = None
    outcome: str = "ok"


class DecisionSource(Protocol):
    name: str

    def decide(self, request: dict, *, attempt: int) -> Answer | Pending: ...


class SessionSource:
    """Claude Code im Dialog: jede Anfrage wartet auf `sdd pipeline decide` (FR-15)."""

    name = "session"

    def decide(self, request: dict, *, attempt: int) -> Answer | Pending:
        return Pending(request)
