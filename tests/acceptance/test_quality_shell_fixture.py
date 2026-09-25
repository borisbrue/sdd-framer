"""SPEC-0054 Erfolgskriterien 3 und 4: Projekt ohne Python läuft ohne Kernänderung durch;
ein Schichtverstoß wird mit Datei, Zeile und ADR erkannt."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from click.testing import CliRunner

from sdd_cli.init import init_project
from sdd_cli.main import cli

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/quality/shell_projekt"


@pytest.fixture()
def projekt(tmp_path, monkeypatch):
    init_project(tmp_path, title="Shell-Dienst")
    shutil.copytree(FIXTURE, tmp_path, dirs_exist_ok=True)
    # Markdown liegt als *.fixture im Repo, damit `sdd validate` es nicht als Artefakt prüft.
    for datei in tmp_path.rglob("*.md.fixture"):
        datei.rename(datei.with_suffix(""))
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_measure_liefert_alle_dimensionen(projekt):
    ergebnis = CliRunner().invoke(cli, ["quality", "measure", "--spec", "SPEC-0901", "--json"])
    assert ergebnis.exit_code == 0, ergebnis.output
    r = json.loads(ergebnis.stdout)
    dims = {k["name"]: k["score"] for k in r["tree"]["children"]}
    assert dims["requirements"] == pytest.approx(0.5)
    assert dims["architecture"] == pytest.approx(0.8)
    assert dims["code_quality"] == pytest.approx(0.6)
    assert r["incomplete"] is False
    assert {f["id"]: f["status"] for f in r["requirements"]["frs"]} == {"FR-01": "erfüllt",
                                                                       "FR-02": "fehlt"}


def test_arch_check_findet_schichtverstoss(projekt):
    ergebnis = CliRunner().invoke(cli, ["arch", "check"])
    assert ergebnis.exit_code == 1
    assert "ARCH-01" in ergebnis.output and "lib/util.sh:2" in ergebnis.output
    assert "ADR-0001" in ergebnis.output


def test_validate_kennt_die_adr_verknuepfung(projekt):
    ergebnis = CliRunner().invoke(cli, ["validate"])
    assert "ARCH-01" not in ergebnis.output
