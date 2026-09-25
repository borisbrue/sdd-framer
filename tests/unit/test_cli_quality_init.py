"""SPEC-0054 FR-13/FR-14, CON-0197: CLI sdd quality init."""
from __future__ import annotations

import pytest

from tests.support.quality_project import make_project


@pytest.fixture()
def qproject(tmp_path, monkeypatch):
    return make_project(tmp_path, monkeypatch)


def test_unbekanntes_preset(qproject):
    ergebnis = qproject.run("quality", "init", "--preset", "gibtsnicht")
    assert ergebnis.exit_code == 2 and "python" in ergebnis.output


def test_zweimal_ist_idempotent(qproject):
    assert qproject.run("quality", "init", "--preset", "python").exit_code == 0
    ergebnis = qproject.run("quality", "init", "--preset", "python")
    assert ergebnis.exit_code == 0
    assert not list((qproject.root / ".sdd").rglob("*.new"))
