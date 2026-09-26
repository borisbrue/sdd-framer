"""HOL-Szenarien unter `.sdd/holdout/` finden (SPEC-0055 FR-05, CON-0219 INV-04).

`.sdd/holdout/roles/` ist der Namensraum der Rollen-Evals; seine Dateien (z. B. `input/spec.md`)
sind keine HOL-Szenarien und werden von allen Scannern ausgelassen.
"""
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

ROLES_SUBDIR = "roles"


def scenario_files(holdout_dir: Path, pattern: str = "*.md") -> Iterator[Path]:
    """Wie `holdout_dir.rglob(pattern)`, ohne den Unterbaum `roles/`."""
    ausgenommen = holdout_dir / ROLES_SUBDIR
    for pfad in holdout_dir.rglob(pattern):
        if not pfad.is_relative_to(ausgenommen):
            yield pfad
