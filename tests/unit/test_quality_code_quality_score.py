"""SPEC-0054 FR-08/FR-11, CON-0196: Codequalitäts-Teilscore aus allen Sonden."""
from __future__ import annotations

import pytest

from sdd_cli.quality.config import Normalization, Probe, QualityConfig
from sdd_cli.quality.metrics import code_quality_node
from sdd_cli.quality.parsers import Metric, MetricsResult
from sdd_cli.quality.probe import ProbeOutcome
from sdd_cli.quality.settings import QualitySettings


def _metrics_probe(name, werte, status="ok", reason=None):
    p = Probe(name, "x {out}", "sdd-metrics")
    res = MetricsResult([Metric(k, v) for k, v in werte.items()]) if status == "ok" else None
    return ProbeOutcome(p, status, "x {out}", result=res, reason=reason)


def _node(outcomes, norm, settings=None):
    cfg = QualityConfig(probes=[o.probe for o in outcomes],
                        normalization={k: Normalization(*v) for k, v in norm.items()})
    return code_quality_node(outcomes, cfg, None, [], None, settings or QualitySettings())


def test_sdd_metrics_mit_normierung():
    n = _node([_metrics_probe("m", {"a": 4})], {"a": (0, 10)})
    assert n.score() == pytest.approx(0.6)


def test_metrik_ohne_normierung_ist_na():
    n = _node([_metrics_probe("m", {"a": 4, "b": 2})], {"a": (0, 10)})
    leaves = {c.name: c for c in n.children}
    assert leaves["b"].normalized is None and leaves["b"].reason == "Normierung fehlt"
    assert n.score() == pytest.approx(0.6) and n.renormalized()


def test_ausgefallene_sonde_ohne_metric_erscheint_mit_sondennamen():
    n = _node([_metrics_probe("m", {"a": 4}),
               _metrics_probe("zweite", {}, status="n/a", reason="Befehl nicht gefunden")],
              {"a": (0, 10)})
    leaves = {c.name: c for c in n.children}
    assert leaves["zweite"].normalized is None
    assert leaves["zweite"].reason == "Befehl nicht gefunden"
    assert n.score() == pytest.approx(0.6) and n.renormalized()


def test_dateibezogene_werte_zaehlen_nicht():
    p = Probe("m", "x {out}", "sdd-metrics")
    o = ProbeOutcome(p, "ok", "x", result=MetricsResult([Metric("a", 4), Metric("a", 9, "f.py")]))
    n = _node([o], {"a": (0, 10)})
    assert [c.name for c in n.children] == ["a"]


def test_gewichte_je_metrik():
    s = QualitySettings(metric_weights={"a": 3})
    n = _node([_metrics_probe("m", {"a": 10, "b": 0})], {"a": (0, 10), "b": (0, 10)}, s)
    assert n.score() == pytest.approx(0.25)


def test_rollen_sonden_gehoeren_nicht_zur_codequalitaet():
    t = ProbeOutcome(Probe("t", "x {out}", "junit", role="tests", fr_marker="name"), "n/a", "x",
                     reason="Befehl nicht gefunden")
    n = _node([t, _metrics_probe("m", {"a": 0})], {"a": (0, 10)})
    assert [c.name for c in n.children] == ["a"]
