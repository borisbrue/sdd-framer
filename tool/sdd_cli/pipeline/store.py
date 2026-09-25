"""Run-Verzeichnis `.sdd/runs/<SPEC>/<run_id>/` (SPEC-0053 FR-12, CON-0202).

`state.json` wird nach jedem Übergang atomar geschrieben (INV-01), `events.jsonl` und
`decisions.jsonl` nur angehängt (INV-04). Offene Entscheidungen liegen in
`pending-decision.json`; beantwortete wandern nach `requests/<request_id>.json` (INV-02).
Keine Datei enthält Prompts, Antworten oder API-Keys (INV-05).
"""
from __future__ import annotations

import json
import os
import re
import secrets
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RUN_ID_RE = re.compile(r"^(SPEC-\d{4})-\d{8}T\d{6}-[0-9a-z]+$")


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_run_id(spec_id: str) -> str:
    """`<SPEC-ID>-<YYYYMMDDTHHMMSS>-<suffix>` (CON-0202 INV-07)."""
    stempel = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    return f"{spec_id}-{stempel}-{secrets.token_hex(3)}"


class RunNotFound(Exception):
    """Der Run existiert nicht."""


def _atomic_write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


class RunStore:
    def __init__(self, root: Path, spec_id: str, run_id: str) -> None:
        self.root = root
        self.spec_id = spec_id
        self.run_id = run_id
        self.dir = root / ".sdd" / "runs" / spec_id / run_id

    # ── Anlegen und Finden ──
    @classmethod
    def create(cls, root: Path, spec_id: str) -> RunStore:
        store = cls(root, spec_id, new_run_id(spec_id))
        store.dir.mkdir(parents=True, exist_ok=False)
        return store

    @classmethod
    def open(cls, root: Path, run_id: str) -> RunStore:
        treffer = RUN_ID_RE.match(run_id)
        if not treffer:
            raise RunNotFound(f"Unbekannter Run: {run_id}")
        store = cls(root, treffer.group(1), run_id)
        if not (store.dir / "state.json").is_file():
            raise RunNotFound(f"Unbekannter Run: {run_id}")
        return store

    # ── Dateien ──
    def write_run(self, data: dict) -> None:
        _atomic_write(self.dir / "run.json", data)

    def read_run(self) -> dict:
        return json.loads((self.dir / "run.json").read_text(encoding="utf-8"))

    def write_state(self, state: dict) -> None:
        state["updated_at"] = now()
        _atomic_write(self.dir / "state.json", state)

    def read_state(self) -> dict:
        return json.loads((self.dir / "state.json").read_text(encoding="utf-8"))

    def _append(self, name: str, record: dict) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        with (self.dir / name).open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    def event(self, type_: str, **felder: Any) -> None:
        self._append("events.jsonl", {"ts": now(), "run_id": self.run_id, "type": type_,
                                      **{k: v for k, v in felder.items() if v is not None}})

    def decision(self, record: dict) -> None:
        self._append("decisions.jsonl", {"ts": now(), **record})

    def read_jsonl(self, name: str) -> list[dict]:
        pfad = self.dir / name
        if not pfad.is_file():
            return []
        return [json.loads(z) for z in pfad.read_text(encoding="utf-8").splitlines() if z.strip()]

    # ── Entscheidungsanfragen ──
    def write_pending(self, request: dict) -> None:
        _atomic_write(self.dir / "pending-decision.json", request)

    def read_pending(self) -> dict | None:
        pfad = self.dir / "pending-decision.json"
        return json.loads(pfad.read_text(encoding="utf-8")) if pfad.is_file() else None

    def archive_pending(self, request_id: str) -> None:
        pfad = self.dir / "pending-decision.json"
        if pfad.is_file():
            ziel = self.dir / "requests" / f"{request_id}.json"
            ziel.parent.mkdir(parents=True, exist_ok=True)
            os.replace(pfad, ziel)
