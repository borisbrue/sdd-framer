"""SPEC-0057 FR-09, CON-0229 INV-08: `sdd quality init` verweist auf Stack-Vorlagen."""
from __future__ import annotations

from pathlib import Path

import pytest

from tests.support.quality_project import make_project

BLUEPRINT = Path(__file__).resolve().parents[2] / "tool/sdd_cli/blueprint"


@pytest.fixture()
def qproject(tmp_path, monkeypatch):
    return make_project(tmp_path, monkeypatch)


def test_unbekanntes_preset_nennt_gleichnamige_vorlage(qproject):
    ergebnis = qproject.run("quality", "init", "--preset", "gibtsnicht")
    assert ergebnis.exit_code == 1
    assert "sdd stack apply gibtsnicht --only quality" in ergebnis.output
    assert "sdd stack list" in ergebnis.output


def test_preset_python_wird_zu_python_cli(qproject):
    ergebnis = qproject.run("quality", "init", "--preset", "python")
    assert ergebnis.exit_code == 1
    assert "sdd stack apply python-cli --only quality" in ergebnis.output
    assert not (qproject.root / ".sdd/quality.yaml").exists()


def test_presets_gibt_es_nicht_mehr():
    assert not (BLUEPRINT / "presets").exists()
