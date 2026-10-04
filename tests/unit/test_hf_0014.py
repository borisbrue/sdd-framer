"""HF-0014: sdd finalize bricht ab, wenn git add/commit fehlschlägt (#142).

Ohne Git-Identität schlug `git commit` still fehl; `rev-parse HEAD` lieferte danach den alten
Commit, der Report meldete ihn als neuen und die Spec wurde trotzdem `implemented`
(Testprojekt knxhub, SPEC-0002).
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from sdd_cli.config import load_config
from sdd_cli.finalize import SpecFinalizer


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)


@pytest.fixture
def ohne_identitaet(tmp_path: Path, monkeypatch) -> Path:
    """Repo mit einem Commit und einer ungestagten Änderung, aber ohne Git-Identität."""
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/dev/null")
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for name in ("EMAIL", "GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL",
                 "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL"):
        monkeypatch.delenv(name, raising=False)
    (tmp_path / ".sdd" / "specs").mkdir(parents=True)
    (tmp_path / ".sdd" / "config.yaml").write_text("version: 1\n", encoding="utf-8")
    (tmp_path / ".sdd" / "specs" / "SPEC-0001-demo.md").write_text(
        "---\nid: SPEC-0001\ntitle: Demo\nstatus: in-progress\nowner: B\n"
        "version: 0.1.0\n---\n\n# Demo\n", encoding="utf-8")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "-c", "user.name=B", "-c", "user.email=b@e.de", "commit", "-q", "-m", "init")
    # Keine aus Hostname/Benutzer geratene Identität: commit muss scheitern.
    _git(tmp_path, "config", "user.useConfigOnly", "true")
    (tmp_path / "neu.txt").write_text("x\n", encoding="utf-8")
    return tmp_path


def test_fehlgeschlagener_commit_bricht_finalize_ab(ohne_identitaet: Path):
    alter_head = _git(ohne_identitaet, "rev-parse", "HEAD").stdout.strip()

    report = SpecFinalizer(load_config(ohne_identitaet)).run("SPEC-0001", skip_container=True)

    assert report.commit_hash != alter_head
    assert report.commit_hash is None
    assert report.tests_passed is False
    assert report.error and report.error.startswith("git commit fehlgeschlagen")
    assert report.pr_url is None and report.pr_path is None
    assert _git(ohne_identitaet, "rev-parse", "HEAD").stdout.strip() == alter_head


def test_spec_bleibt_bei_fehlgeschlagenem_commit_offen(ohne_identitaet: Path):
    spec = ohne_identitaet / ".sdd" / "specs" / "SPEC-0001-demo.md"

    SpecFinalizer(load_config(ohne_identitaet)).run("SPEC-0001", skip_container=True)

    assert "status: in-progress" in spec.read_text(encoding="utf-8")
