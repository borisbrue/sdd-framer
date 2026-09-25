"""SPEC-0054 FR-13, CON-0197: CLI sdd quality doctor."""
from __future__ import annotations

import pytest

from tests.support.quality_project import make_project, standard_projekt


@pytest.fixture()
def qproject(tmp_path, monkeypatch):
    return make_project(tmp_path, monkeypatch)


def test_alles_bereit(qproject):
    standard_projekt(qproject)
    ergebnis = qproject.run("quality", "doctor")
    assert ergebnis.exit_code == 0, ergebnis.output
    for name in ("tests", "metriken", "imports"):
        assert name in ergebnis.output


def test_testsonde_ohne_fr_markierung_wird_gemeldet(qproject):
    standard_projekt(qproject, tests=[("t", "passed", [])])
    ergebnis = qproject.run("quality", "doctor")
    assert "keine FR-Markierung" in ergebnis.output
