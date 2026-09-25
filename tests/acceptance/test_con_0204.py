"""TST-0233 – CON-0204: PathPolicy (Schreibrechte je Rolle, Task und Pfad).

Spec: SPEC-0053 · Contract: CON-0204
Die Regelprüfung nutzt die Schnittstelle `PathPolicy(root, protected_paths).check(role, path,
task) -> Entscheidung(allowed, reason)`; Protokoll und Provider-Unabhängigkeit prüft ein echter
Pipeline-Lauf gegen den Fake-Server. Bis `sdd pipeline` existiert, werden die Tests übersprungen.
"""
from __future__ import annotations

import inspect

import pytest

from tests.support.fake_llm import FakeLLM
from tests.support.pipeline_project import (
    command,
    make_pipeline_project,
    requires_pipeline_cli,
    rot_test,
    task,
    zerlegung,
)

pytestmark = requires_pipeline_cli

TASK = {"test_file": "tests/unit/test_app.py", "allowed_paths": ["tool/app/**"]}


@pytest.fixture()
def policy(tmp_path):
    from sdd_cli.pipeline.path_policy import PathPolicy

    return lambda protected=(): PathPolicy(tmp_path, protected_paths=list(protected))


@pytest.fixture()
def llm():
    fake = FakeLLM().start()
    yield fake
    fake.stop()


def _pruefe(policy, rolle, pfad, task=TASK, protected=()):
    return policy(protected).check(rolle, pfad, task)


def test_tc01_supervisor_darf_nie_schreiben(policy):
    """Scenario: Supervisor darf nie schreiben (CON-0204)."""
    e = _pruefe(policy, "supervisor", "tool/app/a.py")
    assert not e.allowed and e.reason == "Rolle supervisor schreibt nicht"


@pytest.mark.parametrize(("rolle", "pfad"), [
    ("implementer", ".sdd/specs/SPEC-0900.md"), ("implementer", ".sdd/holdout/HOL-0001.md"),
    ("test_author", "contracts/data/x.schema.json"), ("implementer", "specs/alt.md")])
def test_tc02_geschuetzte_pfade_fuer_alle_rollen(policy, rolle, pfad):
    """Scenario Outline: Geschützte Pfade für alle Rollen (CON-0204)."""
    task = {**TASK, "test_file": pfad} if rolle == "test_author" else TASK
    e = _pruefe(policy, rolle, pfad, task)
    assert not e.allowed and e.reason == "geschützter Pfad"


def test_tc03_implementer_darf_die_testdatei_nicht_aendern(policy):
    """Scenario: implementer darf die Testdatei nicht ändern (CON-0204)."""
    e = _pruefe(policy, "implementer", "tests/unit/test_app.py")
    assert not e.allowed and e.reason == "Testdatei des Tasks"


def test_tc04_test_author_schreibt_die_testdatei(policy):
    """Scenario: test_author schreibt die Testdatei (CON-0204)."""
    assert _pruefe(policy, "test_author", "tests/unit/test_app.py").allowed


def test_tc05_pfad_ausserhalb_der_erlaubten_pfade(policy):
    """Scenario: Pfad außerhalb der erlaubten Pfade (CON-0204)."""
    e = _pruefe(policy, "implementer", "tool/other/b.py")
    assert not e.allowed and e.reason == "außerhalb allowed_paths"


def test_tc06_erlaubter_pfad(policy):
    """Scenario: Erlaubter Pfad (CON-0204)."""
    e = _pruefe(policy, "implementer", "tool/app/b.py")
    assert e.allowed and e.reason is None


def test_tc07_task_ohne_allowed_paths(policy):
    """Scenario: Task ohne allowed_paths (CON-0204)."""
    assert _pruefe(policy, "implementer", "tool/other/b.py",
                   {"test_file": "tests/unit/test_app.py"}).allowed


@pytest.mark.parametrize("pfad", ["tool/app/../../.sdd/specs/x.md", "../aussen.py",
                                  "tool//app/../../specs/y.md"])
def test_tc08_pfadflucht_wird_erkannt(policy, pfad):
    """Scenario: Pfadflucht wird erkannt (CON-0204)."""
    e = _pruefe(policy, "implementer", pfad)
    assert not e.allowed and e.reason == "geschützter Pfad"


def test_tc09_abgelehnter_schreibvorgang_im_protokoll(tmp_path, monkeypatch, llm):
    """Scenario: Abgelehnter Schreibvorgang im Protokoll (CON-0204)."""
    p = make_pipeline_project(tmp_path, monkeypatch, llm, frs=("FR-01",))
    t = task("Start", ["FR-01"], "src/start.sh")
    llm.antworte("decomposer", zerlegung(t))
    llm.antworte("supervisor", command("S1", "approve"),
                 lambda a: command("S2", "halt", reason="Schreibversuche außerhalb"))
    llm.antworte("test_author", rot_test(t))
    falsch = {"files": [{"path": "src/anders.sh", "content": "echo ok\n"}], "explanation": "x"}
    llm.antworte("implementer", falsch, falsch, falsch)
    p.run("pipeline", "run", "SPEC-0900")
    abgelehnt = [e for e in p.jsonl("events.jsonl") if e["type"] == "write_rejected"]
    assert abgelehnt and abgelehnt[0]["role"] == "implementer"
    assert "src/anders.sh" in str(abgelehnt[0]) and "außerhalb allowed_paths" in str(abgelehnt[0])
    assert not (p.root / "src/anders.sh").exists()
    assert "gate_failed" in {e["outcome"] for e in p.role_calls("implementer")}


def test_tc10_unabhaengig_vom_provider(policy):
    """Scenario Outline: Unabhängig vom Provider (CON-0204): die Prüfung kennt keinen Provider."""
    from sdd_cli.pipeline.path_policy import PathPolicy

    parameter = set(inspect.signature(PathPolicy.check).parameters) - {"self"}
    assert parameter == {"role", "path", "task"}
    assert not _pruefe(policy, "implementer", "tests/unit/test_app.py").allowed


@pytest.mark.parametrize("rolle", ["reviewer", "decomposer", "doc_writer"])
def test_tc11_nicht_schreibende_rollen_werden_abgelehnt(policy, rolle):
    """Scenario Outline: Nicht schreibende Rollen werden abgelehnt (CON-0204)."""
    e = _pruefe(policy, rolle, "tool/app/a.py")
    assert not e.allowed and e.reason == f"Rolle {rolle} schreibt nicht"


def test_tc12_test_author_schreibt_nur_die_testdatei(policy):
    """Scenario: test_author schreibt nur die Testdatei (CON-0204)."""
    e = _pruefe(policy, "test_author", "tool/app/a.py")
    assert not e.allowed and e.reason == "test_author schreibt nur die Testdatei"


def test_tc13_projekteigene_geschuetzte_pfade(policy):
    """Scenario: Projekteigene geschützte Pfade (CON-0204)."""
    task = {**TASK, "allowed_paths": ["docs/**"]}
    e = _pruefe(policy, "implementer", "docs/adr/ADR-0001.md", task, protected=["docs/adr/**"])
    assert not e.allowed and e.reason == "geschützter Pfad"

