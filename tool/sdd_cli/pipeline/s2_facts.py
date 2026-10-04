"""Fakten für S2 aus der Reviewer-Ausgabe (SPEC-0066 FR-01, CON-0202 `$defs/s2_review`).

Adapter: übersetzt die Ausgabe der Rolle reviewer (CON-0200 `$defs/reviewer`) in die feste Form
`facts.review`. Nur Befunde, keine Prompts; höchstens 20 Befunde, Begründung je höchstens 600
Zeichen. Ohne ablehnendes Review entsteht kein Feld.
"""
from __future__ import annotations

from typing import Any

MAX_FINDINGS = 20
MAX_REASON = 600
FIELDS = ("category", "file", "line", "reason")


def _finding(befund: Any) -> dict | None:
    if not isinstance(befund, dict) or not all(befund.get(k) for k in ("category", "file",
                                                                        "reason")):
        return None
    eintrag = {k: befund[k] for k in FIELDS if k in befund}
    eintrag["reason"] = str(eintrag["reason"])[:MAX_REASON]
    if not (isinstance(eintrag.get("line"), int) and eintrag["line"] >= 1):
        eintrag.pop("line", None)
    return eintrag


def review_facts(output: Any) -> dict | None:
    """`facts.review` aus einer gültigen, ablehnenden Reviewer-Ausgabe; sonst None."""
    if not isinstance(output, dict) or output.get("verdict") != "fail":
        return None
    befunde = output.get("findings")
    if not isinstance(befunde, list):
        return None
    eintraege = [e for b in befunde if (e := _finding(b)) is not None]
    return {"verdict": "fail", "findings": eintraege[:MAX_FINDINGS]}
