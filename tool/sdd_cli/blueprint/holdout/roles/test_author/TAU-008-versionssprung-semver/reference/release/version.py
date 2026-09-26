"""Versionsnummern der Rollen-Prompts erhöhen (SemVer)."""
from __future__ import annotations

import re

PARTS = ("major", "minor", "patch")
_SEMVER = re.compile(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?")


def bump(version: str, part: str) -> str:
    """Erhöht `part` in `version` und liefert die neue Version."""
    if part not in PARTS:
        raise ValueError(f"unbekannter Teil {part!r}")
    m = _SEMVER.fullmatch(version.strip())
    if not m:
        raise ValueError(f"keine SemVer-Version: {version!r}")
    major, minor, patch = (int(g) for g in m.groups())
    vorab = "-" in version
    if part == "major":
        major, minor, patch = major + 1, 0, 0
    elif part == "minor":
        minor, patch = minor + 1, 0
    elif not vorab:
        patch += 1
    return f"{major}.{minor}.{patch}"
