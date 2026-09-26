"""Glob-Muster mit `**` für relative Pfade mit '/'."""
from __future__ import annotations

import re
from functools import cache


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
    """True, wenn `path` das Muster trifft (`*` ohne '/', `**` über Verzeichnisse)."""
    return _regex(pattern).match(path) is not None


def matches_any(path: str, patterns) -> bool:
    return any(glob_match(path, p) for p in patterns)
