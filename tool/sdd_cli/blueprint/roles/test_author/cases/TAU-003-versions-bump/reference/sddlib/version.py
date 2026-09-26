"""Erhöhen von MAJOR.MINOR.PATCH-Versionsnummern."""
from __future__ import annotations

import re

_SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
PARTS = ("major", "minor", "patch")


def bump_version(version: str, part: str) -> str:
    """Erhöht `part` ("major", "minor", "patch") und setzt niedere Stellen auf 0."""
    m = _SEMVER.match(version)
    if m is None:
        raise ValueError(f"ungültige Version: {version!r}")
    if part not in PARTS:
        raise ValueError(f"unbekannter Versionsteil: {part!r}")
    major, minor, patch = (int(g) for g in m.groups())
    if part == "major":
        return f"{major + 1}.0.0"
    if part == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"
