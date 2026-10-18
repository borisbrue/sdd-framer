"""HF-0020: `sdd finalize --dry-run` wechselt keinen Branch und committet nicht (#178).

Der Dry-Run prüfte `self._dry_run` erst nach Branch-Wechsel und `git add -A` + `git commit`;
dabei landeten auch unversionierte Laufdaten aus `.sdd/runs/` im Commit.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from sdd_cli.config import load_config
from sdd_cli.finalize import SpecFinalizer


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-c", "user.name=B", "-c", "user.email=b@e.de", *args],
                          cwd=root, capture_output=True, text=True)


@pytest.fixture
def projekt(tmp_path: Path) -> Path:
    """Repo mit einem Commit, einer neuen Datei und unversionierten Laufdaten."""
    (tmp_path / ".sdd" / "specs").mkdir(parents=True)
    (tmp_path / ".sdd" / "config.yaml").write_text("version: 1\n", encoding="utf-8")
    (tmp_path / ".sdd" / "specs" / "SPEC-0001-demo.md").write_text(
        "---\nid: SPEC-0001\ntitle: Demo\nstatus: in-progress\nowner: B\n"
        "version: 0.1.0\n---\n\n# Demo\n", encoding="utf-8")
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "init")
    (tmp_path / ".sdd" / "runs" / "SPEC-0001").mkdir(parents=True)
    (tmp_path / ".sdd" / "runs" / "SPEC-0001" / "run.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "neu.py").write_text("x = 1\n", encoding="utf-8")
    return tmp_path


def test_dry_run_laesst_head_branch_und_index_unveraendert(projekt: Path):
    alter_head = _git(projekt, "rev-parse", "HEAD").stdout.strip()

    report = SpecFinalizer(load_config(projekt), dry_run=True).run("SPEC-0001")

    assert report.error is None
    assert report.commit_hash == alter_head
    assert _git(projekt, "rev-parse", "HEAD").stdout.strip() == alter_head
    assert _git(projekt, "branch", "--show-current").stdout.strip() == "main"
    assert _git(projekt, "diff", "--cached", "--name-only").stdout.strip() == ""
    status = _git(projekt, "status", "--porcelain").stdout
    assert "?? .sdd/runs/" in status and "?? neu.py" in status
    assert "kein Commit" in report.test_output
