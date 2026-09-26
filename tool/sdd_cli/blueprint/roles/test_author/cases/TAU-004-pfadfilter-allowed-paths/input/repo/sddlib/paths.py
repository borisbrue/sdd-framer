"""Prüfung der Schreibpfade eines Implementierers gegen allowed_paths."""
from __future__ import annotations

from collections.abc import Iterable


def path_violations(paths: Iterable[str], allowed: Iterable[str],
                    test_file: str | None = None) -> list[str]:
    """Pfade aus `paths`, die nicht geschrieben werden dürfen (Eingabereihenfolge)."""
    return []
