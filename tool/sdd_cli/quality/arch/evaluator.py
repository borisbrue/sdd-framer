"""Auswertung der Architekturregeln und Teilscore `architecture` (SPEC-0054 FR-05, CON-0196)."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ...frontmatter import parse_safe
from ..parsers import DepsGraph
from ..score import MetricLeaf, ScoreNode
from ..settings import QualitySettings
from .baseline import Baseline
from .rules import Architecture
from .strategies import STRATEGIES, required_kind


@dataclass(frozen=True)
class Violation:
    rule: str
    adr: str
    file: str
    line: int
    symbol: str
    severity: str
    baselined: bool = False
    fixed_by: str | None = None  # nur für die Textausgabe; der Report (CON-0195) kennt es nicht
    adr_title: str | None = None
    excerpt: str | None = None

    def to_dict(self) -> dict:
        d = {"rule": self.rule, "adr": self.adr, "file": self.file, "line": self.line,
             "symbol": self.symbol, "severity": self.severity, "baselined": self.baselined}
        if self.adr_title:
            d["adr_title"] = self.adr_title
        if self.excerpt:
            d["excerpt"] = self.excerpt
        return d


@dataclass
class ArchResult:
    node: ScoreNode
    violations: list[Violation] = field(default_factory=list)
    rules_na: list[dict] = field(default_factory=list)
    unresolved_edges: int = 0
    stale_baseline_entries: int = 0

    @property
    def errors(self) -> int:
        return sum(1 for v in self.violations if v.severity == "error")

    @property
    def warnings(self) -> int:
        return sum(1 for v in self.violations if v.severity == "warn")

    def to_dict(self) -> dict:
        return {"violations": [v.to_dict() for v in self.violations], "rules_na": self.rules_na,
                "unresolved_edges": self.unresolved_edges,
                "stale_baseline_entries": self.stale_baseline_entries}


def adr_titles(root: Path, adr_dir: str) -> dict[str, dict]:
    """ADR-ID → Frontmatter (für Titel, Status und enforced_by)."""
    verzeichnis = root / adr_dir
    ergebnis = {}
    for md in sorted(verzeichnis.glob("ADR-*.md")) if verzeichnis.is_dir() else []:
        doc = parse_safe(md)
        if doc and doc.frontmatter.get("id"):
            ergebnis[str(doc.frontmatter["id"])] = doc.frontmatter
    return ergebnis


def _auszug(root: Path | None, file: str, line: int) -> str | None:
    if root is None:
        return None
    try:
        zeilen = (root / file).read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    return zeilen[line - 1].strip()[:200] if 0 < line <= len(zeilen) else None


def evaluate_architecture(arch: Architecture, graph: DepsGraph | None,
                          settings: QualitySettings, *, adr_titles: dict[str, str] | None = None,
                          baseline: Baseline | None = None, root: Path | None = None,
                          graph_reason: str | None = None) -> ArchResult:
    titel = adr_titles or {}
    gewichte = settings.severity_weights
    alle: list[Violation] = []
    rules_na: list[dict] = []
    leaves: list[MetricLeaf] = []
    for rule in arch.rules:
        unbekannt = rule.unknown_layers(list(arch.layers))
        if unbekannt:
            grund = f"unbekannte Schicht: {', '.join(unbekannt)}"
        elif graph is None:
            grund = graph_reason or "keine Abhängigkeitssonde"
        elif required_kind(rule.kind) not in graph.kinds:
            grund = f"Kantenart {required_kind(rule.kind)!r} wird nicht geliefert"
        else:
            grund = None
        if grund:
            rules_na.append({"rule": rule.id, "reason": grund})
            leaves.append(MetricLeaf(rule.id.lower().replace("-", "_"), None, None, reason=grund))
            continue
        gefunden = [Violation(v.rule, v.adr, v.file, v.line, v.symbol, v.severity,
                              adr_title=titel.get(rule.adr), excerpt=_auszug(root, v.file, v.line))
                    for v in STRATEGIES[rule.kind].evaluate(rule, graph, arch.layers)]
        alle.extend(gefunden)
        leaves.append(MetricLeaf(rule.id.lower().replace("-", "_"), 0.0, 1.0))

    baseline = baseline or Baseline([])
    alle = baseline.apply(alle)
    summe = sum(gewichte.get(v.severity, 0.0) for v in alle)
    for leaf in leaves:
        if leaf.normalized is not None:
            leaf.raw = sum(gewichte.get(v.severity, 0.0) for v in alle
                           if v.rule.lower().replace("-", "_") == leaf.name)
    schwelle = settings.architecture_threshold

    forced = None
    if graph is None:
        forced = graph_reason or "keine Abhängigkeitssonde (role: deps)"
    elif not arch.rules:
        forced = "keine Regeln"
    node = ScoreNode("architecture", settings.root_weights["architecture"], leaves,
                     policy="quorum", quorum=0.5,
                     aggregate=lambda _kinder: 1 - min(1.0, summe / schwelle),
                     forced_reason=forced, hide_children=True)
    return ArchResult(node, alle, rules_na,
                      sum(1 for e in graph.edges if e.unresolved) if graph else 0,
                      baseline.stale)
