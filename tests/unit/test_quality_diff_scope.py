"""SPEC-0054 FR-01: geänderte Dateien gegenüber BASE_REF."""
from __future__ import annotations

import subprocess

import pytest

from sdd_cli.quality.diff import DiffError, changed_files, current_sha


def _git(root, *args):
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def test_geaenderte_und_neue_dateien(tmp_path):
    _git(tmp_path, "init", "-q", "-b", "main")
    (tmp_path / "a.py").write_text("1\n")
    (tmp_path / "b.py").write_text("1\n")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "x")
    (tmp_path / "a.py").write_text("2\n")
    (tmp_path / "neu.py").write_text("n\n")
    assert changed_files(tmp_path, "main") == ["a.py", "neu.py"]
    assert len(current_sha(tmp_path)) == 40


def test_unbekannter_ref(tmp_path):
    _git(tmp_path, "init", "-q")
    with pytest.raises(DiffError):
        changed_files(tmp_path, "gibtsnicht")


def test_ohne_git_kein_sha(tmp_path):
    assert current_sha(tmp_path) is None
