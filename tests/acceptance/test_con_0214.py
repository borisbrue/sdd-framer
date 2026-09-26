# AUTO-GENERATED from CON-0214 via sdd test generate — do not delete
"""TST-0243 – CON-0214: Abschluss-Kette, reopen und config test-llm.

Spec: SPEC-0061 · Contract: CON-0214
Die Schritte der Kette rufen die bestehenden Werkzeuge über dünne Wrapper in
`sdd_cli.pipeline.steps` auf (`run_holdouts`, `run_finalize`, `automerge`); die Tests ersetzen genau
diese Wrapper, damit weder Holdout-Server noch GitHub gebraucht werden.
"""
from __future__ import annotations

import pytest

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

T1 = task("Start", ["FR-01"], "src/start.sh")
HOLDOUT = {"passed": 1, "failed": 1, "rate": 0.5,
           "scenarios": [{"id": "HOL-0001", "title": "Start", "passed": True},
                         {"id": "HOL-0002", "title": "Leere Eingabe", "passed": False}]}


@pytest.fixture()
def llm():
    fake = FakeLLM().start()
    yield fake
    fake.stop()


@pytest.fixture()
def projekt(tmp_path, monkeypatch, llm):
    return make_pipeline_project(tmp_path, monkeypatch, llm, frs=("FR-01",))


@pytest.fixture()
def schritte(monkeypatch):
    """Ersetzt die Wrapper der Kette und protokolliert ihre Aufrufe."""
    from sdd_cli.pipeline import steps

    aufrufe: list[str] = []
    ergebnis = {"holdout": HOLDOUT, "finalize": "https://github.com/x/y/pull/7",
                "automerge": ("merged", "Autonomie-Level erlaubt Merge")}

    def holdouts(config, spec_id, base_url):
        aufrufe.append("holdout")
        return ergebnis["holdout"]

    def finalize(config, spec_id):
        aufrufe.append("finalize")
        return ergebnis["finalize"]

    def automerge(config, spec_id, pr_url):
        aufrufe.append("automerge")
        return ergebnis["automerge"]

    monkeypatch.setattr(steps, "run_holdouts", holdouts)
    monkeypatch.setattr(steps, "run_finalize", finalize)
    monkeypatch.setattr(steps, "automerge", automerge)
    return aufrufe, ergebnis


def _task_antworten(llm, implementer=1, reviews=1):
    llm.antworte("test_author", rot_test(T1))
    llm.antworte("implementer", *[implementierung(T1)] * implementer)
    llm.antworte("reviewer", *[review()] * reviews)


def _gates(p, name):
    return [e["detail"] for e in p.jsonl("events.jsonl")
            if e["type"] == "gate" and (e.get("detail") or {}).get("gate") == name]


def test_tc01_holdout_ergebnis_als_fakt_der_abnahme(projekt, llm, schritte):
    """Scenario: Holdout-Ergebnis als Fakt der Abnahme (CON-0214)."""
    projekt.config(llm__roles__supervisor__mode="session",
                   evaluator={"base_url": "http://localhost:9000"})
    llm.antworte("decomposer", zerlegung(T1))
    _task_antworten(llm)
    projekt.run("pipeline", "run", "SPEC-0900", "--auto")
    projekt.run("pipeline", "decide", projekt.run_dir().name, "--json",
                '{"point": "S1", "command": "approve", "reason": "ok"}')
    anfrage = projekt.json("pending-decision.json")
    assert anfrage["point"] == "S3"
    assert anfrage["facts"]["holdout"]["rate"] == 0.5
    assert schritte[0] == ["holdout"]


def test_tc02_holdout_ohne_base_url(projekt, llm, schritte):
    """Scenario: Holdout ohne Base-URL (CON-0214)."""
    # Das Blueprint setzt evaluator.base_url auf localhost; „ohne“ heißt hier ausdrücklich leer.
    projekt.config(llm__roles__supervisor__mode="session", evaluator__base_url="")
    llm.antworte("decomposer", zerlegung(T1))
    _task_antworten(llm)
    projekt.run("pipeline", "run", "SPEC-0900", "--auto")
    projekt.run("pipeline", "decide", projekt.run_dir().name, "--json",
                '{"point": "S1", "command": "approve", "reason": "ok"}')
    holdout = projekt.json("pending-decision.json")["facts"]["holdout"]
    assert holdout["status"] == "n/a" and holdout["reason"]
    assert "holdout" not in schritte[0]


def test_tc03_reopen_oeffnet_tasks_erneut(projekt, llm, schritte):
    """Scenario: reopen öffnet Tasks erneut (CON-0214)."""
    llm.antworte("decomposer", zerlegung(T1))
    llm.antworte("supervisor", command("S1", "approve"),
                 command("S3", "reopen", task_ids=["T01"], hint="Leere Eingabe beachten"),
                 abnahme(FR_01="erfüllt"))
    _task_antworten(llm, implementer=2, reviews=2)
    ergebnis = projekt.run("pipeline", "run", "SPEC-0900")
    assert ergebnis.exit_code == 0, ergebnis.output
    implementer = llm.aufrufe("implementer")
    assert len(implementer) == 2 and "Leere Eingabe beachten" in prompt_text(implementer[1])
    assert [d["point"] for d in projekt.jsonl("decisions.jsonl")] == ["S1", "S3", "S3"]


def test_tc04_reopen_bis_zur_grenze(projekt, llm, schritte):
    """Scenario: reopen bis zur Grenze (CON-0214)."""
    projekt.config(pipeline__max_reopen=1)
    reopen = command("S3", "reopen", task_ids=["T01"], hint="nochmal")
    llm.antworte("decomposer", zerlegung(T1))
    llm.antworte("supervisor", command("S1", "approve"), reopen, reopen)
    _task_antworten(llm, implementer=2, reviews=2)
    ergebnis = projekt.run("pipeline", "run", "SPEC-0900")
    assert ergebnis.exit_code == 1
    assert projekt.json("state.json")["status"] == "halted"


def test_tc05_finalize_und_auto_merge(projekt, llm, schritte):
    """Scenario: Finalize und Auto-Merge (CON-0214)."""
    projekt.config(evaluator__base_url="")
    llm.antworte("decomposer", zerlegung(T1))
    llm.antworte("supervisor", command("S1", "approve"), abnahme(FR_01="erfüllt"))
    _task_antworten(llm)
    ergebnis = projekt.run("pipeline", "run", "SPEC-0900", "--auto")
    assert ergebnis.exit_code == 0, ergebnis.output
    assert schritte[0] == ["finalize", "automerge"]
    assert _gates(projekt, "finalize")[0]["status"] == "ok"
    merge = _gates(projekt, "automerge")[0]
    assert merge["status"] == "ok" and merge["result"] == "merged"
    assert projekt.json("state.json")["status"] == "completed"


def test_tc06_auto_merge_nicht_erlaubt(projekt, llm, schritte):
    """Scenario: Auto-Merge nicht erlaubt (CON-0214)."""
    schritte[1]["automerge"] = ("open", "Autonomie-Level 2 erlaubt keinen Merge")
    llm.antworte("decomposer", zerlegung(T1))
    llm.antworte("supervisor", command("S1", "approve"), abnahme(FR_01="erfüllt"))
    _task_antworten(llm)
    assert projekt.run("pipeline", "run", "SPEC-0900", "--auto").exit_code == 0
    merge = _gates(projekt, "automerge")[0]
    assert merge["result"] == "open" and "Autonomie-Level 2" in merge["reason"]


def test_tc07_ohne_auto_nur_finalize(projekt, llm, schritte):
    """Scenario: Ohne --auto nur finalize (CON-0214)."""
    projekt.config(evaluator={"base_url": "http://localhost:9000"})
    llm.antworte("decomposer", zerlegung(T1))
    llm.antworte("supervisor", command("S1", "approve"), abnahme(FR_01="erfüllt"))
    _task_antworten(llm)
    assert projekt.run("pipeline", "run", "SPEC-0900").exit_code == 0
    assert schritte[0] == ["finalize"]


def test_tc08_task_mit_auto(projekt, llm):
    """Scenario: --task mit --auto (CON-0214)."""
    assert projekt.run("pipeline", "run", "SPEC-0900", "--task", "T01", "--auto").exit_code == 2


def test_tc09_test_llm_prueft_rollen_und_profile(projekt, llm):
    """Scenario: test-llm prüft Rollen und Profile (CON-0214)."""
    projekt.config(llm__profiles={"lokal": {"provider": "openai-compat", "base_url": llm.base_url,
                                            "model": "fake-lokal", "api_key": "fake"}},
                   llm__roles__reviewer={"profile": "lokal"},
                   llm__roles__implementer={"profile": "lokal"})
    for rolle in ("lokal", "decomposer", "test_author", "supervisor"):
        llm.antworte(rolle, "OK", reasoning_tokens=3 if rolle == "lokal" else None)
    ergebnis = projekt.run("config", "test-llm")
    assert ergebnis.exit_code == 0, ergebnis.output
    assert len(llm.aufrufe("lokal")) == 1
    assert "Reasoning" in ergebnis.output


def test_tc10_test_llm_ueberspringt_session_rollen(projekt, llm):
    """Scenario: test-llm überspringt Session-Rollen (CON-0214)."""
    projekt.config(llm__roles__implementer={"mode": "session"})
    ergebnis = projekt.run("config", "test-llm", "--role", "implementer")
    assert ergebnis.exit_code == 0, ergebnis.output
    assert "session" in ergebnis.output and not llm.anfragen
