"""TST-0234 – CON-0205: Pipeline-Ablauf, Entscheidungsquelle und Fortsetzen.

Spec: SPEC-0053 · Contract: CON-0205
Jedes Szenario ist ein Lauf der echten `sdd pipeline`-CLI gegen den Fake-Server
(`tests/support/fake_llm.py`) in einem Projekt ohne Python (Shell-Tests, JUnit-Sonde).
Bis `sdd pipeline` existiert, werden die Tests übersprungen.
"""
from __future__ import annotations

import json
import socket

import pytest

from tests.support.fake_llm import FakeLLM, prompt_text, task_id_aus
from tests.support.pipeline_project import (
    abnahme,
    command,
    implementierung,
    make_pipeline_project,
    requires_pipeline_cli,
    review,
    rot_test,
    task,
    zerlegung,
)

pytestmark = requires_pipeline_cli

T1 = task("Start", ["FR-01"], "src/start.sh")
T2 = task("Stop", ["FR-02"], "src/stop.sh", deps=["Start"])


@pytest.fixture()
def llm():
    fake = FakeLLM().start()
    yield fake
    fake.stop()


@pytest.fixture()
def projekt(tmp_path, monkeypatch, llm):
    return make_pipeline_project(tmp_path, monkeypatch, llm)


@pytest.fixture()
def projekt1(tmp_path, monkeypatch, llm):
    """Projekt mit nur FR-01."""
    return make_pipeline_project(tmp_path, monkeypatch, llm, frs=("FR-01",))


def _task_gruen(llm, t, reviews=1):
    llm.antworte("test_author", rot_test(t))
    llm.antworte("implementer", implementierung(t))
    llm.antworte("reviewer", *[review() for _ in range(reviews)])


def _entscheidungen(p):
    return p.jsonl("decisions.jsonl")


def test_tc01_dry_run_zerlegt_und_fragt_nur_s1_an(projekt, llm):
    """Scenario: Dry-Run zerlegt und fragt nur S1 an (CON-0205)."""
    llm.antworte("decomposer", zerlegung(T1, T2))
    llm.antworte("supervisor", command("S1", "approve"))
    ergebnis = projekt.run("pipeline", "run", "SPEC-0900", "--dry-run")
    assert ergebnis.exit_code == 0, ergebnis.output
    assert len(llm.aufrufe("decomposer")) == 1
    assert [d["point"] for d in _entscheidungen(projekt)] == ["S1"]
    assert not llm.aufrufe("test_author") and not llm.aufrufe("implementer")


def test_tc02_rollen_check_fehlgeschlagen_vor_s1(projekt, llm):
    """Scenario: Rollen-Check fehlgeschlagen vor S1 (CON-0205)."""
    llm.antworte("decomposer", zerlegung(T1), zerlegung(T1, T2))
    llm.antworte("supervisor", command("S1", "approve"))
    projekt.run("pipeline", "run", "SPEC-0900", "--dry-run")
    aufrufe = llm.aufrufe("decomposer")
    assert len(aufrufe) == 2
    assert "FR-02" in prompt_text(aufrufe[1])
    assert len(llm.aufrufe("supervisor")) == 1


def test_tc03_revise_bis_zur_grenze(projekt, llm):
    """Scenario: revise bis zur Grenze (CON-0205)."""
    llm.antworte("decomposer", *[zerlegung(T1, T2)] * 4)
    llm.antworte("supervisor", *[command("S1", "revise")] * 5)
    ergebnis = projekt.run("pipeline", "run", "SPEC-0900")
    assert projekt.json("state.json")["status"] == "halted"
    assert len(llm.aufrufe("decomposer")) <= 3
    assert ergebnis.exit_code == 1


def test_tc04_red_gate_verwirft_einen_gruenen_test(projekt1, llm):
    """Scenario: RED-Gate verwirft einen grünen Test (CON-0205)."""
    llm.antworte("decomposer", zerlegung(T1))
    llm.antworte("supervisor", command("S1", "approve"), abnahme(FR_01="erfüllt"))
    immer_gruen = {**rot_test(T1), "content": "true\n"}
    llm.antworte("test_author", immer_gruen, rot_test(T1))
    llm.antworte("implementer", implementierung(T1))
    llm.antworte("reviewer", review())
    projekt1.run("pipeline", "run", "SPEC-0900")
    assert len(llm.aufrufe("test_author")) == 2
    assert (projekt1.root / T1["test_file"]).read_text() != "true\n"


def test_tc05_eskalation_nach_max_attempts(projekt1, llm):
    """Scenario: Eskalation nach max_attempts (CON-0205)."""
    llm.antworte("decomposer", zerlegung(T1))
    llm.antworte("supervisor", command("S1", "approve"),
                 lambda a: command("S2", "reassign", task_id=task_id_aus(a), role="implementer",
                                   model="fake-implementer-2"),
                 abnahme(FR_01="erfüllt"))
    llm.antworte("test_author", rot_test(T1))
    llm.antworte("implementer", *[implementierung(T1, "falsch")] * 3)
    llm.antworte("implementer-2", implementierung(T1))
    llm.antworte("reviewer", review())
    projekt1.run("pipeline", "run", "SPEC-0900")
    assert len(llm.aufrufe("implementer")) == 3
    assert len(llm.aufrufe("implementer-2")) == 1
    assert any(e.get("to") == "reassigned" for e in projekt1.jsonl("events.jsonl"))
    [t] = projekt1.json("state.json")["tasks"]
    assert t["state"] in ("green", "reviewed", "done")


def test_tc06_retry_with_hint_gibt_den_hinweis_weiter(projekt1, llm):
    """Scenario: retry_with_hint gibt den Hinweis weiter (CON-0205)."""
    llm.antworte("decomposer", zerlegung(T1))
    llm.antworte("supervisor", command("S1", "approve"),
                 lambda a: command("S2", "retry_with_hint", task_id=task_id_aus(a),
                                   hint="Typ int statt str"),
                 abnahme(FR_01="erfüllt"))
    llm.antworte("test_author", rot_test(T1))
    llm.antworte("implementer", *[implementierung(T1, "falsch")] * 3, implementierung(T1))
    llm.antworte("reviewer", review())
    projekt1.run("pipeline", "run", "SPEC-0900")
    aufrufe = llm.aufrufe("implementer")
    assert len(aufrufe) == 4
    assert "Typ int statt str" in prompt_text(aufrufe[3])
    assert "Typ int statt str" not in prompt_text(aufrufe[0])


def test_tc07_s3_blockiert_finalize_bei_fehlender_fr(projekt1, llm):
    """Scenario: S3 blockiert Finalize bei fehlender FR (CON-0205)."""
    llm.antworte("decomposer", zerlegung(T1))
    llm.antworte("supervisor", command("S1", "approve"), abnahme(FR_01="fehlt"))
    _task_gruen(llm, T1)
    ergebnis = projekt1.run("pipeline", "run", "SPEC-0900")
    assert ergebnis.exit_code == 1
    assert projekt1.json("state.json")["status"] == "halted"
    assert not (projekt1.root / ".sdd/prs").exists()


def test_tc08_ungueltige_entscheidung(projekt, llm):
    """Scenario: Ungültige Entscheidung (CON-0205)."""
    llm.antworte("decomposer", zerlegung(T1, T2))
    llm.antworte("supervisor", {"point": "S2", "command": "approve"}, "kein json")
    projekt.run("pipeline", "run", "SPEC-0900")
    entscheidungen = _entscheidungen(projekt)
    assert [d["valid"] for d in entscheidungen] == [False, False]
    assert projekt.json("state.json")["status"] == "halted"


def test_tc09_dialogmodus_haelt_an_und_setzt_fort(projekt1, llm):
    """Scenario: Dialogmodus hält an und setzt fort (CON-0205)."""
    projekt1.config(llm__roles__supervisor__mode="session")
    llm.antworte("decomposer", zerlegung(T1))
    _task_gruen(llm, T1)
    ergebnis = projekt1.run("pipeline", "run", "SPEC-0900")
    assert ergebnis.exit_code == 3, ergebnis.output
    anfrage = projekt1.json("pending-decision.json")
    assert anfrage["point"] == "S1"
    assert set(anfrage["allowed_commands"]) == {"approve", "revise", "halt"}
    state = projekt1.json("state.json")
    assert state["status"] == "awaiting_supervisor"
    assert state["pending_request_id"] == anfrage["request_id"]
    assert not llm.aufrufe("supervisor")

    run_id = projekt1.run_dir().name
    ergebnis = projekt1.run("pipeline", "decide", run_id, "--json",
                            json.dumps(command("S1", "approve")))
    assert ergebnis.exit_code == 3, ergebnis.output
    assert (projekt1.run_dir() / "requests" / f"{anfrage['request_id']}.json").is_file()
    [erste, *_] = _entscheidungen(projekt1)
    assert erste["request_id"] == anfrage["request_id"] and erste["source"] == "session"
    assert projekt1.json("pending-decision.json")["point"] == "S3"
    assert llm.aufrufe("implementer")


def test_tc10_decide_ohne_offene_anfrage(projekt1, llm):
    """Scenario: decide ohne offene Anfrage (CON-0205)."""
    llm.antworte("decomposer", zerlegung(T1))
    llm.antworte("supervisor", command("S1", "approve"))
    projekt1.run("pipeline", "run", "SPEC-0900", "--dry-run")
    ergebnis = projekt1.run("pipeline", "decide", projekt1.run_dir().name, "--json",
                            json.dumps(command("S1", "approve")))
    assert ergebnis.exit_code == 2


def test_tc11_decide_mit_unzulaessigem_command(projekt1, llm):
    """Scenario: decide mit unzulässigem Command (CON-0205)."""
    projekt1.config(llm__roles__supervisor__mode="session")
    llm.antworte("decomposer", zerlegung(T1))
    projekt1.run("pipeline", "run", "SPEC-0900")
    vorher = projekt1.json("pending-decision.json")
    ergebnis = projekt1.run("pipeline", "decide", projekt1.run_dir().name, "--json",
                            json.dumps(command("S2", "redecompose")))
    assert ergebnis.exit_code == 2
    assert projekt1.json("pending-decision.json") == vorher


def test_tc12_fortsetzen_nach_abbruch(projekt, llm):
    """Scenario: Fortsetzen nach Abbruch (CON-0205)."""
    llm.antworte("decomposer", zerlegung(T1, T2))
    llm.antworte("supervisor", command("S1", "approve"), abnahme(FR_01="erfüllt", FR_02="erfüllt"))
    _task_gruen(llm, T1)
    projekt.run("pipeline", "run", "SPEC-0900", "--max-tasks", "1")
    run_id = projekt.run_dir().name
    zustaende = {t["state"] for t in projekt.json("state.json")["tasks"]}
    assert "done" in zustaende and "pending" in zustaende
    _task_gruen(llm, T2)
    projekt.run("pipeline", "run", "SPEC-0900", "--resume", run_id)
    assert len(llm.aufrufe("test_author")) == 2
    assert {t["state"] for t in projekt.json("state.json")["tasks"]} == {"done"}
    assert len(llm.aufrufe("decomposer")) == 1


def _freier_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_tc13_modellserver_nicht_erreichbar(projekt1, llm):
    """Scenario: Modellserver nicht erreichbar (CON-0205)."""
    projekt1.config(llm__roles__implementer__base_url=f"http://127.0.0.1:{_freier_port()}/v1")
    llm.antworte("decomposer", zerlegung(T1))
    llm.antworte("supervisor", command("S1", "approve"),
                 lambda a: command("S2", "halt", reason="Server weg"))
    llm.antworte("test_author", rot_test(T1))
    projekt1.run("pipeline", "run", "SPEC-0900")
    assert [d["point"] for d in _entscheidungen(projekt1)] == ["S1", "S2"]
    outcomes = [e["outcome"] for e in projekt1.role_calls("implementer")]
    assert outcomes and set(outcomes) == {"error"}


def test_tc14_laengenabbruch_des_thinking_modells(projekt, llm):
    """Scenario: Längenabbruch des Thinking-Modells (CON-0205)."""
    llm.antworte("decomposer", "", finish_reason="length")
    llm.antworte("decomposer", zerlegung(T1, T2))
    llm.antworte("supervisor", command("S1", "approve"))
    projekt.run("pipeline", "run", "SPEC-0900", "--dry-run")
    erste, zweite = llm.aufrufe("decomposer")
    assert zweite["max_tokens"] == int(erste["max_tokens"] * 1.5)


def test_tc15_warnung_bei_gleichem_modell(projekt, llm):
    """Scenario: Warnung bei gleichem Modell (CON-0205)."""
    projekt.config(llm__roles__reviewer__model="fake-implementer")
    llm.antworte("decomposer", zerlegung(T1, T2))
    llm.antworte("supervisor", command("S1", "approve"))
    projekt.run("pipeline", "run", "SPEC-0900", "--dry-run")
    assert "Modell reviewt seine eigene Arbeit" in projekt.json("run.json")["warnings"]


def test_tc16_rueckwaertskompatibilitaet_ohne_llm_roles(projekt, llm):
    """Scenario: Rückwärtskompatibilität ohne llm.roles (CON-0205)."""
    projekt.config(llm__roles=None, llm__completion={"provider": "openai-compat",
                                                      "base_url": llm.base_url,
                                                      "model": "fake-completion",
                                                      "api_key": "fake"})
    llm.antworte("completion", zerlegung(T1, T2))
    ergebnis = projekt.run("decompose", "SPEC-0900", "--yes")
    assert ergebnis.exit_code == 0, ergebnis.output
    assert len(llm.aufrufe("completion")) == 1


def test_tc17_usage_mit_rollenkontext(projekt, llm):
    """Scenario: Usage mit Rollenkontext (CON-0205)."""
    llm.antworte("decomposer", zerlegung(T1, T2), reasoning_tokens=321)
    llm.antworte("supervisor", command("S1", "approve"))
    projekt.run("pipeline", "run", "SPEC-0900", "--dry-run")
    run_id = projekt.run_dir().name
    zeilen = [u for u in projekt.usage() if u.get("run_id") == run_id]
    assert {u["role"] for u in zeilen} >= {"decomposer", "supervisor"}
    decomposer = next(u for u in zeilen if u["role"] == "decomposer")
    assert decomposer["reasoning_tokens"] == 321 and decomposer["attempt"] == 1
    ereignis = next(e for e in projekt.role_calls("decomposer")
                    if e["call_id"] == decomposer["call_id"])
    assert ereignis["outcome"] == "ok"


def test_fr14_report_zeigt_rollen_und_claude_anteil(projekt, llm):
    """SPEC-0053 FR-14: sdd pipeline report nennt je Rolle Aufrufe und Tokens sowie den Claude-Anteil."""
    llm.antworte("decomposer", zerlegung(T1, T2))
    llm.antworte("supervisor", command("S1", "approve"))
    projekt.run("pipeline", "run", "SPEC-0900", "--dry-run")
    ergebnis = projekt.run("pipeline", "report", projekt.run_dir().name)
    assert ergebnis.exit_code == 0, ergebnis.output
    for text in ("decomposer", "supervisor", "Claude"):
        assert text in ergebnis.output
    assert projekt.run("pipeline", "report", "gibt-es-nicht").exit_code == 2


def test_fr16_skill_sdd_supervise_legt_die_rolle_fest():
    """SPEC-0053 FR-16: Der Skill /sdd-supervise verbietet Edits und nutzt sdd pipeline decide."""
    from pathlib import Path

    skill = (Path(__file__).resolve().parents[2]
             / "tool/sdd_cli/blueprint/templates/agents-md/providers/claude/sdd-supervise.md")
    text = skill.read_text(encoding="utf-8")
    for pflicht in ("sdd pipeline run", "sdd pipeline decide", "mode: session", "halt",
                    "teilweise", "fehlt"):
        assert pflicht in text, pflicht
    assert "keine Edits" in text or "Keine Edits" in text
