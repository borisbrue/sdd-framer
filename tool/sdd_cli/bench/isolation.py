"""Isolationsarten für Benchmark-Läufe (SPEC-0063 FR-04, CON-0226 INV-02), Strategy.

Eine Strategie legt ein Arbeitsverzeichnis an und räumt es wieder ab. `dir` kopiert den Startstand
eines Fixtures in ein Temp-Verzeichnis und macht es zu einem eigenen Git-Repository mit
Start-Commit. Weitere Arten (z. B. Container) kommen als neue Strategie hinzu.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Protocol

from .config import BenchError

GIT = ["git", "-c", "user.email=bench@sdd.local", "-c", "user.name=sdd bench",
       "-c", "commit.gpgsign=false"]


class WorkspaceStrategy(Protocol):
    name: str

    def create(self, source: Path) -> tuple[Path, str]:
        """Arbeitsverzeichnis aus `source`; gibt (Pfad, Start-Commit) zurück."""
        ...

    def remove(self, workspace: Path) -> None: ...


class DirStrategy:
    name = "dir"

    def create(self, source: Path) -> tuple[Path, str]:
        ziel = Path(tempfile.mkdtemp(prefix="sdd-bench-e2e-"))
        shutil.copytree(source, ziel, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("__pycache__", ".git"))
        for befehl in (["init", "-q"], ["add", "-A"], ["commit", "-q", "-m", "Startstand"]):
            r = subprocess.run([*GIT, "-C", str(ziel), *befehl], capture_output=True, text=True)
            if r.returncode != 0:
                shutil.rmtree(ziel, ignore_errors=True)
                raise BenchError(f"git {befehl[0]} im Arbeitsverzeichnis: {r.stderr.strip()}")
        sha = subprocess.run([*GIT, "-C", str(ziel), "rev-parse", "HEAD"], capture_output=True,
                             text=True).stdout.strip()
        return ziel, sha

    def remove(self, workspace: Path) -> None:
        shutil.rmtree(workspace, ignore_errors=True)


STRATEGIES: dict[str, type] = {"dir": DirStrategy}


def strategy(name: str) -> WorkspaceStrategy:
    if name not in STRATEGIES:
        raise BenchError(f"Unbekannte Isolation {name!r} (bekannt: {', '.join(STRATEGIES)}).")
    return STRATEGIES[name]()
