"""SPEC-0054 §3 Composite, FR-11, CON-0196: Score-Baum mit n/a-Regeln."""
from __future__ import annotations

import pytest

from sdd_cli.quality.score import MetricLeaf, ScoreNode


def _leaf(name, wert, gewicht=1.0):
    return MetricLeaf(name=name, raw=wert, normalized=wert, weight=gewicht,
                      reason=None if wert is not None else "ausgefallen")


def test_gewichteter_mittelwert():
    wurzel = ScoreNode("total", 1, [ScoreNode("r", 0.5, [_leaf("a", 1.0)]),
                                    ScoreNode("a", 0.25, [_leaf("b", 0.5)]),
                                    ScoreNode("c", 0.25, [_leaf("c", 0.8)])])
    assert wurzel.score() == pytest.approx(0.825)
    assert not wurzel.renormalized() and not wurzel.incomplete()


def test_renormalize():
    wurzel = ScoreNode("total", 1, [ScoreNode("r", 0.5, [_leaf("a", 1.0)]),
                                    ScoreNode("a", 0.25, [_leaf("b", 0.5)]),
                                    ScoreNode("c", 0.25, [_leaf("c", None)])])
    assert wurzel.score() == pytest.approx(0.8333, abs=1e-4)
    assert wurzel.renormalized() and wurzel.incomplete()
    assert wurzel.children[2].score() is None


def test_gewicht_null_zaehlt_nicht_und_renormiert_nicht():
    wurzel = ScoreNode("total", 1, [ScoreNode("r", 1, [_leaf("a", 1.0)]),
                                    ScoreNode("judge", 0, [_leaf("j", 0.2)])])
    assert wurzel.score() == pytest.approx(1.0)
    assert not wurzel.renormalized()


def test_strict():
    k = ScoreNode("req", 1, [_leaf("a", 1.0), _leaf("b", None)], policy="strict")
    assert k.score() is None


@pytest.mark.parametrize(("werte", "erwartet"), [
    ([0.4, None, 0.8], 0.6),           # 1/3 n/a ≤ 0,5 → renormalisiert
    ([None, None, 0.8], None),          # 2/3 n/a > 0,5 → n/a
])
def test_quorum(werte, erwartet):
    k = ScoreNode("arch", 1, [_leaf(f"r{i}", w) for i, w in enumerate(werte)],
                  policy="quorum", quorum=0.5)
    assert k.score() == (pytest.approx(erwartet) if erwartet is not None else None)


def test_eigene_aggregation():
    k = ScoreNode("arch", 1, [_leaf("r1", 2.0), _leaf("r2", 0.5)],
                  aggregate=lambda kinder: 1 - min(1.0, sum(c.raw for c in kinder) / 5))
    assert k.score() == pytest.approx(0.5)


def test_leerer_knoten_ist_na():
    assert ScoreNode("x", 1, []).score() is None


def test_erzwungenes_na():
    k = ScoreNode("x", 1, [_leaf("a", 1.0)], forced_reason="keine Regeln")
    assert k.score() is None and k.reason == "keine Regeln"


def test_serialisierung():
    wurzel = ScoreNode("total", 1, [ScoreNode("c", 0.25, [_leaf("m", None)], reason="alle n/a")])
    d = wurzel.to_dict()
    assert d["name"] == "total" and d["score"] is None
    kind = d["children"][0]
    assert kind["metrics"][0] == {"name": "m", "raw": None, "normalized": None, "weight": 1.0,
                                  "reason": "ausgefallen"}
    assert kind["reason"] == "alle n/a"


def test_versteckte_kinder_werden_nicht_serialisiert():
    k = ScoreNode("arch", 1, [_leaf("r1", 1.0)], hide_children=True)
    assert "metrics" not in k.to_dict() and "children" not in k.to_dict()
