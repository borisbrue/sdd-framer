"""sdd finalize muss den PR vom finalisierten Branch erstellen.

finalize committete auf `feat/SPEC-XXXX`, erstellte den PR aber von
`dev/SPEC-XXXX`: _create_pr() rief strategy.create(spec_id, cfg) auf, worauf
die Strategie sich ihren Branch ueber branch_name() selbst bildete — nach dem
dev/-Schema aus SPEC-0021. Der PR enthielt die finalisierte Arbeit deshalb
nicht, meldete aber Erfolg, und _mark_implemented() lief unabhaengig davon.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tool"))

from sdd_cli.config import load_config
from sdd_cli.dev_container import GhFallbackPRStrategy, branch_name


def _repo(tmp_path: Path) -> Path:
    (tmp_path / ".sdd" / "specs").mkdir(parents=True)
    (tmp_path / ".sdd" / "config.yaml").write_text("version: 1\n", encoding="utf-8")
    (tmp_path / ".sdd" / "specs" / "SPEC-0001-demo.md").write_text(
        "---\nid: SPEC-0001\ntitle: Demo\nstatus: in-progress\nowner: B\n"
        "version: 0.1.0\n---\n\n# Demo\n", encoding="utf-8")
    for args in (["init", "-q"], ["config", "user.email", "b@e.de"],
                 ["config", "user.name", "B"], ["add", "-A"],
                 ["commit", "-q", "-m", "init"]):
        subprocess.run(["git", *args], cwd=tmp_path, capture_output=True)
    return tmp_path


def _head(root: Path) -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=root,
                          capture_output=True, text=True).stdout.strip()


class TestBranchNaming:
    def test_single_source_for_both_conventions(self):
        assert branch_name("SPEC-0001") == "dev/SPEC-0001"
        assert branch_name("SPEC-0001", prefix="feat") == "feat/SPEC-0001"


class TestPRUsesGivenBranch:
    def test_explicit_branch_reaches_gh_head(self, tmp_path):
        """Der Kern: --head muss der uebergebene Branch sein, nicht dev/."""
        cfg = load_config(_repo(tmp_path))
        captured = {}

        def fake_run(cmd, **kw):
            captured["cmd"] = cmd
            class R:
                returncode = 0
                stdout = "https://example.test/pr/1"
                stderr = ""
            return R()

        with patch.object(subprocess, "run", fake_run):
            url = GhFallbackPRStrategy().create("SPEC-0001", cfg, branch="feat/SPEC-0001")

        assert url == "https://example.test/pr/1"
        head = captured["cmd"][captured["cmd"].index("--head") + 1]
        assert head == "feat/SPEC-0001", f"PR-Head war {head!r}"

    def test_without_branch_keeps_dev_default(self, tmp_path):
        """Rueckwaertskompatibel: DevContainerManager uebergibt keinen Branch."""
        cfg = load_config(_repo(tmp_path))
        captured = {}

        def fake_run(cmd, **kw):
            captured["cmd"] = cmd
            class R:
                returncode = 0
                stdout = "https://example.test/pr/1"
                stderr = ""
            return R()

        with patch.object(subprocess, "run", fake_run):
            GhFallbackPRStrategy().create("SPEC-0001", cfg)

        assert captured["cmd"][captured["cmd"].index("--head") + 1] == "dev/SPEC-0001"


class TestGuardAgainstEmptyPR:
    """Ein PR ohne die finalisierte Arbeit darf gar nicht erst entstehen."""

    def _runner(self, root: Path):
        from sdd_cli.finalize import SpecFinalizer
        return SpecFinalizer(load_config(root))

    def test_branch_without_commit_blocks_pr(self, tmp_path):
        root = _repo(tmp_path)
        subprocess.run(["git", "branch", "dev/SPEC-0001"], cwd=root, capture_output=True)
        subprocess.run(["git", "checkout", "-q", "-b", "feat/SPEC-0001"],
                       cwd=root, capture_output=True)
        (root / "impl.py").write_text("x = 1\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=root, capture_output=True)
        subprocess.run(["git", "commit", "-q", "-m", "impl"], cwd=root, capture_output=True)
        commit = _head(root)

        # dev/ kennt den Commit nicht — genau die gemeldete Lage.
        url, path, error = self._runner(root)._create_pr("SPEC-0001", "dev/SPEC-0001", commit)

        assert url is None and path is None
        assert "enthaelt den Finalize-Commit" in error
        assert "status: in-progress" in (
            root / ".sdd" / "specs" / "SPEC-0001-demo.md").read_text(encoding="utf-8"), \
            "implemented darf nicht gesetzt werden, wenn kein PR entstand"

    def test_branch_with_commit_creates_pr(self, tmp_path):
        root = _repo(tmp_path)
        subprocess.run(["git", "checkout", "-q", "-b", "feat/SPEC-0001"],
                       cwd=root, capture_output=True)
        (root / "impl.py").write_text("x = 1\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=root, capture_output=True)
        subprocess.run(["git", "commit", "-q", "-m", "impl"], cwd=root, capture_output=True)
        commit = _head(root)

        with patch("sdd_cli.finalize.GhFallbackPRStrategy") as strategy:
            strategy.return_value.create.return_value = "https://example.test/pr/2"
            url, path, error = self._runner(root)._create_pr(
                "SPEC-0001", "feat/SPEC-0001", commit)

        assert error is None
        assert url == "https://example.test/pr/2"
        _, kwargs = strategy.return_value.create.call_args
        assert kwargs["branch"] == "feat/SPEC-0001"
        assert "status: implemented" in (
            root / ".sdd" / "specs" / "SPEC-0001-demo.md").read_text(encoding="utf-8")

    def test_no_commit_hash_skips_guard(self, tmp_path):
        root = _repo(tmp_path)
        with patch("sdd_cli.finalize.GhFallbackPRStrategy") as strategy:
            strategy.return_value.create.return_value = "https://example.test/pr/3"
            url, _, error = self._runner(root)._create_pr("SPEC-0001", "main", None)
        assert error is None and url == "https://example.test/pr/3"


class TestFinalizeEndToEnd:
    def test_pr_head_matches_effective_branch(self, tmp_path):
        """Der gemeldete Ablauf: committen auf feat/, PR muss von feat/ kommen."""
        from sdd_cli.finalize import SpecFinalizer

        root = _repo(tmp_path)
        (root / "impl.py").write_text("x = 1\n", encoding="utf-8")
        captured = {}

        real_run = subprocess.run

        def fake_run(cmd, **kw):
            if cmd and cmd[0] == "gh":
                captured["cmd"] = cmd
                class R:
                    returncode = 0
                    stdout = "https://example.test/pr/9"
                    stderr = ""
                return R()
            return real_run(cmd, **kw)

        runner = SpecFinalizer(load_config(root))
        with patch.object(subprocess, "run", fake_run):
            report = runner.run("SPEC-0001", skip_container=True)

        assert report.branch == "feat/SPEC-0001"
        assert report.error is None, report.error
        head = captured["cmd"][captured["cmd"].index("--head") + 1]
        assert head == report.branch, f"PR-Head {head!r} != Commit-Branch {report.branch!r}"
