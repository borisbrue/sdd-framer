"""Die ausgelieferten Skills führen durch die Gate-Kette, in deren Reihenfolge (#134).

`/sdd-review` kannte nur `sdd spec review`-Ersatz, Regression und Approve. Das
Execution Gate (CON-0025) verlangt aber jede Phase; Approve scheiterte an
`contracts-proposed`, `contracts-review` und `tests-generated`, und der Weg war
nur aus main.py/gate.py zu erschließen.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from sdd_cli.gate import PHASE_ORDER

_ROOT = Path(__file__).resolve().parents[2]
_SKILLS = _ROOT / "tool" / "sdd_cli" / "blueprint" / "templates" / "agents-md" / "providers" / "claude"

# Phase → Befehl, der sie abschließt (main.py: mark_phase_complete). spec-draft und
# contracts-draft sind Zustände (gate.py: evaluate_condition_phases), execute-unlocked
# kommt mit spec-approved.
_BEFEHL_JE_PHASE = {
    "spec-review": "sdd spec review",
    "contracts-proposed": "sdd contract propose",
    "contracts-review": "sdd contract analyze",
    "tests-generated": "sdd test generate",
    "regression-ok": "sdd spec regression",
    "spec-approved": "sdd spec approve",
}


def _kette() -> list[tuple[str, str]]:
    return [(p, _BEFEHL_JE_PHASE[p]) for p in PHASE_ORDER if p in _BEFEHL_JE_PHASE]


def _erste_stelle(text: str, befehl: str) -> int | None:
    m = re.search(r"(?<![\w-])" + re.escape(befehl) + r"(?![\w-])", text)
    return m.start() if m else None


@pytest.mark.parametrize("skill", ["sdd-review.md", "sdd-implement.md"])
def test_skill_nennt_jeden_gate_befehl_in_phasenreihenfolge(skill):
    text = (_SKILLS / skill).read_text(encoding="utf-8")
    # Die Einleitung darf die Kette erklären (Tabelle, Hinweis auf `sdd spec approve`);
    # die Anweisungen beginnen mit dem ersten Schritt.
    text = text[text.find("## Schritt"):]
    stellen = []
    for phase, befehl in _kette():
        stelle = _erste_stelle(text, befehl)
        assert stelle is not None, f"{skill}: `{befehl}` (Phase {phase}) fehlt"
        stellen.append((stelle, phase))
    reihenfolge = [phase for _, phase in sorted(stellen)]
    assert reihenfolge == [phase for phase, _ in _kette()], (
        f"{skill}: Befehle stehen nicht in Gate-Reihenfolge: {reihenfolge}"
    )


def test_review_skill_erklaert_die_kette_und_den_ausweg_ohne_llm():
    text = (_SKILLS / "sdd-review.md").read_text(encoding="utf-8")
    for phase in PHASE_ORDER:
        assert f"`{phase}`" in text, f"Phase {phase} wird nicht erklärt"
    assert "--allow-skipped-llm" in text
    assert "noch nicht abgeschlossen" in text  # die Gate-Meldung wird eingeordnet


def test_review_skill_setzt_contract_status_nicht_als_gate_ersatz():
    """`status: approved` per Edit-Tool sieht das Gate nicht; der Skill sagt das."""
    text = (_SKILLS / "sdd-review.md").read_text(encoding="utf-8")
    assert "sieht das Gate nicht" in text
