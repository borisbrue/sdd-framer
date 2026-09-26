"""Leseschnittstelle für Pipeline-Runs (SPEC-0058 FR-05, CON-0211).

Die Web-Schicht liest Runs nur hierüber, nie direkt aus `.sdd/runs/` (ADR-0003). Ereignisse eines
Tasks werden auf das `DagEvent`-Format abgebildet, das der Monitor der Web-UI seit SPEC-0037
erwartet (Adapter).
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .store import RunNotFound, RunStore

# CON-0211 INV-01: Status aus state.json → Status der Runs-Liste
RUN_STATUS = {"running": "running", "awaiting_supervisor": "paused",
              "awaiting_session": "paused", "completed": "done", "halted": "failed",
              "failed": "failed"}
CLOUD_PROVIDERS = ("claude-cli", "anthropic")


def _zeit(wert: str | None) -> float:
    if not wert:
        return 0.0
    try:
        return datetime.fromisoformat(wert.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def list_runs(root: Path) -> list[dict]:
    """Alle Runs des Projekts, neuester zuerst (CON-0211 INV-01)."""
    basis = root / ".sdd" / "runs"
    runs = []
    for state_datei in basis.glob("*/*/state.json") if basis.is_dir() else []:
        run_dir = state_datei.parent
        try:
            state = json.loads(state_datei.read_text(encoding="utf-8"))
            run = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        runs.append({"run_id": run_dir.name, "spec_id": run.get("spec_id", run_dir.parent.name),
                     "status": RUN_STATUS.get(state.get("status", ""), "running"),
                     "started_at": _zeit(run.get("started_at"))})
    return sorted(runs, key=lambda r: (r["started_at"], r["run_id"]), reverse=True)


def is_active(root: Path, run_id: str) -> bool:
    """Ob der Run noch läuft (dann kommen weitere Ereignisse)."""
    return RunStore.open(root, run_id).read_state().get("status") == "running"


def _dag_status(ereignis: dict) -> str:
    if ereignis["type"] == "transition":
        ziel = ereignis.get("to")
        if ziel == "pending":
            return "pending"
        if ziel == "done":
            return "done"
        if ziel == "halted":
            return "failed"
    return "running"


def _details(ereignis: dict) -> str:
    detail = ereignis.get("detail") or {}
    if ereignis["type"] == "role_call":
        return f"{ereignis.get('role')}: {ereignis.get('outcome')} (Versuch {ereignis.get('attempt')})"
    if ereignis["type"] == "write_rejected":
        return f"Schreibzugriff abgelehnt: {detail.get('path')} ({detail.get('reason')})"
    grund = f" – {detail['reason']}" if detail.get("reason") else ""
    return f"{ereignis.get('from', '?')} → {ereignis.get('to', '?')}{grund}"


def _als_dag_event(run_id: str, ereignis: dict, roles: dict) -> dict:
    detail = ereignis.get("detail") or {}
    provider = detail.get("provider") or (roles.get(ereignis.get("role") or "") or {}).get(
        "provider")
    agent = "none" if not provider else ("cloud" if provider in CLOUD_PROVIDERS else "local")
    return {"run_id": run_id, "task_id": ereignis["task_id"], "status": _dag_status(ereignis),
            "agent": agent, "model": str(detail.get("model") or ""),
            "timestamp": ereignis.get("ts", ""), "details": _details(ereignis)}


def task_events(root: Path, run_id: str, offset: int = 0) -> tuple[list[dict], int]:
    """Task-Ereignisse ab Zeile `offset` von events.jsonl im DagEvent-Format (CON-0211 INV-02/03).

    Gibt die Ereignisse und den neuen Offset (Anzahl gelesener Zeilen) zurück.
    """
    store = RunStore.open(root, run_id)
    try:
        roles = store.read_run().get("roles", {})
    except (OSError, json.JSONDecodeError):
        roles = {}
    zeilen = store.read_jsonl("events.jsonl")
    neu = [e for e in zeilen[offset:] if e.get("task_id")]
    return [_als_dag_event(run_id, e, roles) for e in neu], len(zeilen)


def status(root: Path, run_id: str) -> dict:
    """Zustand und offene Anfrage eines Runs (für `sdd pipeline status --json`, CON-0211 INV-06)."""
    store = RunStore.open(root, run_id)
    state = store.read_state()
    offen = store.read_pending() if state.get("pending_request_id") else None
    auftrag = store.read_work() if state.get("status") == "awaiting_session" else None
    return {"run_id": run_id, "spec_id": store.spec_id, "status": state.get("status"),
            "phase": state.get("phase"), "tasks": state.get("tasks", []),
            "pending_request": offen, "pending_work": auftrag}


__all__ = ["RunNotFound", "is_active", "list_runs", "status", "task_events"]
