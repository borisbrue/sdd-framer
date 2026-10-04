# AUTO-GENERATED from CON-0232 via sdd test generate — do not delete
"""Contract-Tests für S2-Fakten, Versuche je Stufe und Token-Report (CON-0232).

Spec: SPEC-0066 · Contract: CON-0232
Die Pipeline-Szenarien laufen mit Fake-Rollen (braucht `openai`, sonst übersprungen); Adapter
und Report werden direkt geprüft.
"""
from __future__ import annotations

import json
import re
import sqlite3

import pytest

from tests.support.quality_project import def_errors

BEFUND = {"category": "requirement", "file": "src/start.sh", "line": 4,
          "reason": "Ausgabe weicht von FR-01 ab"}


def _abgelehnt() -> dict:
    return {"verdict": "fail", "findings": [BEFUND]}


# ── Adapter (INV-01) ──────────────────────────────────────────────────────────

def test_adapter_uebernimmt_urteil_und_befunde():
    from sdd_cli.pipeline.s2_facts import review_facts

    fakten = review_facts(_abgelehnt())
    assert fakten == {"verdict": "fail", "findings": [BEFUND]}
    anfrage = {"request_id": "r", "point": "S2", "created_at": "2026-10-04T10:00:00Z",
               "allowed_commands": ["retry_with_hint", "halt"], "task_id": "T01",
               "facts": {"gate_results": [], "review": fakten}}
    assert def_errors("pipeline_run", "pending_decision", anfrage) == []


def test_adapter_kuerzt_auf_20_befunde_und_600_zeichen():
    from sdd_cli.pipeline.s2_facts import review_facts

    viele = [{**BEFUND, "reason": "x" * 700, "extra": 1, "line": 0}] * 25
    fakten = review_facts({"verdict": "fail", "findings": viele})
    assert len(fakten["findings"]) == 20
    erster = fakten["findings"][0]
    assert len(erster["reason"]) == 600 and "extra" not in erster and "line" not in erster


def test_adapter_ohne_gueltiges_review():
    from sdd_cli.pipeline.s2_facts import review_facts

    assert review_facts(None) is None
    assert review_facts({"verdict": "pass", "findings": []}) is None
    assert review_facts({"findings": "kaputt"}) is None


def test_inv02_alte_runs_ohne_stufenzaehler_sind_gueltig():
    zustand = {"run_id": "r", "status": "running", "phase": "tasks", "revisions": 0,
               "pending_request_id": None, "updated_at": "2026-10-04T10:00:00Z",
               "tasks": [{"task_id": "T01", "state": "red", "attempts": 1}]}
    assert def_errors("pipeline_run", "state", zustand) == []
    zustand["tasks"][0]["stage_attempts"] = {"test": 1, "implementation": 1, "review": 0}
    assert def_errors("pipeline_run", "state", zustand) == []


# ── Report (INV-04) ───────────────────────────────────────────────────────────

class _Store:
    run_id = "SPEC-0900-run"

    def __init__(self, rollen: dict):
        self._rollen = rollen

    def read_run(self) -> dict:
        return {"roles": self._rollen, "warnings": []}

    def read_jsonl(self, name: str) -> list[dict]:
        return []


def _usage(root, rolle: str, **werte) -> None:
    from sdd_cli.llm.usage_table import init_token_usage_table_at

    db = init_token_usage_table_at(root / ".sdd")
    zeile = {"timestamp": "2026-10-04T10:00:00Z", "component": "pipeline", "model": "m",
             "input_tokens": 0, "output_tokens": 0, "cache_read_tokens": 0,
             "cache_write_tokens": 0, "duration_ms": 10, "run_id": _Store.run_id,
             "source": "provider", "context_json": json.dumps({"role": rolle}), **werte}
    with sqlite3.connect(db) as con:
        con.execute(f"INSERT INTO token_usage ({', '.join(zeile)}) "
                    f"VALUES ({', '.join('?' for _ in zeile)})", tuple(zeile.values()))


def test_tc05_cache_tokens_im_report_rechnung(tmp_path):
    """Scenario: Cache-Tokens im Report (CON-0232) – Summen und Claude-Anteil."""
    from sdd_cli.pipeline_cli import build_report

    _usage(tmp_path, "reviewer", input_tokens=100, cache_read_tokens=900, cache_write_tokens=300)
    _usage(tmp_path, "implementer", input_tokens=1000, output_tokens=500)
    _usage(tmp_path, "supervisor", input_tokens=0, source="unavailable")
    bericht = build_report(tmp_path, _Store({
        "reviewer": {"provider": "claude-cli"}, "implementer": {"provider": "openai-compat"},
        "supervisor": {"provider": "claude-cli"}}))
    reviewer = next(r for r in bericht["roles"] if r["role"] == "reviewer")
    assert reviewer["cache_read_tokens"] == 900 and reviewer["cache_write_tokens"] == 300
    assert bericht["claude_share"] == pytest.approx(1300 / 2800)
    assert bericht["roles_without_usage"] == ["supervisor"]


# ── Ende zu Ende mit Fake-Rollen (Szenarien) ──────────────────────────────────

@pytest.fixture()
def llm():
    from tests.support.fake_llm import FakeLLM

    fake = FakeLLM().start()
    yield fake
    fake.stop()


T1 = {"title": "Start", "description": "Start umsetzen", "type": "code", "complexity": "low",
      "fr_ids": ["FR-01"], "dependencies": [], "test_file": "tests/t_FR-01_start.test.sh",
      "test_command": "sh .sdd/quality/run_tests.sh", "allowed_paths": ["src/start.sh"]}


def _projekt(tmp_path, monkeypatch, llm):
    from tests.support.pipeline_project import make_pipeline_project

    return make_pipeline_project(tmp_path, monkeypatch, llm, frs=("FR-01",))


def _anfragen(p, point: str) -> list[dict]:
    dateien = sorted((p.run_dir() / "requests").glob("*.json"))
    anfragen = [json.loads(d.read_text()) for d in dateien]
    return sorted((a for a in anfragen if a["point"] == point), key=lambda a: a["created_at"])


def test_tc01_review_befunde_an_s2(tmp_path, monkeypatch, llm):
    """Scenario: Review-Befunde an S2 (CON-0232)."""
    from tests.support.pipeline_project import command, implementierung, rot_test, zerlegung

    p = _projekt(tmp_path, monkeypatch, llm)
    llm.antworte("decomposer", zerlegung(T1))
    llm.antworte("supervisor", command("S1", "approve"), command("S2", "halt"))
    llm.antworte("test_author", rot_test(T1))
    llm.antworte("implementer", *[implementierung(T1)] * 3)
    llm.antworte("reviewer", *[_abgelehnt()] * 3)
    p.run("pipeline", "run", "SPEC-0900")
    [s2] = _anfragen(p, "S2")
    assert def_errors("pipeline_run", "pending_decision", s2) == []
    assert s2["facts"]["review"] == {"verdict": "fail", "findings": [BEFUND]}
    assert len(llm.aufrufe("reviewer")) == 3 and len(llm.aufrufe("implementer")) == 3
    [t] = p.json("state.json")["tasks"]
    assert t["stage_attempts"]["review"] == 3


def test_tc02_eskalation_ohne_review(tmp_path, monkeypatch, llm):
    """Scenario: Eskalation ohne Review (CON-0232)."""
    from tests.support.pipeline_project import command, implementierung, rot_test, zerlegung

    p = _projekt(tmp_path, monkeypatch, llm)
    llm.antworte("decomposer", zerlegung(T1))
    llm.antworte("supervisor", command("S1", "approve"), command("S2", "halt"))
    llm.antworte("test_author", rot_test(T1))
    llm.antworte("implementer", *[implementierung(T1, "falsch")] * 3)
    p.run("pipeline", "run", "SPEC-0900")
    [s2] = _anfragen(p, "S2")
    assert "review" not in s2["facts"]
    assert s2["facts"]["attempts"] == 3
    [t] = p.json("state.json")["tasks"]
    assert t["stage_attempts"] == {"test": 1, "implementation": 3, "review": 0}
    assert t["attempts"] == 3


def test_tc03_eine_review_ablehnung_fuehrt_nicht_zu_s2(tmp_path, monkeypatch, llm):
    """Scenario: Eine Review-Ablehnung führt nicht zu S2 (CON-0232)."""
    from tests.support.pipeline_project import (
        abnahme,
        command,
        implementierung,
        review,
        rot_test,
        zerlegung,
    )

    p = _projekt(tmp_path, monkeypatch, llm)
    p.config(pipeline__max_attempts=3)
    llm.antworte("decomposer", zerlegung(T1))
    llm.antworte("supervisor", command("S1", "approve"), abnahme(FR_01="erfüllt"))
    llm.antworte("test_author", rot_test(T1))
    # Zwei Implementer-Fehlversuche vor dem ersten Grün: mit einem gemeinsamen Zähler käme S2
    # nach der Review-Ablehnung sofort.
    llm.antworte("implementer", implementierung(T1, "nein"), implementierung(T1, "nein"),
                 implementierung(T1), implementierung(T1))
    llm.antworte("reviewer", _abgelehnt(), review())
    ergebnis = p.run("pipeline", "run", "SPEC-0900")
    assert ergebnis.exit_code == 0, ergebnis.output
    assert _anfragen(p, "S2") == []
    [t] = p.json("state.json")["tasks"]
    assert t["state"] == "done"
    assert t["stage_attempts"] == {"test": 1, "implementation": 1, "review": 2}
    bericht = p.run("pipeline", "report", p.run_dir().name)
    assert bericht.exit_code == 0 and "Claude-Anteil an den Tokens (inkl. Cache)" in bericht.output


def test_tc04_implementer_meldet_keine_aenderung(tmp_path, monkeypatch, llm):
    """Scenario: Implementer meldet keine Änderung (CON-0232)."""
    from tests.support.fake_llm import prompt_text
    from tests.support.pipeline_project import (
        abnahme,
        command,
        implementierung,
        review,
        rot_test,
        zerlegung,
    )

    p = _projekt(tmp_path, monkeypatch, llm)
    llm.antworte("decomposer", zerlegung(T1))
    llm.antworte("supervisor", command("S1", "approve"), abnahme(FR_01="erfüllt"))
    llm.antworte("test_author", rot_test(T1))
    llm.antworte("implementer", implementierung(T1),
                 {"files": [], "explanation": "Stand ist richtig, nichts zu ändern"})
    llm.antworte("reviewer", _abgelehnt(), review())
    ergebnis = p.run("pipeline", "run", "SPEC-0900")
    assert ergebnis.exit_code == 0, ergebnis.output
    assert (p.root / "src/start.sh").read_text() == 'echo "ok"\n'
    assert [e.get("outcome") for e in p.role_calls("implementer")] == ["ok", "ok"]
    assert not [e for e in p.jsonl("events.jsonl") if e.get("type") == "write_rejected"]
    zweites_review = prompt_text(llm.aufrufe("reviewer")[1])
    diff = re.search(r"^## Diff[^\n]*\n(.*?)(?=^## |\Z)", zweites_review, re.M | re.S)
    assert diff is not None and '+echo "ok"' in diff.group(1)
    [t] = p.json("state.json")["tasks"]
    assert t["stage_attempts"]["implementation"] == 1
