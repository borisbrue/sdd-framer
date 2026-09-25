"""TST-0221 – CON-0192: Quality-Config (.sdd/quality.yaml).

Spec: SPEC-0054 · Contract: CON-0192
Schematests (INV-01 bis INV-04) laufen sofort gegen das Contract-Artefakt; die Laufzeit-
Invarianten (INV-03, INV-05 bis INV-09) prüfen `sdd quality` und überspringen, solange der
Befehl fehlt.
"""
from __future__ import annotations

import pytest
import yaml

from tests.support.quality_project import (
    QualityProject,
    junit,
    make_project,
    metrics,
    requires_quality_cli,
    sarif,
    schema_errors,
    standard_projekt,
)


@pytest.fixture()
def qproject(tmp_path, monkeypatch) -> QualityProject:
    return make_project(tmp_path, monkeypatch)

GUELTIG = {
    "version": 1,
    "preset": "python",
    "probes": {
        "pytest": {"command": "pytest -q --junitxml={out}", "format": "junit",
                   "role": "tests", "fr_marker": "property"},
        "imports": {"command": "python .sdd/quality/extract_deps.py {paths} > {out}",
                    "format": "sdd-deps", "role": "deps"},
        "lint": {"command": "ruff check --output-format sarif --output-file {out} {paths}",
                 "format": "sarif", "metric": "lint_per_kloc", "diff_scoped": True,
                 "timeout_seconds": 120, "version_command": "ruff --version"},
        "complexity": {"command": "lizard --xml {paths} | conv > {out}", "format": "sdd-metrics"},
    },
    "normalization": {"complexity_max": {"good": 10, "bad": 30}},
    "suppressions": {"**/*.py": [r"#\s*noqa"]},
    "test_paths": ["tests/**"],
    "exclude": ["vendor/**"],
}


def _mit(**probe: object) -> dict:
    return {"version": 1, "probes": {"p": probe}}


def test_tc01_valid_instance_passes():
    """Valide Instanz besteht Schema-Validierung (CON-0192)."""
    assert schema_errors("quality_config", GUELTIG) == []


def test_tc02_invalid_instance_rejected():
    """Invalide Instanz wird abgelehnt (CON-0192): Beispiel aus dem Contract."""
    ungueltig = _mit(command="pytest -q", format="sarif", role="tests")
    assert schema_errors("quality_config", ungueltig)


class TestSchemaInvarianten:
    def test_inv01_befehl_braucht_out(self):
        assert schema_errors("quality_config", _mit(command="ruff check", format="sarif"))

    def test_inv02_testrolle_verlangt_junit_und_fr_marker(self):
        assert schema_errors("quality_config",
                             _mit(command="x {out}", format="sarif", role="tests",
                                  fr_marker="name"))
        assert schema_errors("quality_config",
                             _mit(command="x {out}", format="junit", role="tests"))
        assert not schema_errors("quality_config",
                                 _mit(command="x {out}", format="junit", role="tests",
                                      fr_marker="name"))

    def test_inv02_deps_rolle_verlangt_sdd_deps(self):
        assert schema_errors("quality_config", _mit(command="x {out}", format="sarif",
                                                    role="deps"))

    def test_inv02_name_tests_hat_keine_sonderbedeutung(self):
        """Ein Sondenname 'tests' ohne role ist eine gewöhnliche Sonde."""
        instanz = {"version": 1, "probes": {"tests": {"command": "x {out}", "format": "sarif"}}}
        assert schema_errors("quality_config", instanz) == []

    def test_inv03_fr_marker_nur_bei_testrolle(self):
        assert schema_errors("quality_config", _mit(command="x {out}", format="junit",
                                                    fr_marker="property"))

    def test_inv04_unbekanntes_format(self):
        assert schema_errors("quality_config", _mit(command="x {out}", format="checkstyle"))

    def test_normierung_braucht_good_und_bad(self):
        instanz = {**GUELTIG, "normalization": {"m": {"good": 0}}}
        assert schema_errors("quality_config", instanz)

    def test_unbekannte_felder_werden_abgelehnt(self):
        assert schema_errors("quality_config", _mit(command="x {out}", format="sarif",
                                                    shell="bash"))


@requires_quality_cli
class TestLaufzeitInvarianten:
    def test_inv03_zwei_sonden_derselben_rolle_sind_konfigurationsfehler(
        self, qproject: QualityProject
    ):
        qproject.spec(["FR-01"])
        a = qproject.fixture_probe("a", junit([]), "junit", role="tests", fr_marker="name")
        b = qproject.fixture_probe("b", junit([]), "junit", role="tests", fr_marker="name")
        qproject.quality_yaml({"eins": a, "zwei": b})
        ergebnis = qproject.run("quality", "measure")
        assert ergebnis.exit_code == 2
        assert "eins" in ergebnis.output and "zwei" in ergebnis.output

    def test_inv05_metrik_ohne_normierung_meldet_doctor(self, qproject: QualityProject):
        qproject.spec(["FR-01"])
        qproject.quality_yaml({"komplex": qproject.fixture_probe(
            "komplex", metrics({"complexity_max": 12}), "sdd-metrics")})
        ergebnis = qproject.run("quality", "doctor")
        assert ergebnis.exit_code == 1
        assert "Normierung fehlt" in ergebnis.output

    @pytest.mark.parametrize(
        ("befehl", "grund"),
        [
            ("gibt-es-nicht-4711 > {out}", "Befehl nicht gefunden"),
            ("sleep 5; echo > {out}", "Zeitlimit überschritten"),
            ("true", "keine Ausgabe"),
            ("echo kaputt > {out}", "Ausgabe nicht parsebar"),
            ("cat .sdd/holdout/x > {out}", "Holdout-Pfad verboten"),
        ],
    )
    def test_inv09_sondenausfall_mit_grund(self, qproject: QualityProject, befehl, grund):
        standard_projekt(qproject)
        daten = yaml.safe_load((qproject.root / ".sdd/quality.yaml").read_text())
        daten["probes"]["kaputt"] = {"command": befehl, "format": "sarif",
                                     "metric": "lint_per_kloc", "timeout_seconds": 1}
        (qproject.root / ".sdd/quality.yaml").write_text(yaml.safe_dump(daten))
        _, report = qproject.measure()
        sonde = {s["name"]: s for s in report["probes"]}["kaputt"]
        assert sonde["status"] == "n/a"
        assert sonde["reason"] == grund

    def test_inv09_exit_code_mit_gueltiger_ausgabe_ist_kein_ausfall(
        self, qproject: QualityProject
    ):
        standard_projekt(qproject)
        datei = qproject.write(".fixtures/lint.sarif",
                               sarif([{"rule": "E1", "file": "src/app.py", "line": 1}]))
        daten = yaml.safe_load((qproject.root / ".sdd/quality.yaml").read_text())
        daten["probes"]["lint"] = {"command": f"cp {datei} {{out}}; exit 1", "format": "sarif",
                                   "metric": "lint_per_kloc"}
        (qproject.root / ".sdd/quality.yaml").write_text(yaml.safe_dump(daten))
        _, report = qproject.measure()
        sonde = {s["name"]: s for s in report["probes"]}["lint"]
        assert sonde["status"] == "ok"
        assert sonde["exit_code"] == 1
