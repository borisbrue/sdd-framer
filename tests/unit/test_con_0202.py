"""TST-0231 – CON-0202: Run-Verzeichnis (run.json, state.json, events, decisions, Anfragen).

Spec: SPEC-0053 · Contract: CON-0202
"""
from __future__ import annotations

from tests.support.quality_project import def_errors

TS = "2026-09-25T10:15:03Z"
STATE = {"run_id": "20260925-101500-a1", "status": "awaiting_supervisor", "phase": "decompose",
         "revisions": 0, "tasks": [], "pending_request_id": "req-1", "updated_at": TS}


def test_tc01_valid_instance_passes():
    """Valide Instanzen aller fünf Dateiarten (CON-0202)."""
    assert def_errors("pipeline_run", "run", {
        "run_id": "r1", "spec_id": "SPEC-0900", "started_at": TS, "sdd_version": "0.1.63",
        "roles": {"decomposer": {"provider": "openai-compat", "model": "q", "role_version": "1.0.0"},
                  "supervisor": {"mode": "session", "role_version": "1.0.0"}},
        "warnings": ["Modell reviewt seine eigene Arbeit"]}) == []
    assert def_errors("pipeline_run", "state", STATE) == []
    assert def_errors("pipeline_run", "event", {"ts": TS, "run_id": "r1", "type": "write_rejected",
                                                "role": "implementer", "detail": {}}) == []
    assert def_errors("pipeline_run", "decision", {
        "ts": TS, "request_id": "req-1", "point": "S1", "source": "session", "valid": True,
        "command": {"point": "S1", "command": "approve", "reason": "ok"}}) == []
    assert def_errors("pipeline_run", "pending_decision", {
        "request_id": "req-1", "point": "S1", "created_at": TS,
        "allowed_commands": ["approve", "revise", "halt"], "facts": {"gate_results": []}}) == []


def test_tc02_invalid_instance_rejected():
    """Beispiel aus dem Contract: unbekannter Status, updated_at fehlt."""
    assert def_errors("pipeline_run", "state", {"run_id": "r", "status": "waiting",
                                                "phase": "decompose", "tasks": []})


def test_inv02_entscheidung_nennt_request_id():
    assert def_errors("pipeline_run", "decision", {
        "ts": TS, "point": "S1", "source": "inline", "valid": True, "command": {}})


def test_inv02_anfrage_braucht_request_id_und_commands():
    assert def_errors("pipeline_run", "pending_decision", {
        "point": "S1", "created_at": TS, "allowed_commands": ["approve"], "facts": {"gate_results": []}})
    assert def_errors("pipeline_run", "pending_decision", {
        "request_id": "r", "point": "S1", "created_at": TS, "allowed_commands": [],
        "facts": {"gate_results": []}})


def test_task_zustaende_geschlossen():
    assert def_errors("pipeline_run", "state", {**STATE, "tasks": [
        {"task_id": "t", "state": "irgendwo", "attempts": 0}]})


def test_inv05_keine_klartext_felder():
    assert def_errors("pipeline_run", "event", {"ts": TS, "run_id": "r", "type": "role_call",
                                                "prompt": "geheim"})


# ── SPEC-0064: S3-Fakten mit Tasks, Task-Schnappschuss (INV-10 bis INV-12) ─────

S3_TASK = {"id": "T03", "title": "Rabatt ab 100 €", "fr_ids": ["FR-03"],
           "test_file": "tests/test_rabatt.py", "state": "done", "attempts": 1}
S3_FR = {"id": "FR-03", "status": "grün", "tests": ["tests/test_rabatt.py"], "tasks": ["T03"]}


def _s3(**facts) -> dict:
    return {"request_id": "req-3", "point": "S3", "created_at": TS,
            "allowed_commands": ["accept_frs", "reopen", "halt"],
            "facts": {"gate_results": [], "tasks": [S3_TASK], "frs": [S3_FR], **facts}}


def test_inv11_s3_anfrage_mit_reopen_und_task_fakten():
    """SPEC-0064 FR-05: reopen ist erlaubt; FR-02/FR-03: Tasks und Task-IDs je FR."""
    assert def_errors("pipeline_run", "pending_decision", _s3()) == []
    ohne_task = {**S3_TASK, "id": "T04", "fr_ids": [], "test_file": None}
    assert def_errors("pipeline_run", "pending_decision",
                      _s3(tasks=[S3_TASK, ohne_task], frs=[S3_FR, {**S3_FR, "id": "FR-04",
                                                               "tasks": []}])) == []


def test_inv11_s3_braucht_tasks_und_frs():
    for fehlt in ("tasks", "frs"):
        anfrage = _s3()
        del anfrage["facts"][fehlt]
        assert def_errors("pipeline_run", "pending_decision", anfrage), fehlt


def test_inv11_s1_bleibt_unveraendert():
    """An S1 hat facts.tasks die Form der Zerlegung, nicht s3_task."""
    assert def_errors("pipeline_run", "pending_decision", {
        "request_id": "req-1", "point": "S1", "created_at": TS,
        "allowed_commands": ["approve", "revise", "halt"],
        "facts": {"gate_results": [], "tasks": [{"title": "x", "description": "y"}]}}) == []


def test_inv12_s3_task_nur_allowlist_felder():
    assert def_errors("pipeline_run", "pending_decision",
                      _s3(tasks=[{**S3_TASK, "allowed_paths": ["src/x.py"]}]))
    assert def_errors("pipeline_run", "pending_decision",
                      _s3(tasks=[{**S3_TASK, "fr_ids": None}]))
    assert def_errors("pipeline_run", "pending_decision",
                      _s3(frs=[{k: v for k, v in S3_FR.items() if k != "tasks"}]))


def test_inv10_task_schnappschuss():
    gueltig = {"spec_id": "SPEC-0900", "request_id": "req-1",
               "tasks": [{"id": "T01", "title": "Start", "fr_ids": ["FR-01"],
                          "test_file": "tests/t.sh", "description": "…"}]}
    assert def_errors("pipeline_run", "task_snapshot", gueltig) == []
    assert def_errors("pipeline_run", "task_snapshot", {**gueltig, "request_id": ""})
    assert def_errors("pipeline_run", "task_snapshot", {"spec_id": "SPEC-0900", "tasks": []})


def test_inv13_s2_review_mit_befunden():
    """SPEC-0066 FR-01: facts.review an S2 hat die Form von $defs/s2_review."""
    anfrage = {"request_id": "req-2", "point": "S2", "created_at": TS, "task_id": "T01",
               "allowed_commands": ["retry_with_hint", "halt"],
               "facts": {"gate_results": [], "review": {"verdict": "fail", "findings": [
                   {"category": "quality", "file": "src/a.py", "line": 4, "reason": "r"}]}}}
    assert def_errors("pipeline_run", "pending_decision", anfrage) == []
    befund = anfrage["facts"]["review"]["findings"][0]
    zu_lang = {**befund, "reason": "x" * 601}
    anfrage["facts"]["review"]["findings"] = [zu_lang]
    assert def_errors("pipeline_run", "pending_decision", anfrage)
    anfrage["facts"]["review"]["findings"] = [befund] * 21
    assert def_errors("pipeline_run", "pending_decision", anfrage)


def test_inv14_stage_attempts_optional_und_geschlossen():
    """SPEC-0066 FR-03: Stufenzähler je Task; fehlen sie (alter Run), ist state.json gültig."""
    task = {"task_id": "T01", "state": "red", "attempts": 1}
    assert def_errors("pipeline_run", "state", {**STATE, "tasks": [task]}) == []
    mit = {**task, "stage_attempts": {"test": 1, "implementation": 1, "review": 0}}
    assert def_errors("pipeline_run", "state", {**STATE, "tasks": [mit]}) == []
    falsch = {**task, "stage_attempts": {"deploy": 1}}
    assert def_errors("pipeline_run", "state", {**STATE, "tasks": [falsch]})
