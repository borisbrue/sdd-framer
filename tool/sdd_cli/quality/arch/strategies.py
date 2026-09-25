"""Eine Strategie je Regelart (SPEC-0054 §3 Strategy, CON-0194 INV-03..INV-06, INV-09).

Jede Strategie bekommt Regel, Graph und Schichten und liefert alle Verstöße, ohne
Kurzschluss. Ob die benötigte Kantenart vorhanden ist, prüft der Evaluator.
"""
from __future__ import annotations

import re
from functools import cache

from ..files import glob_match, matches_any
from ..parsers import DepsGraph, Edge
from .rules import Rule, layer_of


class RuleStrategy:
    kind = ""
    edge_kind = "import"

    def evaluate(self, rule: Rule, graph: DepsGraph, layers: dict[str, list[str]]) -> list:
        from .evaluator import Violation

        return [Violation(rule=rule.id, adr=rule.adr, file=e.file, line=e.line, symbol=e.symbol,
                          severity=rule.severity)
                for e in graph.edges
                if e.kind == self.edge_kind and self.violates(rule, e, layers)]

    def violates(self, rule: Rule, edge: Edge, layers: dict[str, list[str]]) -> bool:
        raise NotImplementedError


class ForbiddenDependency(RuleStrategy):
    kind = "forbidden_dependency"

    def violates(self, rule: Rule, edge: Edge, layers: dict[str, list[str]]) -> bool:
        if edge.unresolved or edge.target is None:
            return False
        if layer_of(edge.source, layers) not in rule.layers("from"):
            return False
        ziel_schicht = layer_of(edge.target, layers)
        return (ziel_schicht in rule.layers("to_layers")
                or matches_any(edge.target, rule.layers("to_paths")))


class AllowedDependencies(RuleStrategy):
    kind = "allowed_dependencies"

    def violates(self, rule: Rule, edge: Edge, layers: dict[str, list[str]]) -> bool:
        if edge.unresolved or edge.target is None:
            return False
        quelle, ziel = layer_of(edge.source, layers), layer_of(edge.target, layers)
        if quelle is None or ziel is None or quelle == ziel:
            return False
        return ziel not in (rule.params.get("graph") or {}).get(quelle, [])


@cache
def _call_regex(pattern: str) -> re.Pattern[str]:
    return re.compile("".join("[^.]*" if ch == "*" else re.escape(ch) for ch in pattern) + r"\Z")


class ForbiddenCall(RuleStrategy):
    kind = "forbidden_call"
    edge_kind = "call"

    def violates(self, rule: Rule, edge: Edge, layers: dict[str, list[str]]) -> bool:
        if layer_of(edge.source, layers) not in rule.layers("in"):
            return False
        if matches_any(edge.file, rule.layers("except")):
            return False
        if not any(_call_regex(p).match(edge.symbol) for p in rule.layers("calls")):
            return False
        muster = rule.params.get("args_match")
        return muster is None or any(re.search(muster, a) for a in edge.args)


class WriteOwnership(RuleStrategy):
    kind = "write_ownership"
    edge_kind = "write"

    def violates(self, rule: Rule, edge: Edge, layers: dict[str, list[str]]) -> bool:
        if edge.unresolved or edge.target is None:
            # CON-0208: mit `unresolved: violation` zählt ein Schreibzugriff mit unbekanntem Ziel
            # aus einer Schicht außerhalb der owners; Dateien ohne Schicht bleiben ausgenommen.
            if rule.params.get("unresolved", "skip") != "violation":
                return False
            schicht = layer_of(edge.source, layers)
            return schicht is not None and schicht not in rule.layers("owners")
        if not any(glob_match(edge.target, p) for p in rule.layers("paths")):
            return False
        return layer_of(edge.source, layers) not in rule.layers("owners")


STRATEGIES: dict[str, RuleStrategy] = {
    s.kind: s for s in (ForbiddenDependency(), AllowedDependencies(), ForbiddenCall(),
                        WriteOwnership())
}


def required_kind(kind: str) -> str:
    return STRATEGIES[kind].edge_kind
