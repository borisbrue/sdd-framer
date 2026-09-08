"""Shared test fixtures und sys.path-Konfiguration."""
from __future__ import annotations

import sys
from pathlib import Path

# web/api Verzeichnis für WebSocket-Route-Tests (TST-0082)
_WEB_API = Path(__file__).resolve().parents[1] / "web" / "api"
if str(_WEB_API) not in sys.path:
    sys.path.insert(0, str(_WEB_API))


# ─── Wächter: der Testlauf darf das Repository nicht verändern ────────────────
#
# Zwei Tests schrieben in die echten .sdd/-Dateien: TST-0198 rief
# `sdd review contract` mit cwd=REPO_ROOT auf (der Review haengt seine Notizen
# an die Contract-Datei an), TST-0143 baute SddConfig(root=Path(".")). Nach
# jedem Lauf war der Arbeitsbaum schmutzig — wer danach `git add -A` benutzte,
# committete das unbemerkt mit.
#
# Der Wächter vergleicht gegen den Zustand *vor* dem Lauf, nicht gegen "sauber":
# uncommittete Arbeit an .sdd/ ist legitim, sie waehrend des Laufs zu erzeugen
# nicht.

import subprocess as _subprocess

import pytest as _pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _sdd_worktree_state() -> set[str] | None:
    """Zeilen von `git status --porcelain .sdd/`. None, wenn nicht ermittelbar."""
    try:
        result = _subprocess.run(
            ["git", "status", "--porcelain", "--", ".sdd/"],
            cwd=_REPO_ROOT, capture_output=True, text=True, timeout=30,
        )
    except (OSError, _subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return {line for line in result.stdout.splitlines() if line.strip()}


@_pytest.fixture(scope="session", autouse=True)
def _repository_bleibt_unveraendert():
    before = _sdd_worktree_state()
    yield
    if before is None:
        return  # kein Git, keine Aussage
    after = _sdd_worktree_state()
    if after is None:
        return
    neu = sorted(after - before)
    if neu:
        _pytest.fail(
            "Der Testlauf hat .sdd/-Dateien des Repositories veraendert:\n"
            + "\n".join(f"    {line}" for line in neu)
            + "\n  Tests muessen in tmp_path arbeiten, nicht im Repo-Root."
            + "\n  Zuruecknehmen mit: git checkout -- .sdd/",
            pytrace=False,
        )
