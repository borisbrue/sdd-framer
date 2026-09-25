"""SPEC-0054 FR-12, CON-0195: Report-Builder erzeugt schema-gültige Reports."""
from __future__ import annotations

from sdd_cli.quality.report import build_report
from sdd_cli.quality.schemas import validator
from sdd_cli.quality.score import MetricLeaf, ScoreNode


def test_minimaler_report_ist_schema_gueltig():
    tree = ScoreNode("total", 1, [
        ScoreNode("requirements", 0.5, [MetricLeaf("fr_fulfilled", 1.0, 1.0)], policy="strict"),
        ScoreNode("code_quality", 0.25, [MetricLeaf("m", None, None, reason="weg")])])
    report = build_report(tree=tree, git_sha="abc1234", duration_ms=5, spec_id="SPEC-0900",
                          base_ref=None, frs=[], holdout_rate=None, test_run=None,
                          architecture={"violations": [], "rules_na": [], "unresolved_edges": 0},
                          probes=[], gates=None, excluded=0)
    assert list(validator("quality-report").iter_errors(report)) == []
    assert report["score"] == report["tree"]["score"] == 1.0
    assert report["incomplete"] is True
    assert report["requirements"]["holdout_pass_rate"] is None
