"""HF-0015: PR-Base aus dem Repo statt fest `main`; vorhandenes PR-Dokument bleibt (#138).

Im Projekt kitafinanzen (Default-Branch `master`) scheiterte jeder `gh pr create` mit
"Base ref must be a branch"; das lokale PR-Dokument nannte `git checkout main` und
ersetzte ein vorher geschriebenes Dokument durch das leere Template.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from sdd_cli.config import load_config
from sdd_cli.dev_container import GhFallbackPRStrategy, LocalGitStrategy, resolve_pr_base


def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True,
                          check=True).stdout.strip()


def _repo(root: Path, *, branch: str = "master", config: str = "version: 1\n") -> Path:
    (root / ".sdd").mkdir(parents=True)
    (root / ".sdd" / "config.yaml").write_text(config, encoding="utf-8")
    _git(root, "init", "-q", "-b", branch)
    _git(root, "config", "user.email", "b@e.de")
    _git(root, "config", "user.name", "B")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "init")
    _git(root, "checkout", "-q", "-b", "feat/SPEC-0001")
    (root / "neu.txt").write_text("x\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "impl")
    return root


class TestResolvePrBase:
    def test_lokaler_master(self, tmp_path):
        assert resolve_pr_base(load_config(_repo(tmp_path / "p"))) == "master"

    def test_origin_head_vor_lokalem_branch(self, tmp_path):
        origin = tmp_path / "origin"
        _repo(origin, branch="trunk")
        _git(origin, "checkout", "-q", "trunk")  # origin/HEAD des Klons
        klon = tmp_path / "klon"
        _git(tmp_path, "clone", "-q", str(origin), str(klon))
        _git(klon, "branch", "-q", "master")

        assert resolve_pr_base(load_config(klon)) == "trunk"

    def test_konfiguration_gewinnt(self, tmp_path):
        root = _repo(tmp_path / "p", config="version: 1\ndocker:\n  base_branch: develop\n")
        assert resolve_pr_base(load_config(root)) == "develop"


class TestGhBase:
    def test_gh_pr_create_bekommt_master(self, tmp_path, monkeypatch):
        root = _repo(tmp_path / "p")
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        argv_datei = tmp_path / "gh-argv"
        gh = bin_dir / "gh"
        gh.write_text(f'#!/bin/sh\nprintf "%s\\n" "$@" > {argv_datei}\n'
                      'echo https://example.test/pr/1\n', encoding="utf-8")
        gh.chmod(0o755)
        monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")

        url = GhFallbackPRStrategy().create("SPEC-0001", load_config(root),
                                            branch="feat/SPEC-0001")

        argv = argv_datei.read_text(encoding="utf-8").splitlines()
        assert url == "https://example.test/pr/1"
        assert argv[argv.index("--base") + 1] == "master"


class TestLokalesPrDokument:
    def test_vorhandenes_dokument_bleibt(self, tmp_path, monkeypatch):
        root = _repo(tmp_path / "p")
        monkeypatch.chdir(root)
        pr = root / ".sdd" / "prs" / "PR-SPEC-0001.md"
        pr.parent.mkdir(parents=True)
        pr.write_text("# PR\n\n## Summary\nvorbereitet\n", encoding="utf-8")

        LocalGitStrategy().create("SPEC-0001", load_config(root), branch="feat/SPEC-0001")

        assert pr.read_text(encoding="utf-8") == "# PR\n\n## Summary\nvorbereitet\n"

    def test_neues_dokument_mit_master(self, tmp_path, monkeypatch):
        root = _repo(tmp_path / "p")
        monkeypatch.chdir(root)

        LocalGitStrategy().create("SPEC-0001", load_config(root), branch="feat/SPEC-0001")

        text = (root / ".sdd" / "prs" / "PR-SPEC-0001.md").read_text(encoding="utf-8")
        assert 'merge_command: "git checkout master && git merge feat/SPEC-0001"' in text
        assert "neu.txt" in text
        assert "diff nicht verfügbar" not in text
