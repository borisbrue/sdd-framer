# AUTO-GENERATED from CON-0234 via sdd test generate — do not delete
"""Contract-Tests für Aufteilung von System-Prompt und Prompt im RoleRunner (CON-0234).

Spec: SPEC-0068 · Contract: CON-0234
Pipeline-Läufe über die echte CLI gegen den OpenAI-kompatiblen Fake-Server; geprüft wird, was als
System- und was als Nutzer-Nachricht ankommt. Aufbau, Kürzung und Hash prüfen den echten
RoleRunner mit dem echten `openai-compat`-Provider gegen denselben Server.
"""
from __future__ import annotations

import dataclasses
import hashlib
import re

import pytest

NONCE = re.compile(r"\n\nnonce: [0-9a-f]{16}\Z")

T1 = {"title": "Start", "description": "Start umsetzen", "type": "code", "complexity": "low",
      "fr_ids": ["FR-01"], "dependencies": [], "test_file": "tests/t_FR-01_start.test.sh",
      "test_command": "sh .sdd/quality/run_tests.sh", "allowed_paths": ["src/start.sh"]}


@pytest.fixture()
def llm():
    from tests.support.fake_llm import FakeLLM

    fake = FakeLLM().start()
    yield fake
    fake.stop()


def _nachricht(anfrage: dict, rolle: str) -> str:
    [inhalt] = [m["content"] for m in anfrage["messages"] if m["role"] == rolle]
    return inhalt


def _system(anfrage: dict) -> str:
    return _nachricht(anfrage, "system")


def _nutzer(anfrage: dict) -> str:
    return _nachricht(anfrage, "user")


def _projekt(tmp_path, monkeypatch, llm):
    """Testprojekt mit einem Contract und einer bestehenden Zieldatei."""
    from tests.support.pipeline_project import make_pipeline_project

    p = make_pipeline_project(tmp_path, monkeypatch, llm, frs=("FR-01",))
    (p.root / ".sdd/contracts/behavior").mkdir(parents=True, exist_ok=True)
    (p.root / ".sdd/contracts/behavior/CON-0900-start.md").write_text(
        "---\nid: CON-0900\ntitle: Start\ntype: behavior\nformat: markdown\nspec: SPEC-0900\n"
        "version: 0.1.0\nstatus: approved\ntests: []\n---\n\nVERTRAGSTEXT-START\n")
    spec = next((p.root / ".sdd/specs").glob("SPEC-0900-*.md"))
    spec.write_text(spec.read_text().replace("contracts: []", "contracts: [CON-0900]"))
    (p.root / "src/start.sh").write_text('echo "alt"\n')
    return p


def _drei_rote_versuche(p, llm):
    from tests.support.pipeline_project import command, implementierung, rot_test, zerlegung

    llm.antworte("decomposer", zerlegung(T1))
    llm.antworte("supervisor", command("S1", "approve"), command("S2", "halt"))
    llm.antworte("test_author", rot_test(T1))
    llm.antworte("implementer", *[implementierung(T1, "falsch")] * 3)
    p.run("pipeline", "run", "SPEC-0900")
    return llm.aufrufe("implementer")


def test_tc01_wiederholungsversuche_teilen_den_system_prompt(tmp_path, monkeypatch, llm):
    """Scenario: Wiederholungsversuche teilen den System-Prompt (CON-0234 INV-02, INV-04)."""
    p = _projekt(tmp_path, monkeypatch, llm)
    aufrufe = _drei_rote_versuche(p, llm)

    assert len(aufrufe) == 3
    systeme = [_system(a) for a in aufrufe]
    assert systeme[0] == systeme[1] == systeme[2]
    for teil in ("## Spec", "Anforderung FR-01", "## Contracts", "VERTRAGSTEXT-START",
                 "## AGENTS.md", "## Task", "## Testdatei", 'echo "alt"'):
        assert teil in systeme[0], teil
    assert "nonce:" not in systeme[0]
    assert "## Testausgabe" not in systeme[0]


def test_tc02_rueckmeldungen_stehen_im_prompt(tmp_path, monkeypatch, llm):
    """Scenario: Rückmeldungen stehen im Prompt (CON-0234 INV-03)."""
    p = _projekt(tmp_path, monkeypatch, llm)
    zweiter = _nutzer(_drei_rote_versuche(p, llm)[1])

    assert zweiter.index("## Testausgabe") < zweiter.index("## history")
    assert "GREEN-Gate" in zweiter
    assert NONCE.search(zweiter)
    assert "## Spec" not in zweiter and "## Contracts" not in zweiter


def test_tc03_nach_review_ablehnung_aendert_sich_der_system_prom(tmp_path, monkeypatch, llm):
    """Scenario: Nach Review-Ablehnung ändert sich der System-Prompt (CON-0234 INV-02)."""
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
    llm.antworte("implementer", implementierung(T1), implementierung(T1))
    llm.antworte("reviewer", review(ok=False), review())
    ergebnis = p.run("pipeline", "run", "SPEC-0900")

    assert ergebnis.exit_code == 0, ergebnis.output
    erster, zweiter = (_system(a) for a in llm.aufrufe("implementer"))
    assert erster != zweiter
    assert 'echo "alt"' in erster and 'echo "ok"' in zweiter


def test_tc04_reviewer_sieht_den_diff_im_prompt(tmp_path, monkeypatch, llm):
    """Scenario: Reviewer sieht den Diff im Prompt (CON-0234 INV-01)."""
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
    llm.antworte("implementer", implementierung(T1))
    llm.antworte("reviewer", review())
    p.run("pipeline", "run", "SPEC-0900")

    [anfrage] = llm.aufrufe("reviewer")
    assert "## Diff" in _nutzer(anfrage) and "## Diff" not in _system(anfrage)
    assert "## Spec" in _system(anfrage)


def test_tc05_supervisor_anfrage_im_prompt(tmp_path, monkeypatch, llm):
    """Scenario: Supervisor-Anfrage im Prompt (CON-0234 INV-03)."""
    p = _projekt(tmp_path, monkeypatch, llm)
    _drei_rote_versuche(p, llm)

    s1 = llm.aufrufe("supervisor")[0]
    assert _nutzer(s1).startswith("## Anfrage\n\n")
    assert '"point": "S1"' in _nutzer(s1)
    assert "## Spec" in _system(s1)


def test_tc06_rolle_ohne_wechselnde_quellen(tmp_path, monkeypatch, llm):
    """Scenario: Rolle ohne wechselnde Quellen (CON-0234 INV-02, INV-03)."""
    from sdd_cli.pipeline.roles import load_role

    p = _projekt(tmp_path, monkeypatch, llm)
    _drei_rote_versuche(p, llm)

    rolle = load_role(p.root, "decomposer")
    [erster] = llm.aufrufe("decomposer")
    assert re.fullmatch(re.escape(rolle.purpose) + r"\n\nnonce: [0-9a-f]{16}", _nutzer(erster))
    assert _system(erster).startswith(rolle.prompt + "\n\n## Spec\n\n")


# ── RoleRunner direkt ─────────────────────────────────────────────────────────

def _rolle(inputs: tuple[str, ...], **budgets: int):
    from sdd_cli.pipeline.roles import load_blueprint_role

    return dataclasses.replace(load_blueprint_role("reviewer"), inputs=inputs,
                               input_budgets=budgets)


def _aufruf(llm, rolle, quellen: dict, lead: str = ""):
    """Ruft den echten RoleRunner mit dem echten openai-compat-Provider auf."""
    from sdd_cli.llm.providers.openai_compat import OpenAICompatCompletionProvider
    from sdd_cli.pipeline.runner import RoleRunner

    pytest.importorskip("openai")
    llm.antworte("reviewer", {"verdict": "pass", "findings": []})
    provider = OpenAICompatCompletionProvider(base_url=llm.base_url, model="fake-reviewer",
                                              api_key="fake")
    ergebnis = RoleRunner(run_id="r1", spec_id="SPEC-0900").run(
        rolle, provider, quellen, attempt=1, lead=lead)
    return ergebnis, llm.anfragen[-1]


def test_tc07_aufbau_reihenfolge_kuerzung_und_leere_quellen(llm):
    """Scenario: Aufbau, Reihenfolge, Kürzung und leere Quellen (CON-0234 INV-02, INV-03)."""
    rolle = _rolle(("spec", "task", "test_output", "contracts", "review"), spec=10)
    _, anfrage = _aufruf(llm, rolle, {"spec": "S" * 100, "task": {"id": "T01"},
                                      "test_output": "AUSGABE", "contracts": "", "review": None},
                         lead="ANFRAGE")

    task = '{\n  "id": "T01"\n}'
    gekuerzt = "S" * 40 + "\n… [gekürzt auf etwa 10 Tokens]"
    assert _system(anfrage) == f"{rolle.prompt}\n\n## Spec\n\n{gekuerzt}\n\n## Task\n\n{task}"
    assert NONCE.sub("", _nutzer(anfrage)) == "ANFRAGE\n\n## Testausgabe\n\nAUSGABE"


def test_tc08_rolle_ohne_stabile_quellen(llm):
    """Scenario: Rolle ohne stabile Quellen (CON-0234 INV-02)."""
    rolle = _rolle(("diff",))
    _, anfrage = _aufruf(llm, rolle, {"diff": "+neu"})

    assert _system(anfrage) == rolle.prompt
    assert NONCE.sub("", _nutzer(anfrage)) == "## Diff\n\n+neu"


def test_tc09_prompt_hash(llm):
    """Scenario: prompt_hash (CON-0234 INV-05)."""
    rolle = _rolle(("spec", "test_output"))
    quellen = {"spec": "SPEC", "test_output": "A"}
    erster, anfrage = _aufruf(llm, rolle, quellen)
    zweiter, _ = _aufruf(llm, rolle, quellen)
    anderer_wechsel, _ = _aufruf(llm, rolle, {**quellen, "test_output": "B"})
    andere_stabile, _ = _aufruf(llm, rolle, {**quellen, "spec": "SPEC2"})

    erwartet = hashlib.sha256((_system(anfrage) + "\n\n" + NONCE.sub("", _nutzer(anfrage)))
                              .encode("utf-8")).hexdigest()[:16]
    assert erster.prompt_hash == zweiter.prompt_hash == erwartet
    assert anderer_wechsel.prompt_hash != erster.prompt_hash
    assert andere_stabile.prompt_hash != erster.prompt_hash


def test_tc10_jede_quelle_ist_eingeteilt():
    """Scenario: Jede Quelle ist eingeteilt (CON-0234 INV-01)."""
    from sdd_cli.pipeline.roles import CONTEXT_SOURCES, SOURCE_KINDS

    assert tuple(SOURCE_KINDS) == CONTEXT_SOURCES
    assert set(SOURCE_KINDS.values()) <= {"stable", "volatile"}
    assert {q for q, art in SOURCE_KINDS.items() if art == "volatile"} == {
        "test_output", "review", "history", "diff", "gate_results"}
