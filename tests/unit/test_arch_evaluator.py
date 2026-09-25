"""SPEC-0054 FR-05, CON-0196 (Architekturscore, quorum), CON-0194 INV-03/INV-07."""
from __future__ import annotations

import pytest

from sdd_cli.quality.arch.evaluator import evaluate_architecture
from sdd_cli.quality.arch.rules import Architecture, Rule
from sdd_cli.quality.parsers import DepsGraph, Edge
from sdd_cli.quality.settings import QualitySettings


def _rule(i, severity="error", kind="forbidden_dependency", **params):
    params = params or {"from": "src", "to_paths": [f"ziel{i}/**"]}
    return Rule(id=f"ARCH-{i:02d}", adr="ADR-0101", kind=kind, severity=severity, params=params)


def _graph(n, kinds=("import",)):
    return DepsGraph(frozenset(kinds), [Edge("src/a.py", f"ziel{i}/x.py", "import", f"S{i}",
                                             "src/a.py", i + 1) for i in range(1, n + 1)])


def _arch(rules):
    return Architecture({"src": ["src/**"]}, rules)


def test_gewichteter_score():
    r = evaluate_architecture(_arch([_rule(1), _rule(2), _rule(3, "warn"), _rule(4, "warn")]),
                              _graph(4), QualitySettings(), adr_titles={"ADR-0101": "Titel"})
    assert r.node.score() == pytest.approx(0.5)
    assert r.errors == 2 and r.warnings == 2
    v = r.violations[0]
    assert (v.rule, v.adr, v.adr_title, v.file, v.line, v.symbol) == (
        "ARCH-01", "ADR-0101", "Titel", "src/a.py", 2, "S1")


def test_severity_gewichte_konfigurierbar():
    s = QualitySettings(severity_weights={"error": 1.0, "warn": 0.5})
    r = evaluate_architecture(_arch([_rule(1), _rule(2), _rule(3, "warn"), _rule(4, "warn")]),
                              _graph(4), s)
    assert r.node.score() == pytest.approx(0.4)


def test_quorum_ueber_regeln():
    regeln = [_rule(1), _rule(2, kind="forbidden_call", **{"in": "src", "calls": ["x"]}),
              _rule(3, kind="write_ownership", paths=["y/**"], owners="src")]
    r = evaluate_architecture(_arch(regeln), _graph(1), QualitySettings())
    assert r.node.score() is None
    assert [n["rule"] for n in r.rules_na] == ["ARCH-02", "ARCH-03"]
    assert all("Kantenart" in n["reason"] for n in r.rules_na)


def test_unbekannte_schicht():
    r = evaluate_architecture(_arch([_rule(1, **{"from": "gibtsnicht", "to_layers": ["src"]})]),
                              _graph(0), QualitySettings())
    assert "unbekannte Schicht" in r.rules_na[0]["reason"]


def test_ohne_graph_oder_regeln_na():
    assert evaluate_architecture(_arch([_rule(1)]), None, QualitySettings(),
                                 graph_reason="Sonde imports: Befehl nicht gefunden"
                                 ).node.score() is None
    assert evaluate_architecture(_arch([]), _graph(0), QualitySettings()).node.score() is None


def test_unaufgeloeste_kanten_werden_gezaehlt():
    g = DepsGraph(frozenset({"import"}), [Edge("src/a.py", None, "import", "d", "src/a.py", 1,
                                                (), True)])
    r = evaluate_architecture(_arch([_rule(1)]), g, QualitySettings())
    assert r.unresolved_edges == 1 and r.violations == []
