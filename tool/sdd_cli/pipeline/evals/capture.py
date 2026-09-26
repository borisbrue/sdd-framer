"""Fall aus einem Pipeline-Run (SPEC-0055 FR-09, CON-0219 INV-06).

Liest den Run über `store` (Run-Verzeichnis nach CON-0202). Eine Request-ID ergibt einen
Supervisor-Fall mit `decision_matches`, eine Task-ID den Fall der Rolle des letzten gescheiterten
Aufrufs mit den gescheiterten Checks. Der Fall ist ein Entwurf (`draft: true`).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from ..checks import GATE, REGISTRY
from ..context import ContextError, ProjectContext
from ..store import RunNotFound, RunStore
from .cases import Case, new_case, role_home

if TYPE_CHECKING:
    from ...config import SddConfig


class CaptureError(Exception):
    """Run oder Element unbekannt oder ohne verwertbaren Fehlschlag."""


def _spec_inputs(root: Path, spec_id: str) -> dict[str, str]:
    try:
        ctx = ProjectContext(root, spec_id)
        return {"spec.md": ctx.spec_text, "contracts.md": ctx.contracts_text}
    except ContextError:
        return {}


def _request(store: RunStore, request_id: str) -> dict | None:
    archiv = store.dir / "requests" / f"{request_id}.json"
    if archiv.is_file():
        return json.loads(archiv.read_text(encoding="utf-8"))
    offen = store.read_pending()
    return offen if offen and offen.get("request_id") == request_id else None


def capture(config: SddConfig, run_id: str, element_id: str) -> Case:
    try:
        store = RunStore.open(config.root, run_id)
    except RunNotFound as exc:
        raise CaptureError(str(exc)) from exc
    if element_id.startswith("req-"):
        return _capture_decision(config, store, element_id)
    return _capture_task(config, store, element_id)


def _capture_decision(config: SddConfig, store: RunStore, request_id: str) -> Case:
    anfrage = _request(store, request_id)
    if anfrage is None:
        raise CaptureError(f"Anfrage {request_id} gibt es in {store.run_id} nicht")
    entscheidungen = [d for d in store.read_jsonl("decisions.jsonl")
                      if d.get("request_id") == request_id]
    befehl = (entscheidungen[-1].get("command") if entscheidungen else None) or {}
    erwartet = {k: befehl[k] for k in ("point", "command") if k in befehl} or {
        "point": anfrage["point"]}
    inputs = {"request.json": json.dumps(anfrage, ensure_ascii=False, indent=2),
              **_spec_inputs(config.root, store.spec_id)}
    fall = new_case(role_home(config.root, "supervisor"),
                    f"captured {store.run_id} {request_id}", holdout=False, inputs=inputs,
                    data={"origin": f"captured:{store.run_id}",
                          "description": f"Entscheidung {anfrage['point']} aus {store.run_id}; "
                                         f"getroffen: {befehl.get('command', '?')}. Erwartung "
                                         f"in expected/decision.json prüfen.",
                          "expect": {"checks": [{"json_schema": {}}, {"decision_matches": {}}]}})
    (fall.dir / "expected").mkdir()
    (fall.dir / "expected" / "decision.json").write_text(
        json.dumps(erwartet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return fall


def _capture_task(config: SddConfig, store: RunStore, task_id: str) -> Case:
    aufrufe = [e for e in store.read_jsonl("events.jsonl")
               if e.get("type") == "role_call" and e.get("task_id") == task_id
               and e.get("outcome") not in (None, "ok")]
    if not aufrufe:
        raise CaptureError(f"Task {task_id} hat in {store.run_id} keinen gescheiterten Aufruf")
    letzter = aufrufe[-1]
    rolle = letzter["role"]
    detail = letzter.get("detail") or {}
    checks = ["json_schema", *[c for c in detail.get("failed_checks", [])
                                if c != "json_schema" and c in REGISTRY
                                and GATE in REGISTRY[c].contexts]]
    from ...decompose import TaskDecomposer

    tasks = {t.id: t.to_dict() for t in TaskDecomposer().load(store.spec_id, config)}
    task = tasks.get(task_id)
    if task is None:
        raise CaptureError(f"Task {task_id} fehlt in .sdd/tasks/{store.spec_id}.json")
    inputs = {"task.json": json.dumps(task, ensure_ascii=False, indent=2),
              **_spec_inputs(config.root, store.spec_id)}
    probleme = "; ".join(detail.get("problems", [])[:5])
    return new_case(role_home(config.root, rolle), f"captured {store.run_id} {task_id}",
                    holdout=False, inputs=inputs,
                    data={"origin": f"captured:{store.run_id}",
                          "description": f"{rolle} scheiterte an {task_id} "
                                         f"({letzter.get('outcome')}): {probleme}",
                          "expect": {"checks": [{c: {}} for c in dict.fromkeys(checks)]}})
