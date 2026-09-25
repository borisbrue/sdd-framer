"""TST-0222 – CON-0193: Austauschformate sdd-deps, sdd-metrics, sdd-findings.

Spec: SPEC-0054 · Contract: CON-0193
Schematests laufen sofort. Die Gleichwertigkeit mit SARIF (INV-08) und der Umgang mit
unparsebaren Dateien (INV-01) prüfen `sdd quality measure` und überspringen, solange er fehlt.
"""
from __future__ import annotations

import pytest
import yaml

from tests.support.quality_project import (
    QualityProject,
    findings,
    make_project,
    requires_quality_cli,
    sarif,
    schema_errors,
    score,
    standard_projekt,
)

DEPS = {
    "format": "sdd-deps", "version": 1, "tool": {"name": "extract_deps.py", "version": "1.0.0"},
    "kinds_provided": ["import", "call", "write"],
    "edges": [
        {"from": "tool/a.py", "to": "tool/b.py", "kind": "import", "symbol": "B",
         "file": "tool/a.py", "line": 3},
        {"from": "tool/a.py", "to": None, "kind": "call", "symbol": "subprocess.run",
         "args": ["claude"], "file": "tool/a.py", "line": 9, "unresolved": True},
        {"from": "tool/w.py", "to": ".sdd/specs/SPEC-0001.md", "kind": "write",
         "symbol": "pathlib.Path.write_text", "file": "tool/w.py", "line": 42},
    ],
}


def _kante(**felder: object) -> dict:
    basis = {"from": "a.py", "to": "b.py", "kind": "import", "symbol": "b", "file": "a.py",
             "line": 1}
    return {**DEPS, "edges": [{**basis, **felder}]}


@pytest.fixture()
def qproject(tmp_path, monkeypatch) -> QualityProject:
    return make_project(tmp_path, monkeypatch)


def test_tc01_valid_instance_passes():
    """Valide Instanzen aller drei Formate bestehen (CON-0193)."""
    assert schema_errors("exchange", DEPS) == []
    assert schema_errors("exchange", {"format": "sdd-metrics", "version": 1, "metrics": [
        {"name": "complexity_max", "value": 12, "scope": "project"},
        {"name": "complexity", "value": 4, "scope": "tool/a.py", "unit": "mccabe"}]}) == []
    assert schema_errors("exchange", {"format": "sdd-findings", "version": 1, "findings": [
        {"rule": "E501", "message": "zu lang", "file": "a.go", "line": 7, "column": 2,
         "severity": "warning"}]}) == []


def test_tc02_invalid_instance_rejected():
    """Beispiel aus dem Contract: '..', to null ohne unresolved, args bei import."""
    assert schema_errors("exchange", {**DEPS, "edges": [
        {"from": "../other/x.py", "to": None, "kind": "import", "symbol": "x", "args": ["a"],
         "file": "x.py", "line": 1}]})


class TestInvarianten:
    def test_inv01_format_und_version_pflicht(self):
        ohne = {k: v for k, v in DEPS.items() if k != "version"}
        assert schema_errors("exchange", ohne)

    @pytest.mark.parametrize("pfad", ["/abs/a.py", "../a.py", "a/../../b.py", "a\\b.py"])
    def test_inv02_nur_relative_pfade(self, pfad):
        assert schema_errors("exchange", _kante(**{"from": pfad}))

    def test_inv03_kinds_provided_pflicht_und_nicht_leer(self):
        assert schema_errors("exchange", {**DEPS, "kinds_provided": []})

    def test_inv04_to_null_verlangt_unresolved(self):
        assert schema_errors("exchange", _kante(to=None))
        assert not schema_errors("exchange", _kante(to=None, unresolved=True))

    def test_inv05_symbol_pflicht(self):
        kante = _kante()
        del kante["edges"][0]["symbol"]
        assert schema_errors("exchange", kante)

    @pytest.mark.parametrize("art", ["import", "write"])
    def test_inv05_args_nur_bei_call(self, art):
        assert schema_errors("exchange", _kante(kind=art, args=["x"]))

    def test_inv06_metrikname_snake_case(self):
        assert schema_errors("exchange", {"format": "sdd-metrics", "version": 1,
                                          "metrics": [{"name": "Complexity-Max", "value": 1}]})

    def test_inv07_severity_geschlossen(self):
        assert schema_errors("exchange", {"format": "sdd-findings", "version": 1, "findings": [
            {"rule": "r", "message": "m", "file": "a", "line": 1, "severity": "fatal"}]})


@requires_quality_cli
class TestVerbraucher:
    def _mit_befunden(self, p: QualityProject, sonde: dict) -> dict:
        standard_projekt(p)
        daten = yaml.safe_load((p.root / ".sdd/quality.yaml").read_text())
        daten["probes"]["lint"] = sonde
        (p.root / ".sdd/quality.yaml").write_text(yaml.safe_dump(daten))
        _, report = p.measure()
        return report

    def test_inv08_sarif_und_sdd_findings_sind_gleichwertig(self, tmp_path, monkeypatch):
        befunde = [{"rule": "E1", "file": "src/app.py", "line": 1},
                   {"rule": "E2", "file": "src/app.py", "line": 2, "level": "error"},
                   {"rule": "N1", "file": "src/app.py", "line": 3, "level": "note"}]
        a = make_project(tmp_path / "a", monkeypatch)
        rep_a = self._mit_befunden(a, a.fixture_probe("lint", sarif(befunde), "sarif",
                                                      metric="lint_per_kloc"))
        b = make_project(tmp_path / "b", monkeypatch)
        als_findings = [{"rule": x["rule"], "file": x["file"], "line": x["line"],
                         "severity": {"error": "error", "note": "note"}.get(
                             x.get("level", ""), "warning")} for x in befunde]
        rep_b = self._mit_befunden(b, b.fixture_probe("lint", findings(als_findings),
                                                      "sdd-findings", metric="lint_per_kloc"))
        assert score(rep_a, "code_quality.lint_per_kloc") == score(
            rep_b, "code_quality.lint_per_kloc")

    def test_inv01_unparsebare_datei_macht_sonde_na(self, qproject: QualityProject):
        report = self._mit_befunden(qproject, qproject.fixture_probe(
            "lint", '{"format": "sdd-findings", "version": 1}', "sdd-findings",
            metric="lint_per_kloc"))
        sonde = {s["name"]: s for s in report["probes"]}["lint"]
        assert sonde["status"] == "n/a"
        assert sonde["reason"] == "Ausgabe nicht parsebar"
