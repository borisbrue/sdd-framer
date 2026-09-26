"""Run-Verzeichnis `.sdd/runs/<SPEC>/<run_id>/` (SPEC-0104).

`state.json` wird atomar geschrieben, `events.jsonl` nur angehängt.
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
    """`<SPEC-ID>-<YYYYMMDDTHHMMSS>-<suffix>` (FR-01)."""
    stempel = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    return f"{spec_id}-{stempel}-{secrets.token_hex(3)}"


class RunNotFound(Exception):
    """Der Run existiert nicht."""


def atomic_write_json(path: Path, data: Any) -> None:
    """Schreibt JSON über eine Temp-Datei und os.replace (FR-02)."""
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

    @classmethod
    def create(cls, root: Path, spec_id: str, run_id: str | None = None) -> RunStore:
        """Neuer Run (FR-03)."""
        if run_id is not None:
            treffer = RUN_ID_RE.match(run_id)
            if not treffer or treffer.group(1) != spec_id:
                raise ValueError(f"Run-ID {run_id!r} passt nicht zu {spec_id}.")
        store = cls(root, spec_id, run_id or new_run_id(spec_id))
        store.dir.mkdir(parents=True, exist_ok=False)
        return store

    @classmethod
    def open(cls, root: Path, run_id: str) -> RunStore:
        """Bestehender Run (FR-04)."""
        treffer = RUN_ID_RE.match(run_id)
        if not treffer:
            raise RunNotFound(f"Unbekannter Run: {run_id}")
        store = cls(root, treffer.group(1), run_id)
        if not (store.dir / "state.json").is_file():
            raise RunNotFound(f"Unbekannter Run: {run_id}")
        return store

    def write_state(self, state: dict) -> None:
        state["updated_at"] = now()
        atomic_write_json(self.dir / "state.json", state)

    def read_state(self) -> dict:
        return json.loads((self.dir / "state.json").read_text(encoding="utf-8"))

    def event(self, type_: str, **felder: Any) -> None:
        """Hängt ein Ereignis an events.jsonl an (FR-06)."""
        record = {"ts": now(), "run_id": self.run_id, "type": type_,
                  **{k: v for k, v in felder.items() if v is not None}}
        self.dir.mkdir(parents=True, exist_ok=True)
        with (self.dir / "events.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    def read_jsonl(self, name: str) -> list[dict]:
        pfad = self.dir / name
        if not pfad.is_file():
            return []
        return [json.loads(z) for z in pfad.read_text(encoding="utf-8").splitlines() if z.strip()]
