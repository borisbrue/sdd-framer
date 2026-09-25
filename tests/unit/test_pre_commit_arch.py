"""SPEC-0059 FR-06 / CON-0209 INV-03: nicht auswertbare Architekturprüfung blockiert nicht."""
from __future__ import annotations

import subprocess

from sdd_cli.pre_commit_hook import PreCommitHook


def _projekt(root, architektur: str) -> None:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    (root / ".sdd").mkdir()
    (root / ".sdd/architecture.yaml").write_text(architektur, encoding="utf-8")
    (root / "modul.py").write_text("x = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)


def test_ungueltige_regeln_blockieren_nicht(tmp_path, capsys):
    _projekt(tmp_path, "version: 1\nlayers: {}\nrules: [kaputt]\n")
    assert PreCommitHook(tmp_path, {}).run() == 0
    assert "nicht auswertbar" in capsys.readouterr().out


def test_ohne_python_dateien_keine_pruefung(tmp_path, capsys):
    _projekt(tmp_path, "version: 1\nlayers: {}\nrules: [kaputt]\n")
    subprocess.run(["git", "rm", "-q", "--cached", "modul.py"], cwd=tmp_path, check=True)
    (tmp_path / "notiz.md").write_text("x\n", encoding="utf-8")
    subprocess.run(["git", "add", "notiz.md"], cwd=tmp_path, check=True)
    assert PreCommitHook(tmp_path, {}).run() == 0
    assert "Architektur" not in capsys.readouterr().out
