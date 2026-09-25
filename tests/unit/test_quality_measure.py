"""SPEC-0054 FR-01/FR-12: Messung orchestrieren (Facade)."""
from __future__ import annotations

import pytest

from sdd_cli.quality.measure import measure
from sdd_cli.quality.schemas import validator
from tests.support.quality_project import make_project, standard_projekt


@pytest.fixture()
def qproject(tmp_path, monkeypatch):
    return make_project(tmp_path, monkeypatch)


def test_ergebnis_ist_schema_gueltig_und_vollstaendig(qproject):
    standard_projekt(qproject, frs=["FR-01", "FR-02"],
                     tests=[("a", "passed", ["FR-01"]), ("b", "failed", ["FR-02"])])
    ergebnis = measure(qproject.root, spec_id="SPEC-0900")
    r = ergebnis.report
    assert list(validator("quality-report").iter_errors(r)) == []
    assert [p["name"] for p in r["probes"]] == ["tests", "metriken", "imports"]
    assert {f["id"]: f["status"] for f in r["requirements"]["frs"]} == {"FR-01": "erfüllt",
                                                                        "FR-02": "fehlt"}
    assert ergebnis.exit_code == 0


def test_ohne_spec_ist_requirements_na(qproject):
    standard_projekt(qproject)
    r = measure(qproject.root).report
    req = {c["name"]: c for c in r["tree"]["children"]}["requirements"]
    assert req["score"] is None and "keine Spec" in req["reason"]
