"""SPEC-0054 FR-01/FR-10, CON-0197: CLI sdd quality measure."""
from __future__ import annotations

import json

import pytest

from tests.support.quality_project import make_project, standard_projekt


@pytest.fixture()
def qproject(tmp_path, monkeypatch):
    return make_project(tmp_path, monkeypatch)


def test_json_nur_auf_stdout(qproject):
    standard_projekt(qproject)
    ergebnis = qproject.run("quality", "measure", "--json", "--spec", "SPEC-0900")
    assert ergebnis.exit_code == 0, ergebnis.output
    assert json.loads(ergebnis.stdout)["schema_version"] == 1


def test_tabelle_ohne_json(qproject):
    standard_projekt(qproject)
    ergebnis = qproject.run("quality", "measure", "--spec", "SPEC-0900")
    assert ergebnis.exit_code == 0
    assert "requirements" in ergebnis.output and "code_quality" in ergebnis.output


def test_ohne_quality_yaml_exit_2(qproject):
    ergebnis = qproject.run("quality", "measure")
    assert ergebnis.exit_code == 2 and "sdd stack apply" in ergebnis.output
