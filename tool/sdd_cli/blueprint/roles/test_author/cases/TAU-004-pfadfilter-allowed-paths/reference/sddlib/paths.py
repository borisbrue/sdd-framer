"""Prüfung der Schreibpfade eines Implementierers gegen allowed_paths."""
from __future__ import annotations

import fnmatch
from collections.abc import Iterable
from pathlib import PurePosixPath


def _unsafe(path: str) -> bool:
    return path.startswith("/") or ".." in PurePosixPath(path).parts


def path_violations(paths: Iterable[str], allowed: Iterable[str],
                    test_file: str | None = None) -> list[str]:
    """Pfade aus `paths`, die nicht geschrieben werden dürfen (Eingabereihenfolge)."""
    muster = list(allowed)
    verstoesse = []
    for pfad in paths:
        if (_unsafe(pfad) or pfad == test_file or pfad.startswith(".sdd/")
                or not any(fnmatch.fnmatchcase(pfad, m) for m in muster)):
            verstoesse.append(pfad)
    return verstoesse
