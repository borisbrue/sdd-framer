"""TST-0224 – CON-0195: Quality-Report.

Spec: SPEC-0054 · Contract: CON-0195
Schematests laufen sofort. Die Querbeziehungen (INV-02, INV-03, INV-05, INV-06, INV-08) prüfen
einen echten Report von `sdd quality measure` und überspringen, solange der Befehl fehlt.
"""
from __future__ import annotations

import copy

import pytest
import yaml

from tests.support.quality_project import (
    QualityProject,
    fr_status,
    make_project,
    requires_quality_cli,
    schema_errors,
    standard_projekt,
)

REPORT = {
    "schema_version": 1, "spec": "SPEC-0900", "git_sha": "abc1234",
    "generated_at": "2026-09-25T10:00:00Z", "duration_ms": 4210, "incomplete": True,
    "score": 0.8333,
    "tree": {"name": "total", "weight": 1, "score": 0.8333, "renormalized": True, "children": [
        {"name": "requirements", "weight": 0.5, "score": 1.0},
        {"name": "architecture", "weight": 0.25, "score": 0.5},
        {"name": "code_quality", "weight": 0.25, "score": None, "reason": "alle Metriken n/a",
         "metrics": [{"name": "type_errors", "raw": None, "normalized": None,
                      "reason": "Sonde types: Befehl nicht gefunden"}]}]},
    "requirements": {"frs": [{"id": "FR-01", "status": "erfüllt", "tests": [
        {"name": "test_a", "status": "passed", "source": "junit_property"}]}]},
    "architecture": {"violations": [{"rule": "ARCH-01", "adr": "ADR-0007", "adr_title": "T",
                                     "file": "web/a.py", "line": 3, "symbol": "W",
                                     "severity": "warn", "baselined": True}],
                     "rules_na": [], "unresolved_edges": 2},
    "probes": [{"name": "types", "command": "mypy …", "format": "sarif", "status": "n/a",
                "reason": "Befehl nicht gefunden", "exit_code": 127, "duration_ms": 3}],
}


def _ohne(pfad: list, feld: str) -> dict:
    kopie = copy.deepcopy(REPORT)
    ziel = kopie
    for teil in pfad:
        ziel = ziel[teil]
    del ziel[feld]
    return kopie


@pytest.fixture()
def qproject(tmp_path, monkeypatch) -> QualityProject:
    return make_project(tmp_path, monkeypatch)


def test_tc01_valid_instance_passes():
    """Valide Instanz besteht Schema-Validierung (CON-0195)."""
    assert schema_errors("report", REPORT) == []


def test_tc02_invalid_instance_rejected():
    """Score außerhalb [0, 1] wird abgelehnt (CON-0195)."""
    kaputt = copy.deepcopy(REPORT)
    kaputt["score"] = 1.2
    assert schema_errors("report", kaputt)


class TestSchemaInvarianten:
    def test_inv01_score_ist_zahl_oder_null(self):
        kaputt = copy.deepcopy(REPORT)
        kaputt["tree"]["children"][0]["score"] = "n/a"
        assert schema_errors("report", kaputt)

    def test_inv04_null_knoten_braucht_reason(self):
        assert schema_errors("report", _ohne(["tree", "children", 2], "reason"))

    def test_inv04_null_metrik_braucht_reason(self):
        assert schema_errors("report", _ohne(["tree", "children", 2, "metrics", 0], "reason"))

    def test_inv04_na_sonde_braucht_reason(self):
        assert schema_errors("report", _ohne(["probes", 0], "reason"))

    def test_inv05_fr_status_geschlossen(self):
        kaputt = copy.deepcopy(REPORT)
        kaputt["requirements"]["frs"][0]["status"] = "ok"
        assert schema_errors("report", kaputt)

    def test_inv07_verstoss_braucht_adr_und_symbol(self):
        assert schema_errors("report", _ohne(["architecture", "violations", 0], "adr"))
        assert schema_errors("report", _ohne(["architecture", "violations", 0], "symbol"))


@requires_quality_cli
class TestQuerbeziehungen:
    def _report(self, p: QualityProject, **kw: object) -> dict:
        standard_projekt(p, **kw)
        _, report = p.measure("--spec", "SPEC-0900")
        assert schema_errors("report", report) == []
        return report

    def test_inv02_score_gleich_wurzel(self, qproject: QualityProject):
        report = self._report(qproject)
        assert report["score"] == report["tree"]["score"]

    def test_inv03_incomplete_genau_bei_null_im_baum(self, qproject: QualityProject):
        report = self._report(qproject)
        assert report["incomplete"] is False

        def hat_null(k: dict) -> bool:
            eigen = k.get("score", k.get("normalized")) is None
            return eigen or any(hat_null(c) for c in k.get("children", []) + k.get("metrics", []))

        assert hat_null(report["tree"]) is False

    def test_inv05_jede_fr_genau_einmal(self, qproject: QualityProject):
        report = self._report(qproject, frs=["FR-01", "FR-02", "FR-03"],
                              tests=[("t1", "passed", ["FR-01"])])
        ids = [fr["id"] for fr in report["requirements"]["frs"]]
        assert ids == ["FR-01", "FR-02", "FR-03"]
        assert fr_status(report)["FR-02"] == "fehlt"

    def test_inv06_unbekannt_nur_bei_ausgefallener_testsonde(self, qproject: QualityProject):
        standard_projekt(qproject, frs=["FR-01", "FR-02"])
        pfad = qproject.root / ".sdd/quality.yaml"
        daten = yaml.safe_load(pfad.read_text())
        daten["probes"]["tests"]["command"] = "gibt-es-nicht-4711 > {out}"
        pfad.write_text(yaml.safe_dump(daten))
        _, report = qproject.measure("--spec", "SPEC-0900")
        assert set(fr_status(report).values()) == {"unbekannt"}
        assert report["tree"]["children"][0]["score"] is None

    def test_status_not_run_bei_zugeordnetem_aber_nicht_gelaufenem_test(
        self, qproject: QualityProject
    ):
        standard_projekt(qproject, frs=["FR-01"], tests=[("a", "passed", ["FR-01"])])
        qproject.spec(["FR-01"], fr_test_map={"FR-01": ["test_gibt_es_nicht"]})
        _, report = qproject.measure("--spec", "SPEC-0900")
        tests = {t["name"]: t for t in report["requirements"]["frs"][0]["tests"]}
        assert tests["test_gibt_es_nicht"]["status"] == "not_run"
        assert tests["test_gibt_es_nicht"]["source"] == "fr_test_map"

    def test_inv08_sonden_vollstaendig_in_reihenfolge(self, qproject: QualityProject):
        report = self._report(qproject)
        assert [s["name"] for s in report["probes"]] == ["tests", "metriken", "imports"]
