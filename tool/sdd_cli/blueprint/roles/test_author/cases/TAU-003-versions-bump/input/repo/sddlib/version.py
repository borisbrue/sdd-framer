"""Erhöhen von MAJOR.MINOR.PATCH-Versionsnummern."""
from __future__ import annotations


def bump_version(version: str, part: str) -> str:
    """Erhöht `part` ("major", "minor", "patch") und setzt niedere Stellen auf 0."""
    raise NotImplementedError
