"""SPEC-0054 FR-08, CON-0196 (Teilnahme eingebauter Metriken, lint_per_kloc)."""
from __future__ import annotations

import pytest

from sdd_cli.quality.config import Probe, QualityConfig
from sdd_cli.quality.metrics import builtin_metrics
from sdd_cli.quality.parsers import Finding, FindingsResult
from sdd_cli.quality.probe import ProbeOutcome
from sdd_cli.quality.settings import QualitySettings


def _finding(file="src/a.py", severity="warning"):
    return Finding("R", "m", file, 1, severity)


def _ok(name, metric, findings):
    return ProbeOutcome(Probe(name, "x {out}", "sarif", metric=metric), "ok", "x {out}",
                        result=FindingsResult(findings))


@pytest.fixture()
def projekt(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src/a.py").write_text("x = 1  # SUPPRESS\n" * 500)
    (tmp_path / "src/b.py").write_text("y = 2\n" * 500)
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/t.py").write_text("t\n" * 250)
    return tmp_path


def _metrics(projekt, outcomes, cfg=None, changed=None, files=None):
    cfg = cfg or QualityConfig(probes=[o.probe for o in outcomes])
    files = files or ["src/a.py", "src/b.py"]
    leaves = builtin_metrics(outcomes, cfg, projekt, files, changed, QualitySettings())
    return {m.name: m for m in leaves}


def test_nicht_konfigurierte_metriken_fehlen_ganz(projekt):
    assert _metrics(projekt, []) == {}


def test_lint_per_kloc_ohne_notes(projekt):
    m = _metrics(projekt, [_ok("lint", "lint_per_kloc",
                                [_finding(), _finding(), _finding(), _finding(severity="note")])])
    assert m["lint_per_kloc"].raw == pytest.approx(3.0)
    assert m["lint_per_kloc"].normalized == pytest.approx(0.7)
    assert m["lint_per_kloc"].source_probe == "lint"


def test_lint_per_kloc_ignoriert_ausgeschlossene_dateien(projekt):
    cfg = QualityConfig(probes=[], exclude=["vendor/**"])
    outcome = _ok("lint", "lint_per_kloc", [_finding(), _finding("vendor/x.py")])
    cfg.probes.append(outcome.probe)
    m = _metrics(projekt, [outcome], cfg=cfg)
    assert m["lint_per_kloc"].raw == pytest.approx(1.0)


def test_type_errors_zaehlt(projekt):
    m = _metrics(projekt, [_ok("types", "type_errors", [_finding()] * 5)])
    assert m["type_errors"].raw == 5 and m["type_errors"].normalized == pytest.approx(0.75)


def test_ausgefallene_metrik_sonde_wird_na(projekt):
    o = ProbeOutcome(Probe("types", "x {out}", "sarif", metric="type_errors"), "n/a", "x",
                     reason="Befehl nicht gefunden")
    m = _metrics(projekt, [o])
    assert m["type_errors"].normalized is None
    assert "Befehl nicht gefunden" in m["type_errors"].reason


def test_suppressions_nur_mit_mustern(projekt):
    cfg = QualityConfig(probes=[], suppressions={"**/*.py": [r"#\s*SUPPRESS"]})
    m = _metrics(projekt, [], cfg=cfg)
    assert m["suppressions"].raw == 500


def test_test_ratio_nur_mit_diff_und_test_paths(projekt):
    cfg = QualityConfig(probes=[], test_paths=["tests/**"])
    assert "test_ratio" not in _metrics(projekt, [], cfg=cfg)
    m = _metrics(projekt, [], cfg=cfg, changed=["src/a.py", "tests/t.py"])
    assert m["test_ratio"].raw == pytest.approx(0.5)
    assert m["test_ratio"].normalized == pytest.approx(0.5)


def test_eigene_normierung_schlaegt_eingebaute(projekt):
    from sdd_cli.quality.config import Normalization

    outcome = _ok("lint", "lint_per_kloc", [_finding()] * 2)
    cfg = QualityConfig(probes=[outcome.probe],
                        normalization={"lint_per_kloc": Normalization(0, 4)})
    assert _metrics(projekt, [outcome], cfg=cfg)["lint_per_kloc"].normalized == pytest.approx(0.5)
