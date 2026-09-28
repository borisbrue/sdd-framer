"""Fakten der Abnahme S3 mit Tasks und FR-Zuordnung (SPEC-0064, CON-0230, CON-0202).

Quelle sind zwei Schnappschüsse des Runs (Memento): `approved-tasks.json` aus der S1-Freigabe und
die Tasks in `state.json`. `s3_task` bildet beide auf das Format `$defs/s3_task` ab (Adapter) und
übernimmt nur die Felder aus `FIELDS` (Proxy als Allowlist). `S3FactsBuilder` setzt die Fakten in
fester Reihenfolge zusammen: erst `tasks`, daraus `frs[].tasks` (Builder).
"""
from __future__ import annotations

from typing import Any

from .store import APPROVED_TASKS

FIELDS = ("id", "title", "fr_ids", "test_file", "state", "attempts")


class SnapshotMissing(Exception):
    """`approved-tasks.json` fehlt oder deckt nicht alle Tasks aus `state.json` ab (FR-04)."""


def s3_task(definition: dict, laufzustand: dict) -> dict:
    """Task-Definition + Laufzustand → `$defs/s3_task`, genau die Felder aus FIELDS."""
    eintrag = {
        "id": laufzustand["task_id"],
        "title": str(definition.get("title") or ""),
        "fr_ids": list(definition.get("fr_ids") or []),
        "test_file": definition.get("test_file") or None,
        "state": laufzustand["state"],
        "attempts": int(laufzustand.get("attempts", 0)),
    }
    return {feld: eintrag[feld] for feld in FIELDS}


class S3FactsBuilder:
    def __init__(self) -> None:
        self._facts: dict[str, Any] = {}

    def tasks(self, snapshot: dict | None, state_tasks: list[dict]) -> S3FactsBuilder:
        if snapshot is None:
            raise SnapshotMissing(f"{APPROVED_TASKS} fehlt im Run-Verzeichnis")
        definitionen = {t.get("id"): t for t in snapshot.get("tasks") or []
                        if isinstance(t, dict)}
        fehlend = [st["task_id"] for st in state_tasks if st["task_id"] not in definitionen]
        if fehlend:
            raise SnapshotMissing(f"{APPROVED_TASKS} enthält die Tasks {', '.join(fehlend)} "
                                  "aus state.json nicht")
        self._facts["tasks"] = [s3_task(definitionen[st["task_id"]], st) for st in state_tasks]
        return self

    def frs(self, fr_status: list[dict]) -> S3FactsBuilder:
        if "tasks" not in self._facts:
            raise RuntimeError("frs() braucht zuerst tasks()")
        self._facts["frs"] = [
            {**fr, "tasks": [t["id"] for t in self._facts["tasks"] if fr["id"] in t["fr_ids"]]}
            for fr in fr_status]
        return self

    def gate_results(self, ergebnisse: list[dict]) -> S3FactsBuilder:
        self._facts["gate_results"] = list(ergebnisse)
        return self

    def holdout(self, fakten: dict) -> S3FactsBuilder:
        self._facts["holdout"] = fakten
        return self

    def build(self) -> dict:
        fehlend = [k for k in ("tasks", "frs", "gate_results") if k not in self._facts]
        if fehlend:
            raise RuntimeError(f"S3-Fakten unvollständig: {', '.join(fehlend)}")
        return dict(self._facts)
