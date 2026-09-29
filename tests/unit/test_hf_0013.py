"""HF-0013: `retry_with_hint` kann einen Task an den Test-Autor zurückgeben.

Bisher protokollierte `retry_with_hint` einen Übergang nach `retry`, ließ den Zustand aber stehen:
Stand der Task auf `red`, lief wieder nur der Implementer. Ein falscher Test (Testprojekt
todo-service, SPEC-0002 T04: 101 statt 201 Zeichen als „zu lang“) ließ sich an S2 nicht beheben.
Jetzt nennt `stage` die Stufe: `test` schickt die Task an den Test-Autor, `implementation` (und
ohne Angabe) bleibt es beim Implementer wie bisher.
"""
from __future__ import annotations

import pytest

from tests.support.quality_project import schema_errors

BASIS = {"point": "S2", "command": "retry_with_hint", "reason": "Test ist falsch",
         "task_id": "T01", "hint": "Grenze 201 Zeichen"}


@pytest.mark.parametrize("stage", [None, "test", "implementation"])
def test_schema_erlaubt_stage(stage):
    befehl = dict(BASIS) if stage is None else {**BASIS, "stage": stage}
    assert schema_errors("supervisor_command", befehl) == []


def test_schema_lehnt_unbekannte_stage_ab():
    assert schema_errors("supervisor_command", {**BASIS, "stage": "review"})


def test_paketkopie_gleicht_dem_contract():
    import json
    from pathlib import Path

    repo = Path(__file__).resolve().parents[2]
    contract = json.loads((repo / ".sdd/contracts/data/"
                           "supervisor-commands-fuer-s1-bis-s3.schema.json").read_text())
    paket = json.loads((repo / "tool/sdd_cli/pipeline/schemas/"
                        "supervisor-decision.schema.json").read_text())
    assert contract == paket


# ── Ende zu Ende mit Fake-Rollen ────────────────────────────────────────────────

@pytest.fixture()
def llm():
    from tests.support.fake_llm import FakeLLM

    fake = FakeLLM().start()
    yield fake
    fake.stop()


def _lauf(tmp_path, monkeypatch, llm, **retry):
    from tests.support.fake_llm import task_id_aus
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

    projekt = make_pipeline_project(tmp_path, monkeypatch, llm, frs=("FR-01",))
    t1 = task("Start", ["FR-01"], "src/start.sh")
    llm.antworte("decomposer", zerlegung(t1))
    llm.antworte("supervisor", command("S1", "approve"),
                 lambda a: command("S2", "retry_with_hint", task_id=task_id_aus(a),
                                   hint="Der Test erwartet die falsche Ausgabe: ok ist richtig",
                                   **retry),
                 abnahme(FR_01="erfüllt"))
    # Der erste Test ist falsch: er verlangt "anders", richtig wäre "ok".
    llm.antworte("test_author", rot_test(t1, "anders"), rot_test(t1, "ok"))
    llm.antworte("implementer", *[implementierung(t1)] * 4)
    llm.antworte("reviewer", review())
    return projekt, projekt.run("pipeline", "run", "SPEC-0900")


def test_stage_test_schickt_die_task_an_den_test_autor(tmp_path, monkeypatch, llm):
    from tests.support.fake_llm import prompt_text

    projekt, ergebnis = _lauf(tmp_path, monkeypatch, llm, stage="test")
    assert ergebnis.exit_code == 0, ergebnis.output
    autoren = llm.aufrufe("test_author")
    assert len(autoren) == 2
    assert "ok ist richtig" in prompt_text(autoren[1])
    assert len(llm.aufrufe("implementer")) == 4
    zustaende = [(e.get("from"), e.get("to")) for e in projekt.jsonl("events.jsonl")
                 if e.get("type") == "transition" and e.get("task_id") == "T01"]
    assert ("red", "retry") in zustaende
    assert projekt.json("state.json")["tasks"][0]["state"] == "done"


def test_stage_implementation_nach_review_befund(tmp_path, monkeypatch, llm):
    from tests.support.fake_llm import task_id_aus
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

    projekt = make_pipeline_project(tmp_path, monkeypatch, llm, frs=("FR-01",))
    t1 = task("Start", ["FR-01"], "src/start.sh")
    llm.antworte("decomposer", zerlegung(t1))
    llm.antworte("supervisor", command("S1", "approve"),
                 lambda a: command("S2", "retry_with_hint", task_id=task_id_aus(a),
                                   hint="Review-Befund beheben", stage="implementation"),
                 abnahme(FR_01="erfüllt"))
    llm.antworte("test_author", rot_test(t1))
    llm.antworte("implementer", *[implementierung(t1)] * 5)
    llm.antworte("reviewer", review(ok=False), review(), review())
    ergebnis = projekt.run("pipeline", "run", "SPEC-0900")
    zustaende = [(e.get("from"), e.get("to"), (e.get("detail") or {}).get("reason"))
                 for e in projekt.jsonl("events.jsonl")
                 if e.get("type") == "transition" and e.get("task_id") == "T01"]
    assert ergebnis.exit_code == 0, ergebnis.output
    # Der S2-Beschluss (Begründung "begründet" aus command()) schickt die grüne Task zurück an
    # den Implementer; der Test-Autor läuft nicht erneut.
    assert ("green", "red", "begründet") in zustaende
    assert len(llm.aufrufe("test_author")) == 1


def test_ohne_stage_bleibt_es_beim_implementer(tmp_path, monkeypatch, llm):
    projekt, ergebnis = _lauf(tmp_path, monkeypatch, llm)
    # Der falsche Test bleibt, also scheitert der Implementer weiter: kein zweiter Test-Autor.
    assert len(llm.aufrufe("test_author")) == 1
    zustaende = [(e.get("from"), e.get("to")) for e in projekt.jsonl("events.jsonl")
                 if e.get("type") == "transition" and e.get("task_id") == "T01"]
    assert ("red", "retry") not in zustaende
