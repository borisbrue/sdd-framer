# AUTO-GENERATED from CON-0213 via sdd test generate — do not delete
"""TST-0242 – CON-0213: Session-Arbeitsrollen, Routing, Task-Typen und Gates pro Task.

Spec: SPEC-0061 · Contract: CON-0213
LLM-Rollen laufen gegen den Fake-Server; eine Session wird gespielt, indem der Test die Dateien
schreibt und `sdd pipeline done` aufruft.
"""
from __future__ import annotations

import json
import shutil
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

T1 = task("Start", ["FR-01"], "src/start.sh")
T2 = task("Stop", ["FR-02"], "src/stop.sh", deps=["Start"])
PRESET = Path(__file__).resolve().parents[2] / "tool/sdd_cli/blueprint/stacks/python-cli/files/.sdd/quality"


@pytest.fixture()
def llm():
    fake = FakeLLM().start()
    yield fake
    fake.stop()


@pytest.fixture()
def projekt(tmp_path, monkeypatch, llm):
    return make_pipeline_project(tmp_path, monkeypatch, llm, frs=("FR-01",))


@pytest.fixture()
def projekt2(tmp_path, monkeypatch, llm):
    return make_pipeline_project(tmp_path, monkeypatch, llm)


def _auftrag(p) -> dict:
    return p.json("pending-work.json")


def _bis_zum_implementer_session(p, llm):
    p.config(llm__roles__implementer={"mode": "session"})
    llm.antworte("decomposer", zerlegung(T1))
    llm.antworte("supervisor", command("S1", "approve"), abnahme(FR_01="erfüllt"))
    llm.antworte("test_author", rot_test(T1))
    return p.run("pipeline", "run", "SPEC-0900")


def _schreiben(p, pfad, inhalt):
    ziel = p.root / pfad
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text(inhalt, encoding="utf-8")


def test_tc01_implementer_im_dialog(projekt, llm):
    """Scenario: Implementer im Dialog (CON-0213)."""
    ergebnis = _bis_zum_implementer_session(projekt, llm)
    assert ergebnis.exit_code == 3, ergebnis.output
    assert projekt.json("state.json")["status"] == "awaiting_session"
    auftrag = _auftrag(projekt)
    assert (auftrag["kind"], auftrag["role"], auftrag["task_id"]) == ("work", "implementer", "T01")
    assert auftrag["allowed_paths"] == ["src/start.sh"]
    assert not llm.aufrufe("implementer")


def test_tc02_bestaetigung_setzt_den_run_fort(projekt, llm):
    """Scenario: Bestätigung setzt den Run fort (CON-0213)."""
    _bis_zum_implementer_session(projekt, llm)
    request_id = _auftrag(projekt)["request_id"]
    llm.antworte("reviewer", review())
    _schreiben(projekt, "src/start.sh", 'echo "ok"\n')
    ergebnis = projekt.run("pipeline", "done", projekt.run_dir().name)
    assert ergebnis.exit_code == 0, ergebnis.output
    assert len(llm.aufrufe("reviewer")) == 1
    assert (projekt.run_dir() / "requests" / f"{request_id}.json").is_file()
    assert {t["state"] for t in projekt.json("state.json")["tasks"]} == {"done"}


def _bis_zum_reviewer_session(p, llm):
    p.config(llm__roles__reviewer={"mode": "session"})
    llm.antworte("decomposer", zerlegung(T1))
    llm.antworte("supervisor", command("S1", "approve"), abnahme(FR_01="erfüllt"))
    llm.antworte("test_author", rot_test(T1))
    llm.antworte("implementer", implementierung(T1))
    assert p.run("pipeline", "run", "SPEC-0900").exit_code == 3


def test_tc03_reviewer_im_dialog_mit_json_ausgabe(projekt, llm):
    """Scenario: Reviewer im Dialog mit JSON-Ausgabe (CON-0213)."""
    _bis_zum_reviewer_session(projekt, llm)
    assert _auftrag(projekt)["role"] == "reviewer"
    ergebnis = projekt.run("pipeline", "done", projekt.run_dir().name, "--json",
                           json.dumps({"verdict": "pass", "findings": []}))
    assert ergebnis.exit_code == 0, ergebnis.output
    assert {t["state"] for t in projekt.json("state.json")["tasks"]} == {"done"}


def test_tc04_ungueltige_bestaetigung(projekt, llm):
    """Scenario: Ungültige Bestätigung (CON-0213)."""
    _bis_zum_reviewer_session(projekt, llm)
    vorher = _auftrag(projekt)
    ergebnis = projekt.run("pipeline", "done", projekt.run_dir().name, "--json",
                           json.dumps({"verdict": "vielleicht"}))
    assert ergebnis.exit_code == 2
    assert _auftrag(projekt) == vorher
    assert projekt.json("state.json")["status"] == "awaiting_session"


def test_tc05_done_ohne_offenen_auftrag(projekt, llm):
    """Scenario: done ohne offenen Auftrag (CON-0213)."""
    llm.antworte("decomposer", zerlegung(T1))
    llm.antworte("supervisor", command("S1", "approve"))
    projekt.run("pipeline", "run", "SPEC-0900", "--dry-run")
    assert projekt.run("pipeline", "done", projekt.run_dir().name).exit_code == 2


def test_tc06_rollenvertrag_bei_schreibzugriff_ausserhalb_der_er(projekt, llm):
    """Scenario: Rollenvertrag bei Schreibzugriff außerhalb der erlaubten Pfade (CON-0213)."""
    _bis_zum_implementer_session(projekt, llm)
    _schreiben(projekt, "src/start.sh", 'echo "ok"\n')
    _schreiben(projekt, "src/anders.sh", "echo x\n")
    ergebnis = projekt.run("pipeline", "done", projekt.run_dir().name)
    assert ergebnis.exit_code == 3, ergebnis.output
    abgelehnt = [e for e in projekt.jsonl("events.jsonl") if e["type"] == "write_rejected"]
    assert abgelehnt and "src/anders.sh" in json.dumps(abgelehnt[0])
    assert "gate_failed" in {e["outcome"] for e in projekt.role_calls("implementer")}
    assert "src/anders.sh" in json.dumps(_auftrag(projekt)["feedback"])


def _profile(p, llm, **belegung):
    p.config(llm__profiles={name: {"provider": "openai-compat", "base_url": llm.base_url,
                                   "model": f"fake-{name}", "api_key": "fake"}
                            for name in ("lokal", "stark")})
    p.config(llm__roles__implementer={"by_complexity": belegung})


def test_tc07_routing_nach_komplexitaet(projekt2, llm):
    """Scenario: Routing nach Komplexität (CON-0213)."""
    _profile(projekt2, llm, low="lokal", high="stark")
    t2 = {**T2, "complexity": "high"}
    llm.antworte("decomposer", zerlegung(T1, t2))
    llm.antworte("supervisor", command("S1", "approve"), abnahme(FR_01="erfüllt", FR_02="erfüllt"))
    llm.antworte("test_author", rot_test(T1), rot_test(t2))
    llm.antworte("lokal", implementierung(T1))
    llm.antworte("stark", implementierung(t2))
    llm.antworte("reviewer", review(), review())
    assert projekt2.run("pipeline", "run", "SPEC-0900").exit_code == 0
    assert "Start" in prompt_text(llm.aufrufe("lokal")[0])
    assert "Stop" in prompt_text(llm.aufrufe("stark")[0])
    assert not llm.aufrufe("implementer")
    modelle = {u["model"] for u in projekt2.usage() if u.get("role") == "implementer"}
    assert modelle == {"fake-lokal", "fake-stark"}


def test_tc08_routing_auf_session(projekt, llm):
    """Scenario: Routing auf session (CON-0213)."""
    projekt.config(llm__roles__implementer={"by_complexity": {"high": "session"}})
    llm.antworte("decomposer", zerlegung({**T1, "complexity": "high"}))
    llm.antworte("supervisor", command("S1", "approve"))
    llm.antworte("test_author", rot_test(T1))
    assert projekt.run("pipeline", "run", "SPEC-0900").exit_code == 3
    assert _auftrag(projekt)["role"] == "implementer"
    assert not llm.aufrufe("implementer")


def test_tc09_unbekanntes_profil(projekt, llm):
    """Scenario: Unbekanntes Profil (CON-0213)."""
    projekt.config(llm__roles__implementer={"by_complexity": {"low": "gibtsnicht"}})
    assert projekt.run("pipeline", "run", "SPEC-0900").exit_code == 2
    assert not llm.anfragen


def test_tc10_einzelner_task(projekt2, llm):
    """Scenario: Einzelner Task (CON-0213)."""
    llm.antworte("decomposer", zerlegung(T1, T2))
    llm.antworte("supervisor", command("S1", "approve"))
    assert projekt2.run("pipeline", "run", "SPEC-0900", "--dry-run").exit_code == 0
    llm.anfragen.clear()
    llm.antworte("test_author", rot_test(T2))
    llm.antworte("implementer", implementierung(T2))
    llm.antworte("reviewer", review())
    ergebnis = projekt2.run("pipeline", "run", "SPEC-0900", "--task", "T02")
    assert ergebnis.exit_code == 0, ergebnis.output
    assert not llm.aufrufe("decomposer") and not llm.aufrufe("supervisor")
    [t] = projekt2.json("state.json")["tasks"]
    assert (t["task_id"], t["state"]) == ("T02", "done")


def test_tc11_einzelner_task_ohne_zerlegung(projekt, llm):
    """Scenario: Einzelner Task ohne Zerlegung (CON-0213)."""
    assert projekt.run("pipeline", "run", "SPEC-0900", "--task", "T01").exit_code == 2


def test_tc12_doku_task_ohne_red_gate(projekt, llm):
    """Scenario: Doku-Task ohne RED-Gate (CON-0213)."""
    doku = task("Handbuch", ["FR-01"], "docs/handbuch.md", typ="doc")
    llm.antworte("decomposer", zerlegung(doku))
    llm.antworte("supervisor", command("S1", "approve"), abnahme(FR_01="erfüllt"))
    llm.antworte("implementer", {"files": [{"path": "docs/handbuch.md", "content": "# Handbuch\n"}],
                                 "explanation": "Doku"})
    llm.antworte("reviewer", review())
    ergebnis = projekt.run("pipeline", "run", "SPEC-0900")
    assert ergebnis.exit_code == 0, ergebnis.output
    assert not llm.aufrufe("test_author")
    assert (projekt.root / "docs/handbuch.md").is_file()


def _architektur(p):
    (p.root / ".sdd/quality").mkdir(parents=True, exist_ok=True)
    shutil.copy(PRESET / "extract_deps.py", p.root / ".sdd/quality/extract_deps.py")
    qpfad = p.root / ".sdd/quality.yaml"
    q = yaml.safe_load(qpfad.read_text(encoding="utf-8"))
    q["paths"] = ["app/**/*.py"]
    q["probes"]["imports"] = {"command": "python3 .sdd/quality/extract_deps.py {paths} > {out}",
                              "format": "sdd-deps", "role": "deps"}
    qpfad.write_text(yaml.safe_dump(q, sort_keys=False), encoding="utf-8")
    (p.root / "app").mkdir()
    (p.root / "app/__init__.py").write_text("", encoding="utf-8")
    (p.root / "app/verboten.py").write_text("X = 1\n", encoding="utf-8")
    (p.root / ".sdd/architecture.yaml").write_text(yaml.safe_dump({
        "version": 1, "layers": {"app": ["app/**"]},
        "rules": [{"id": "ARCH-01", "adr": "ADR-0001", "kind": "forbidden_dependency",
                   "from": ["app"], "to_paths": ["app/verboten.py"]}]}), encoding="utf-8")


def test_tc13_architektur_gate_pro_task(projekt, llm):
    """Scenario: Architektur-Gate pro Task (CON-0213)."""
    _architektur(projekt)
    t = {**T1, "allowed_paths": ["src/start.sh", "app/modul.py"]}
    schlecht = {"files": [{"path": "src/start.sh", "content": 'echo "ok"\n'},
                          {"path": "app/modul.py", "content": "import app.verboten\n"}],
                "explanation": "mit verbotenem Import"}
    gut = {"files": [{"path": "src/start.sh", "content": 'echo "ok"\n'},
                     {"path": "app/modul.py", "content": "Y = 2\n"}], "explanation": "sauber"}
    llm.antworte("decomposer", zerlegung(t))
    llm.antworte("supervisor", command("S1", "approve"), abnahme(FR_01="erfüllt"))
    llm.antworte("test_author", rot_test(t))
    llm.antworte("implementer", schlecht, gut)
    llm.antworte("reviewer", review())
    ergebnis = projekt.run("pipeline", "run", "SPEC-0900")
    assert ergebnis.exit_code == 0, ergebnis.output
    assert [e["outcome"] for e in projekt.role_calls("implementer")] == ["gate_failed", "ok"]
    assert (projekt.root / "app/modul.py").read_text(encoding="utf-8") == "Y = 2\n"


def test_tc14_gate_ohne_konfiguration(projekt, llm):
    """Scenario: Gate ohne Konfiguration (CON-0213)."""
    projekt.config(pipeline__task_gates=["tests", "architecture"])
    llm.antworte("decomposer", zerlegung(T1))
    llm.antworte("supervisor", command("S1", "approve"), abnahme(FR_01="erfüllt"))
    llm.antworte("test_author", rot_test(T1))
    llm.antworte("implementer", implementierung(T1))
    llm.antworte("reviewer", review())
    assert projekt.run("pipeline", "run", "SPEC-0900").exit_code == 0
    gates = [e for e in projekt.jsonl("events.jsonl") if e["type"] == "gate"
             and (e.get("detail") or {}).get("gate") == "architecture"]
    assert gates and gates[0]["detail"]["status"] == "n/a"
