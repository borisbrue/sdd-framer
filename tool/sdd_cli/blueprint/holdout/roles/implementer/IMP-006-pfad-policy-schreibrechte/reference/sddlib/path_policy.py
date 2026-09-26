"""PathPolicy: Schreibrechte je Rolle, Task und Pfad.

Default deny. Schreiben dürfen nur `test_author` (ausschließlich die Testdatei seines Tasks) und
`implementer`. Die Regeln gelten in fester Reihenfolge; die erste zutreffende entscheidet.
"""
from __future__ import annotations

import posixpath
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from .globs import matches_any

WRITING_ROLES = frozenset({"test_author", "implementer"})
PROTECTED = (".sdd/**", "specs/**", "contracts/**")

REASON_PROTECTED = "geschützter Pfad"
REASON_TEST_FILE = "Testdatei des Tasks"
REASON_TEST_AUTHOR = "test_author schreibt nur die Testdatei"
REASON_OUTSIDE = "außerhalb allowed_paths"


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str | None = None


def normalize(path: str) -> str | None:
    """Pfad relativ zur Projektwurzel mit '/', oder None bei Pfadflucht."""
    roh = path.replace("\\", "/")
    if roh.startswith("/"):
        return None
    norm = posixpath.normpath(roh)
    if norm == ".." or norm.startswith("../"):
        return None
    return norm


class PathPolicy:
    def __init__(self, protected_paths: Iterable[str] = ()) -> None:
        self.protected = (*PROTECTED, *protected_paths)

    @classmethod
    def from_config(cls, raw_config: Mapping) -> "PathPolicy":
        pipeline = raw_config.get("pipeline") or {}
        return cls(protected_paths=list(pipeline.get("protected_paths") or []))

    def check(self, role: str, path: str, task: Mapping) -> PolicyDecision:
        norm = normalize(path)
        if norm is None:
            return PolicyDecision(False, REASON_PROTECTED)
        if role not in WRITING_ROLES:
            return PolicyDecision(False, f"Rolle {role} schreibt nicht")
        if matches_any(norm, self.protected) or norm in (".sdd", "specs", "contracts"):
            return PolicyDecision(False, REASON_PROTECTED)
        test_file = normalize(task.get("test_file") or "")
        if test_file and norm == test_file:
            if role != "test_author":
                return PolicyDecision(False, REASON_TEST_FILE)
            return PolicyDecision(True)
        if role == "test_author":
            return PolicyDecision(False, REASON_TEST_AUTHOR)
        allowed = task.get("allowed_paths")
        if allowed and not matches_any(norm, allowed):
            return PolicyDecision(False, REASON_OUTSIDE)
        return PolicyDecision(True)
