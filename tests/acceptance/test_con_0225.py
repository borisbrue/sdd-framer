# AUTO-GENERATED from CON-0225 via sdd test generate — do not delete
"""TST-0254 – CON-0225: Pipeline-Budget.

Spec: SPEC-0063 · Contract: CON-0225
Rollen laufen gegen den Fake-LLM-Server; jede Antwort meldet 100 + 50 Tokens.
"""
from __future__ import annotations

import sqlite3

import pytest

from sdd_cli.pipeline import budget
from tests.support.fake_llm import FakeLLM
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


@pytest.fixture()
def llm():
    fake = FakeLLM().start()
    yield fake
    fake.stop()


@pytest.fixture()
def projekt(tmp_path, monkeypatch, llm):
    return make_pipeline_project(tmp_path, monkeypatch, llm, frs=("FR-01",))


def _voll(llm) -> None:
    llm.antworte("decomposer", zerlegung(T1))
    llm.antworte("supervisor", command("S1", "approve"), abnahme(FR_01="erfüllt"))
    llm.antworte("test_author", rot_test(T1))
    llm.antworte("implementer", implementierung(T1))
    llm.antworte("reviewer", review())


def _halt_ereignis(p) -> dict | None:
    return next((e for e in p.jsonl("events.jsonl") if e["type"] == "transition"
                 and e.get("to") == "halted"), None)


def test_tc01_budget_aus_der_run_option(projekt, llm):
    """Scenario: Budget aus der Run-Option (CON-0225)."""
    _voll(llm)
    ergebnis = projekt.run("pipeline", "run", "SPEC-0900", "--max-tokens", "100")
    assert ergebnis.exit_code == 1, ergebnis.output
    assert projekt.json("run.json")["options"]["budget"] == {"max_tokens": 100}
    zustand = projekt.json("state.json")
    assert zustand["status"] == "halted" and zustand["budget_halt"] == "max_tokens"
    ereignis = _halt_ereignis(projekt)
    assert ereignis["detail"]["reason"] == "budget" and ereignis["detail"]["tokens"] == 150
    assert len(llm.aufrufe("decomposer")) == 1 and llm.aufrufe("supervisor") == []


def test_tc02_budget_aus_der_config(projekt, llm):
    """Scenario: Budget aus der Config (CON-0225)."""
    projekt.config(pipeline__budget={"max_tokens": 100})
    _voll(llm)
    assert projekt.run("pipeline", "run", "SPEC-0900").exit_code == 1
    assert _halt_ereignis(projekt)["detail"]["reason"] == "budget"


def test_tc03_claude_budget_zaehlt_nur_claude_rollen(projekt, llm):
    """Scenario: Claude-Budget zählt nur Claude-Rollen (CON-0225)."""
    _voll(llm)
    ergebnis = projekt.run("pipeline", "run", "SPEC-0900", "--max-claude-tokens", "100")
    assert ergebnis.exit_code == 0, ergebnis.output
    assert projekt.json("state.json")["status"] == "completed"


def test_claude_anteil_aus_der_belegung(tmp_path):
    """INV-02: Claude-Tokens sind die der Rollen mit claude-cli/anthropic."""
    (tmp_path / ".sdd").mkdir()
    with sqlite3.connect(tmp_path / ".sdd/evaluations.db") as con:
        con.execute("CREATE TABLE token_usage (component TEXT, input_tokens INTEGER, "
                    "output_tokens INTEGER, run_id TEXT)")
        con.executemany("INSERT INTO token_usage VALUES (?,?,?,?)", [
            ("role:supervisor", 60, 40, "r1"), ("role:implementer", 500, 100, "r1"),
            ("role:supervisor", 999, 1, "anderer-run")])
    rollen = {"supervisor": {"provider": "claude-cli"}, "implementer": {"provider": "x"}}
    stand = budget.usage(tmp_path, "r1", budget.claude_roles(rollen))
    assert stand == {"tokens": 700, "claude_tokens": 100}
    assert budget.exceeded({"max_claude_tokens": 99}, stand) == "max_claude_tokens"
    assert budget.exceeded({"max_tokens": 700}, stand) is None


def test_tc04_kein_budget(projekt, llm):
    """Scenario: Kein Budget (CON-0225)."""
    _voll(llm)
    assert projekt.run("pipeline", "run", "SPEC-0900").exit_code == 0
    assert "budget" not in projekt.json("run.json")["options"]
    assert _halt_ereignis(projekt) is None


def test_tc05_ungueltiges_budget(projekt, llm):
    """Scenario: Ungültiges Budget (CON-0225)."""
    assert projekt.run("pipeline", "run", "SPEC-0900", "--max-tokens", "0").exit_code == 2
    projekt.config(pipeline__budget={"max_tokens": -1})
    assert projekt.run("pipeline", "run", "SPEC-0900").exit_code == 2
    ergebnis = projekt.run("config", "validate")
    assert "pipeline.budget.max_tokens" in ergebnis.output
    assert llm.anfragen == []
