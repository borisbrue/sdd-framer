# AUTO-GENERATED from CON-0208 via sdd test generate — do not delete
"""TST-0237 – CON-0208: write_ownership mit unaufgelösten Schreibzielen.

Spec: SPEC-0059 · Contract: CON-0208
"""
from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from sdd_cli.quality.arch.rules import Rule
from sdd_cli.quality.arch.strategies import STRATEGIES
from sdd_cli.quality.parsers import DepsGraph, Edge
from sdd_cli.quality.schemas import validator

REPO = Path(__file__).resolve().parents[2]
DIFF = json.loads((REPO / ".sdd/contracts/data/write-ownership-unaufgeloeste-schreibziele.schema.json")
                  .read_text(encoding="utf-8"))
LAYERS = {"web": ["app/web/**"], "cli": ["app/**"]}
REGEL = {"id": "ARCH-01", "adr": "ADR-0002", "kind": "write_ownership",
         "paths": [".sdd/**"], "owners": ["cli"], "unresolved": "violation"}


def _arch(regel: dict) -> dict:
    return {"version": 1, "layers": LAYERS, "rules": [regel]}


def _fehler(instanz: dict) -> list[str]:
    diff = [e.message for e in Draft202012Validator(DIFF).iter_errors(instanz)]
    basis = [e.message for e in validator("architecture-rules").iter_errors(_arch(instanz))]
    return diff + basis


def _verstoesse(regel: dict, *kanten: Edge) -> list:
    params = {k: v for k, v in regel.items() if k not in ("id", "adr", "kind", "severity")}
    rule = Rule(id=regel["id"], adr=regel["adr"], kind=regel["kind"], params=params)
    graph = DepsGraph(frozenset({"write"}), list(kanten))
    return STRATEGIES["write_ownership"].evaluate(rule, graph, LAYERS)


def _schreiben(quelle: str, ziel: str | None = None) -> Edge:
    return Edge(source=quelle, target=ziel, kind="write", symbol="pathlib.Path.write_text",
                file=quelle, line=7, unresolved=ziel is None)


def test_tc01_valid_instance_passes():
    """Valide Instanz erfüllt CON-0208 und das erweiterte Schema von CON-0194."""
    assert _fehler(REGEL) == []
    assert _fehler({**REGEL, "unresolved": "skip"}) == []


def test_tc02_invalid_instance_rejected():
    """Beispiel aus dem Contract: unresolved bei forbidden_dependency; unbekannter Wert."""
    falsch = {"id": "ARCH-03", "adr": "ADR-0004", "kind": "forbidden_dependency", "from": ["web"],
              "to_paths": ["app/llm/**"], "unresolved": "violation"}
    assert _fehler(falsch)
    assert _fehler({**REGEL, "unresolved": "immer"})


def test_inv02_ohne_option_bleibt_das_alte_verhalten():
    ohne = {k: v for k, v in REGEL.items() if k != "unresolved"}
    kante = _schreiben("app/web/routes.py")
    assert _verstoesse(ohne, kante) == []
    assert _verstoesse({**REGEL, "unresolved": "skip"}, kante) == []


def test_inv03_unaufgeloest_ausserhalb_der_owners_ist_verstoss():
    [v] = _verstoesse(REGEL, _schreiben("app/web/routes.py"))
    assert (v.rule, v.file, v.symbol) == ("ARCH-01", "app/web/routes.py", "pathlib.Path.write_text")


def test_inv03_owner_und_dateien_ohne_schicht_bleiben_ausgenommen():
    assert _verstoesse(REGEL, _schreiben("app/cli.py"), _schreiben("skripte/x.py")) == []


def test_inv03_aufgeloeste_ziele_wie_bisher():
    assert _verstoesse(REGEL, _schreiben("app/web/r.py", "docs/readme.md")) == []
    assert len(_verstoesse(REGEL, _schreiben("app/web/r.py", ".sdd/specs/SPEC-0001.md"))) == 1
