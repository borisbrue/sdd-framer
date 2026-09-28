# AUTO-GENERATED from CON-0230 via sdd test generate — do not delete
"""Contract-Tests für S3-Abnahme mit Task-Fakten (CON-0230).

Spec: SPEC-0064 · Contract: CON-0230
Die Pipeline-Szenarien laufen mit Fake-Rollen (braucht `openai`, sonst übersprungen); Builder,
Anleitung und Golden Cases werden direkt geprüft.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from tests.support.fake_llm import FakeLLM, prompt_text
from tests.support.pipeline_project import (
    abnahme,
    command,
    implementierung,
    make_pipeline_project,
    review,
    rot_test,
    task,
    zerlegung,
)
from tests.support.quality_project import def_errors

REPO = Path(__file__).resolve().parents[2]
BLUEPRINT = REPO / "tool/sdd_cli/blueprint"
CASES = BLUEPRINT / "roles/supervisor/cases"

T1 = task("Start", ["FR-01"], "src/start.sh")
T2 = task("Stop", ["FR-02"], "src/stop.sh")
T3 = task("Rabatt", ["FR-03"], "src/rabatt.sh")
FELDER = ["id", "title", "fr_ids", "test_file", "state", "attempts"]


@pytest.fixture()
def llm():
    fake = FakeLLM().start()
    yield fake
    fake.stop()


@pytest.fixture()
def projekt(tmp_path, monkeypatch, llm):
    return make_pipeline_project(tmp_path, monkeypatch, llm, frs=("FR-01", "FR-02", "FR-03"))


def _gruen(llm, *tasks):
    llm.antworte("test_author", *[rot_test(t) for t in tasks])
    llm.antworte("implementer", *[implementierung(t) for t in tasks])
    llm.antworte("reviewer", *[review() for _ in tasks])


def _anfragen(p, point: str) -> list[dict]:
    dateien = sorted((p.run_dir() / "requests").glob("*.json"))
    anfragen = [json.loads(d.read_text()) for d in dateien]
    return sorted((a for a in anfragen if a["point"] == point), key=lambda a: a["created_at"])


def _fr(anfrage: dict, fr_id: str) -> dict:
    return next(f for f in anfrage["facts"]["frs"] if f["id"] == fr_id)


def test_tc01_schnappschuss_bei_der_freigabe(projekt, llm):
    """Scenario: Schnappschuss bei der Freigabe (CON-0230)."""
    llm.antworte("decomposer", zerlegung(T1, T2, T3))
    llm.antworte("supervisor", command("S1", "approve"))
    assert projekt.run("pipeline", "run", "SPEC-0900", "--dry-run").exit_code == 0
    snapshot = projekt.json("approved-tasks.json")
    assert def_errors("pipeline_run", "task_snapshot", snapshot) == []
    [s1] = _anfragen(projekt, "S1")
    assert snapshot["request_id"] == s1["request_id"]
    assert [(t["id"], t["title"], t["fr_ids"]) for t in snapshot["tasks"]] == [
        ("T01", "Start", ["FR-01"]), ("T02", "Stop", ["FR-02"]), ("T03", "Rabatt", ["FR-03"])]
    assert not (projekt.run_dir() / "tasks.json").exists()


def test_tc02_abnahme_nennt_tasks_und_ihre_frs(projekt, llm):
    """Scenario: Abnahme nennt Tasks und ihre FRs (CON-0230)."""
    llm.antworte("decomposer", zerlegung(T1, T2, T3))
    llm.antworte("supervisor", command("S1", "approve"),
                 abnahme(FR_01="erfüllt", FR_02="erfüllt", FR_03="erfüllt"))
    _gruen(llm, T1, T2, T3)
    assert projekt.run("pipeline", "run", "SPEC-0900").exit_code == 0
    [s3] = _anfragen(projekt, "S3")
    assert def_errors("pipeline_run", "pending_decision", s3) == []
    assert s3["allowed_commands"] == ["accept_frs", "reopen", "halt"]
    tasks = s3["facts"]["tasks"]
    assert [list(t) for t in tasks] == [FELDER] * 3
    assert tasks[2] == {"id": "T03", "title": "Rabatt", "fr_ids": ["FR-03"],
                        "test_file": T3["test_file"], "state": "done", "attempts": 0}
    assert _fr(s3, "FR-03")["tasks"] == ["T03"]


def test_tc03_fr_ohne_task_und_task_ohne_fr(tmp_path, monkeypatch, llm):
    """Scenario: FR ohne Task und Task ohne FR (CON-0230).

    Eine FR ohne Task besteht die Zerlegungsprüfung `fr_coverage` im Normalfall nicht; diesen Teil
    prüft `test_builder_reihenfolge_und_allowlist` (FR-03 → [])."""
    projekt = make_pipeline_project(tmp_path, monkeypatch, llm, frs=("FR-01",))
    doku = task("Doku", [], "docs/liesmich.md", typ="doc")
    llm.antworte("decomposer", zerlegung(T1, doku))
    llm.antworte("supervisor", command("S1", "approve"), abnahme(FR_01="erfüllt"))
    llm.antworte("test_author", rot_test(T1))  # doc-Tasks laufen ohne test_author
    llm.antworte("implementer", implementierung(T1), implementierung(doku))
    llm.antworte("reviewer", review(), review())
    ergebnis = projekt.run("pipeline", "run", "SPEC-0900")
    assert ergebnis.exit_code == 0, ergebnis.output
    [s3] = _anfragen(projekt, "S3")
    assert def_errors("pipeline_run", "pending_decision", s3) == []
    assert _fr(s3, "FR-01")["tasks"] == ["T01"]
    t02 = next(t for t in s3["facts"]["tasks"] if t["id"] == "T02")
    assert t02["fr_ids"] == [] and t02["title"] == "Doku"


def test_tc04_reopen_mit_task_ids_aus_den_fakten(projekt, llm):
    """Scenario: reopen mit Task-IDs aus den Fakten (CON-0230)."""

    prompts = []

    def reopen_aus_fakten(aufruf):
        prompts.append(prompt_text(aufruf))
        return command("S3", "reopen", task_ids=["T03"], hint="Grenzwert 100 einschließen")

    llm.antworte("decomposer", zerlegung(T1, T2, T3))
    llm.antworte("supervisor", command("S1", "approve"), reopen_aus_fakten,
                 abnahme(FR_01="erfüllt", FR_02="erfüllt", FR_03="erfüllt"))
    _gruen(llm, T1, T2, T3)
    llm.antworte("test_author", rot_test(T3))
    llm.antworte("implementer", implementierung(T3))
    llm.antworte("reviewer", review())
    ergebnis = projekt.run("pipeline", "run", "SPEC-0900")
    assert ergebnis.exit_code == 0, ergebnis.output
    assert '"fr_ids": [' in prompts[0] and '"T03"' in prompts[0]
    erste, zweite = _anfragen(projekt, "S3")
    assert _fr(erste, "FR-03")["tasks"] == ["T03"]
    assert [d["valid"] for d in projekt.jsonl("decisions.jsonl")] == [True, True, True]
    assert any(e.get("to") == "red" and e.get("task_id") == "T03"
               for e in projekt.jsonl("events.jsonl"))
    assert def_errors("pipeline_run", "pending_decision", zweite) == []
    assert [t["state"] for t in zweite["facts"]["tasks"]] == ["done"] * 3


def test_tc05_schnappschuss_fehlt(projekt, llm, monkeypatch):
    """Scenario: Schnappschuss fehlt (CON-0230)."""
    from sdd_cli.pipeline.store import RunStore

    monkeypatch.setattr(RunStore, "write_approved_tasks", lambda self, *a, **k: None)
    llm.antworte("decomposer", zerlegung(T1, T2, T3))
    llm.antworte("supervisor", command("S1", "approve"))
    _gruen(llm, T1, T2, T3)
    ergebnis = projekt.run("pipeline", "run", "SPEC-0900")
    assert ergebnis.exit_code == 1
    state = projekt.json("state.json")
    assert state["status"] == "halted" and state["pending_request_id"] is None
    halt = [e for e in projekt.jsonl("events.jsonl") if e.get("to") == "halted"]
    assert "approved-tasks.json" in halt[-1]["detail"]["reason"]
    assert [d["point"] for d in projekt.jsonl("decisions.jsonl")] == ["S1"]


def test_tc06_neue_zerlegung_ersetzt_den_schnappschuss(tmp_path, monkeypatch, llm):
    """Scenario: Neue Zerlegung ersetzt den Schnappschuss (CON-0230)."""
    projekt = make_pipeline_project(tmp_path, monkeypatch, llm, frs=("FR-01",))
    neu = task("Start neu", ["FR-01"], "src/start.sh")  # ersetzt T1 samt Testdatei
    llm.antworte("decomposer", zerlegung(T1), zerlegung(neu))
    llm.antworte("supervisor", command("S1", "approve"),
                 command("S2", "redecompose"),
                 command("S1", "approve"), abnahme(FR_01="erfüllt"))
    llm.antworte("test_author", rot_test(T1), rot_test(neu))
    llm.antworte("implementer", *[implementierung(T1, "falsch")] * 3, implementierung(neu))
    llm.antworte("reviewer", review())
    ergebnis = projekt.run("pipeline", "run", "SPEC-0900")
    assert ergebnis.exit_code == 0, ergebnis.output
    snapshot = projekt.json("approved-tasks.json")
    assert [t["title"] for t in snapshot["tasks"]] == ["Start neu"]
    assert snapshot["request_id"] == _anfragen(projekt, "S1")[-1]["request_id"]


# ── Builder, Allowlist (FR-02, FR-03, CON-0202 INV-12) ───────────────────────

STATE = [{"task_id": "T01", "state": "done", "attempts": 1},
         {"task_id": "T02", "state": "done", "attempts": 2}]
SNAPSHOT = {"spec_id": "SPEC-0900", "request_id": "req-1", "tasks": [
    {"id": "T02", "title": "B", "fr_ids": ["FR-01", "FR-02"], "test_file": "tests/b.sh",
     "description": "geheim", "allowed_paths": ["src/b.sh"]},
    {"id": "T01", "title": "A", "fr_ids": ["FR-01"], "test_file": None}]}


def test_builder_reihenfolge_und_allowlist():
    from sdd_cli.pipeline.s3_facts import S3FactsBuilder

    fakten = (S3FactsBuilder().tasks(SNAPSHOT, STATE)
              .frs([{"id": "FR-01", "status": "grün", "tests": []},
                    {"id": "FR-02", "status": "rot", "tests": []},
                    {"id": "FR-03", "status": "ohne Test", "tests": []}])
              .gate_results([]).build())
    assert [t["id"] for t in fakten["tasks"]] == ["T01", "T02"]
    assert all(list(t) == FELDER for t in fakten["tasks"])
    assert "geheim" not in json.dumps(fakten)
    assert [f["tasks"] for f in fakten["frs"]] == [["T01", "T02"], ["T02"], []]


def test_builder_verlangt_tasks_vor_frs_und_vollstaendigen_schnappschuss():
    from sdd_cli.pipeline.s3_facts import S3FactsBuilder, SnapshotMissing

    with pytest.raises(RuntimeError):
        S3FactsBuilder().frs([])
    with pytest.raises(SnapshotMissing, match="approved-tasks.json fehlt"):
        S3FactsBuilder().tasks(None, STATE)
    with pytest.raises(SnapshotMissing, match="T03"):
        S3FactsBuilder().tasks(SNAPSHOT, [*STATE, {"task_id": "T03", "state": "red",
                                                   "attempts": 0}])


# ── Anleitung und Golden Cases (FR-06, FR-07, INV-05) ─────────────────────────

@pytest.mark.parametrize("datei", [
    BLUEPRINT / "roles/supervisor.md",
    BLUEPRINT / "templates/agents-md/providers/claude/sdd-supervise.md"],
    ids=["rolle", "skill"])
def test_inv05_anleitung_nennt_die_task_fakten(datei):
    text = datei.read_text(encoding="utf-8")
    assert "facts.tasks" in text and "facts.frs[].tasks" in text


def _s3_faelle() -> list[Path]:
    return sorted(p for p in CASES.iterdir()
                  if json.loads((p / "input/request.json").read_text())["point"] == "S3")


def test_inv05_s3_golden_cases_tragen_die_fakten():
    faelle = _s3_faelle()
    assert len(faelle) >= 3
    for fall in faelle:
        anfrage = json.loads((fall / "input/request.json").read_text())
        assert def_errors("pipeline_run", "pending_decision", anfrage) == [], fall.name
        ids = {t["id"] for t in anfrage["facts"]["tasks"]}
        for fr in anfrage["facts"]["frs"]:
            assert set(fr["tasks"]) <= ids, fall.name
        beschreibung = yaml.safe_load((fall / "case.yaml").read_text())["description"]
        assert "Historie" not in beschreibung, fall.name
        erwartet = json.loads((fall / "expected/decision.json").read_text())
        assert set(erwartet.get("task_ids", [])) <= ids, fall.name


def test_inv05_neuer_fall_zuordnung_nur_aus_den_fakten():
    reopen = [f for f in _s3_faelle()
              if len(json.loads((f / "expected/decision.json").read_text())
                     .get("task_ids", [])) >= 2]
    assert reopen, "kein S3-Fall mit reopen über mehrere Tasks"
    for fall in reopen:
        historie = (fall / "input/history.json").read_text()
        for task_id in json.loads((fall / "expected/decision.json").read_text())["task_ids"]:
            assert task_id not in historie, f"{fall.name}: {task_id} steht in der Historie"
