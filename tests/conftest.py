"""Shared test fixtures und sys.path-Konfiguration."""
from __future__ import annotations

import os
import sys
from pathlib import Path

# ─── Farbfreie CLI-Ausgabe, unabhängig von der Shell (#124) ──────────────────
#
# Tests vergleichen CLI-Ausgabe als Klartext. Die rich-Console in main.py legt
# ihr Farbsystem beim Import fest, nicht beim Ausgeben. Sieht sie dabei
# FORCE_COLOR oder ein echtes Terminal (`pytest -s`), schreibt sie später auch in
# den CliRunner Farbcodes, und sechs Tests scheiterten je nach Shell.
#
# TTY_COMPATIBLE=0 sagt rich "kein Terminal". rich prüft das vor FORCE_COLOR, und
# es ist genau der Zustand eines normalen Laufs mit Capture. pytest liest die
# Variable nicht, seine eigene Ausgabe bleibt farbig. TERM=dumb hätte auch die
# abgeschaltet.
#
# Die Zeile muss hier stehen, beim Laden des conftest und damit vor dem ersten
# Import von sdd_cli. Eine Fixture käme zu spät.
os.environ["TTY_COMPATIBLE"] = "0"

# Die Web-API, die der Server laedt (ui.py: _web_root() / "api"). Bis #107 zeigte
# der Pfad auf eine zweite Kopie unter web/api/ im Repo-Root, die nirgends
# ausgeliefert wurde und in zehn Dateien abwich — die Tests prueften die falsche.
_WEB_API = Path(__file__).resolve().parents[1] / "tool" / "sdd_cli" / "web" / "api"
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


# ─── Wächter: LLM-Aufrufe in Tests schreiben keine Usage ins Repository ──────
#
# Seit SPEC-0060 erfasst die Factory jeden Aufruf in token_usage des Projekts.
# Tests, die eine Konfiguration des Repos laden, würden sonst in dessen
# .sdd/evaluations.db schreiben (gitignored, der Wächter oben sähe es nicht).

@_pytest.fixture(autouse=True)
def _keine_usage_im_repository(monkeypatch):
    try:
        from sdd_cli.llm import usage
    except ImportError:
        yield
        return
    original = usage.SqliteUsageSink.root_for

    def root_for(self, record):
        root = original(self, record)
        if root is not None and root.resolve() == _REPO_ROOT:
            return None
        return root

    monkeypatch.setattr(usage.SqliteUsageSink, "root_for", root_for)
    yield
