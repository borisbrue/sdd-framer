"""Versionsnummern der Rollen-Prompts erhöhen (SemVer)."""
from __future__ import annotations

PARTS = ("major", "minor", "patch")


def bump(version: str, part: str) -> str:
    """Erhöht `part` in `version` und liefert die neue Version."""
    raise NotImplementedError
