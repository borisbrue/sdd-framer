"""finalize muss den Branch pushen, den es fuer den PR braucht.

`sdd finalize` legte feat/SPEC-XXXX lokal an, committete dorthin und rief dann
`gh pr create`:

    pull request create failed: GraphQL: Head sha can't be blank,
    No commits between main and feat/SPEC-0002,
    Head ref must be a branch (createPullRequest)

Der Branch existierte auf origin nicht. Der PR landete als lokale Datei, und
der Zweck des Kommandos — Spec zu PR ohne Handgriffe — war verfehlt.

Die Frage war in #38 ausdruecklich offen gelassen worden ("ob finalize
automatisch pushen soll, ist eine Verhaltensentscheidung"); der Fall ist
seither dreimal aufgetreten.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tool"))

from sdd_cli.config import load_config
from sdd_cli.finalize import SpecFinalizer


def _repo(tmp_path: Path, mit_origin: bool = True) -> Path:
    (tmp_path / ".sdd" / "specs").mkdir(parents=True)
    (tmp_path / ".sdd" / "config.yaml").write_text("version: 1\n", encoding="utf-8")
    (tmp_path / ".sdd" / "specs" / "SPEC-0001-demo.md").write_text(
        "---\nid: SPEC-0001\ntitle: Demo\nstatus: in-progress\nowner: B\n"
        "version: 0.1.0\n---\n\n# Demo\n", encoding="utf-8")
    for args in (["init", "-q"], ["config", "user.email", "b@e.de"],
                 ["config", "user.name", "B"], ["add", "-A"],
                 ["commit", "-q", "-m", "init"]):
        subprocess.run(["git", *args], cwd=tmp_path, capture_output=True)
    if mit_origin:
        remote = tmp_path.parent / f"{tmp_path.name}-remote.git"
        subprocess.run(["git", "init", "--bare", "-q", str(remote)], capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", str(remote)],
                       cwd=tmp_path, capture_output=True)
    return tmp_path


def _auf_branch(root: Path, branch: str) -> str:
    subprocess.run(["git", "checkout", "-q", "-b", branch], cwd=root, capture_output=True)
    (root / "impl.py").write_text("x = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=root, capture_output=True)
    subprocess.run(["git", "commit", "-q", "-m", "impl"], cwd=root, capture_output=True)
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=root,
                          capture_output=True, text=True).stdout.strip()


def _remote_branches(root: Path) -> str:
    return subprocess.run(["git", "ls-remote", "--heads", "origin"], cwd=root,
                          capture_output=True, text=True).stdout


class TestBranchLandetAufOrigin:
    def test_branch_wird_gepusht(self, tmp_path):
        """Der Kern: ohne Remote-Branch kann gh pr create nicht greifen."""
        root = _repo(tmp_path)
        commit = _auf_branch(root, "feat/SPEC-0001")
        assert "feat/SPEC-0001" not in _remote_branches(root)

        with patch("sdd_cli.finalize.GhFallbackPRStrategy") as strategy:
            strategy.return_value.create.return_value = "https://example.test/pr/1"
            SpecFinalizer(load_config(root))._create_pr(
                "SPEC-0001", "feat/SPEC-0001", commit)

        assert "feat/SPEC-0001" in _remote_branches(root)

    def test_push_laeuft_vor_der_pr_erstellung(self, tmp_path):
        root = _repo(tmp_path)
        commit = _auf_branch(root, "feat/SPEC-0001")
        reihenfolge: list[str] = []

        finalizer = SpecFinalizer(load_config(root))
        echt = finalizer._push_branch

        def fake_push(branch):
            reihenfolge.append("push")
            return echt(branch)

        with patch.object(finalizer, "_push_branch", fake_push), \
             patch("sdd_cli.finalize.GhFallbackPRStrategy") as strategy:
            strategy.return_value.create.side_effect = (
                lambda *a, **kw: reihenfolge.append("pr") or "https://example.test/pr/1")
            finalizer._create_pr("SPEC-0001", "feat/SPEC-0001", commit)

        assert reihenfolge == ["push", "pr"]

    def test_upstream_wird_gesetzt(self, tmp_path):
        root = _repo(tmp_path)
        commit = _auf_branch(root, "feat/SPEC-0001")
        with patch("sdd_cli.finalize.GhFallbackPRStrategy") as strategy:
            strategy.return_value.create.return_value = "https://example.test/pr/1"
            SpecFinalizer(load_config(root))._create_pr(
                "SPEC-0001", "feat/SPEC-0001", commit)

        upstream = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "feat/SPEC-0001@{upstream}"],
            cwd=root, capture_output=True, text=True)
        assert upstream.returncode == 0


class TestPushIstKeinAbbruchgrund:
    def test_ohne_origin_geht_es_weiter(self, tmp_path):
        """Der lokale Rueckfall bleibt bestehen."""
        root = _repo(tmp_path, mit_origin=False)
        commit = _auf_branch(root, "feat/SPEC-0001")

        with patch("sdd_cli.finalize.GhFallbackPRStrategy") as strategy:
            strategy.return_value.create.return_value = None
            url, pfad, fehler = SpecFinalizer(load_config(root))._create_pr(
                "SPEC-0001", "feat/SPEC-0001", commit)

        assert fehler is None, "Ein fehlender Remote darf finalize nicht abbrechen"
        assert pfad is not None and pfad.name == "PR-SPEC-0001.md"

    def test_ohne_origin_wird_der_grund_genannt(self, tmp_path):
        root = _repo(tmp_path, mit_origin=False)
        meldung = SpecFinalizer(load_config(root))._push_branch("feat/SPEC-0001")
        assert meldung is not None and "origin" in meldung

    def test_fehlgeschlagener_push_nennt_den_grund(self, tmp_path):
        root = _repo(tmp_path)
        _auf_branch(root, "feat/SPEC-0001")
        meldung = SpecFinalizer(load_config(root))._push_branch("gibt-es-nicht")
        assert meldung is not None and "fehlgeschlagen" in meldung

    def test_erfolgreicher_push_meldet_nichts(self, tmp_path):
        root = _repo(tmp_path)
        _auf_branch(root, "feat/SPEC-0001")
        assert SpecFinalizer(load_config(root))._push_branch("feat/SPEC-0001") is None


class TestGuardBleibtVorgeschaltet:
    def test_ohne_commit_im_branch_wird_nicht_gepusht(self, tmp_path):
        """Der Schutz aus #38 greift vor dem Push."""
        root = _repo(tmp_path)
        subprocess.run(["git", "branch", "dev/SPEC-0001"], cwd=root, capture_output=True)
        commit = _auf_branch(root, "feat/SPEC-0001")

        url, pfad, fehler = SpecFinalizer(load_config(root))._create_pr(
            "SPEC-0001", "dev/SPEC-0001", commit)

        assert fehler is not None and "enthaelt den Finalize-Commit" in fehler
        assert "dev/SPEC-0001" not in _remote_branches(root)
