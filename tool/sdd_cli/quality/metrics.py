"""Codequalitäts-Teilscore (SPEC-0054 FR-08, CON-0196).

Eingebaut und sprachneutral sind nur `lint_per_kloc`, `type_errors`, `suppressions` und
`test_ratio`; sie nehmen nur teil, wenn ihre Quelle konfiguriert ist. Alle weiteren
Metriken liefern Projekt-Sonden als `sdd-metrics`, Cobertura oder LCOV.
"""
from __future__ import annotations

import re
from pathlib import Path

from .config import QualityConfig
from .files import glob_match, matches_any
from .normalize import BUILTIN_NORMALIZATION, normalize
from .parsers import FindingsResult, MetricsResult
from .probe import ProbeOutcome
from .score import MetricLeaf, ScoreNode
from .settings import QualitySettings

LINT = "lint_per_kloc"
TYPES = "type_errors"
FINDING_METRICS = (LINT, TYPES)
REASON_NO_NORMALIZATION = "Normierung fehlt"


def _grenzen(name: str, cfg: QualityConfig) -> tuple[float, float] | None:
    if name in cfg.normalization:
        n = cfg.normalization[name]
        return n.good, n.bad
    return BUILTIN_NORMALIZATION.get(name)


def metric_leaf(name: str, raw: float | None, cfg: QualityConfig, settings: QualitySettings,
                probe: str | None = None, reason: str | None = None) -> MetricLeaf:
    grenzen = _grenzen(name, cfg)
    if raw is not None and grenzen is None:
        reason, norm = REASON_NO_NORMALIZATION, None
    else:
        norm = None if raw is None else normalize(raw, *grenzen)
    return MetricLeaf(name=name, raw=raw, normalized=norm, weight=settings.metric_weight(name),
                      good=grenzen[0] if grenzen else None, bad=grenzen[1] if grenzen else None,
                      source_probe=probe, reason=reason if norm is None else None)


def _zeilen(root: Path, files: list[str]) -> int:
    summe = 0
    for rel in files:
        try:
            with (root / rel).open("rb") as f:
                summe += sum(1 for _ in f)
        except OSError:
            continue
    return summe


def _finding_metric(name: str, outcomes: list[ProbeOutcome], cfg: QualityConfig, root: Path,
                    files: list[str], settings: QualitySettings) -> MetricLeaf:
    ausgefallen = [o for o in outcomes if not o.ok]
    quellen = ", ".join(o.probe.name for o in outcomes)
    if ausgefallen:
        grund = "; ".join(f"Sonde {o.probe.name}: {o.reason}" for o in ausgefallen)
        return metric_leaf(name, None, cfg, settings, quellen, grund)
    anzahl = sum(
        1 for o in outcomes if isinstance(o.result, FindingsResult)
        for f in o.result.findings
        if f.severity != "note" and not matches_any(f.file, cfg.exclude)
    )
    if name == LINT:
        zeilen = _zeilen(root, files)
        if zeilen == 0:
            return metric_leaf(name, None, cfg, settings, quellen, "keine gemessenen Zeilen")
        return metric_leaf(name, anzahl / (zeilen / 1000), cfg, settings, quellen)
    return metric_leaf(name, float(anzahl), cfg, settings, quellen)


def _suppressions(cfg: QualityConfig, root: Path, files: list[str]) -> int:
    muster = [(glob, [re.compile(r) for r in regexe]) for glob, regexe in cfg.suppressions.items()]
    treffer = 0
    for rel in files:
        regexe = [r for glob, rs in muster if glob_match(rel, glob) for r in rs]
        if not regexe:
            continue
        try:
            text = (root / rel).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        treffer += sum(len(r.findall(text)) for r in regexe)
    return treffer


def builtin_metrics(outcomes: list[ProbeOutcome], cfg: QualityConfig, root: Path,
                    files: list[str], changed: list[str] | None,
                    settings: QualitySettings) -> list[MetricLeaf]:
    leaves = []
    for name in FINDING_METRICS:
        quellen = [o for o in outcomes if o.probe.metric == name and o.probe.role is None]
        if quellen:
            leaves.append(_finding_metric(name, quellen, cfg, root, files, settings))
    if cfg.suppressions:
        leaves.append(metric_leaf("suppressions", float(_suppressions(cfg, root, files)), cfg,
                                  settings))
    if changed is not None and cfg.test_paths:
        tests = [f for f in changed if matches_any(f, cfg.test_paths)]
        prod = [f for f in changed if f not in tests]
        prod_zeilen = _zeilen(root, prod)
        if prod_zeilen:
            leaves.append(metric_leaf("test_ratio", _zeilen(root, tests) / prod_zeilen, cfg,
                                      settings))
        else:
            leaves.append(metric_leaf("test_ratio", None, cfg, settings,
                                      reason="keine geänderten Produktionszeilen"))
    return leaves


def probe_metrics(outcomes: list[ProbeOutcome], cfg: QualityConfig,
                  settings: QualitySettings) -> list[MetricLeaf]:
    """Metriken aus Sonden ohne Rolle: sdd-metrics, Cobertura, LCOV; Ausfälle unter ihrem Namen."""
    leaves = []
    for o in outcomes:
        if o.probe.role is not None or o.probe.metric in FINDING_METRICS:
            continue
        if not o.ok:
            name = o.probe.metric or o.probe.name
            leaves.append(metric_leaf(name, None, cfg, settings, o.probe.name, o.reason))
        elif isinstance(o.result, MetricsResult):
            leaves.extend(metric_leaf(m.name, m.value, cfg, settings, o.probe.name)
                          for m in o.result.metrics if m.scope == "project")
    return leaves


def code_quality_node(outcomes: list[ProbeOutcome], cfg: QualityConfig, root: Path | None,
                      files: list[str], changed: list[str] | None,
                      settings: QualitySettings) -> ScoreNode:
    leaves = [*builtin_metrics(outcomes, cfg, root or Path("."), files, changed, settings),
              *probe_metrics(outcomes, cfg, settings)]
    return ScoreNode("code_quality", settings.root_weights["code_quality"], leaves,
                     policy="renormalize")
