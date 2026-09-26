"""Dateimengen für `{paths}` und Glob-Muster mit `**` (SPEC-0102)."""
from __future__ import annotations

import re
from functools import cache
from pathlib import Path

ALWAYS_EXCLUDED = (".sdd/**", ".git/**")


@cache
def _regex(pattern: str) -> re.Pattern[str]:
    teile, i = [], 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            teile.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            teile.append(".*")
            i += 2
        elif pattern[i] == "*":
            teile.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            teile.append("[^/]")
            i += 1
        else:
            teile.append(re.escape(pattern[i]))
            i += 1
    muster = "".join(teile)
    if pattern.endswith("/**"):
        muster = muster[: -len("/.*")] + "/.+"
    return re.compile(muster + r"\Z")


def glob_match(path: str, pattern: str) -> bool:
    """Ganzer Pfad gegen Muster (FR-01 bis FR-03)."""
    return _regex(pattern).match(path) is not None


def matches_any(path: str, patterns: list[str] | tuple[str, ...]) -> bool:
    """Wahr, wenn mindestens ein Muster trifft (FR-04)."""
    return any(glob_match(path, p) for p in patterns)


def collect_files(root: Path, include: list[str], exclude: list[str]) -> list[str]:
    """Alle Dateien unter root, relativ und sortiert, die `include` (Default: alle) treffen (FR-05)."""
    ausgeschlossen = [*ALWAYS_EXCLUDED, *exclude]
    ergebnis = []
    for pfad in root.rglob("*"):
        if not pfad.is_file():
            continue
        rel = pfad.relative_to(root).as_posix()
        if matches_any(rel, ausgeschlossen):
            continue
        if include and not matches_any(rel, include):
            continue
        ergebnis.append(rel)
    return sorted(ergebnis)
