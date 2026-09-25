"""Geänderte Dateien gegenüber einem Git-Stand (SPEC-0054 FR-01)."""
from __future__ import annotations

import subprocess
from pathlib import Path


class DiffError(Exception):
    pass


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)


def current_sha(root: Path) -> str | None:
    try:
        proc = _git(root, "rev-parse", "HEAD")
    except FileNotFoundError:
        return None
    return proc.stdout.strip() if proc.returncode == 0 else None


def changed_files(root: Path, base_ref: str) -> list[str]:
    """Geänderte und neue (nicht ignorierte) Dateien seit `base_ref`, sortiert."""
    diff = _git(root, "diff", "--name-only", base_ref, "--")
    if diff.returncode != 0:
        raise DiffError(f"git diff gegen {base_ref!r} fehlgeschlagen: {diff.stderr.strip()}")
    neu = _git(root, "ls-files", "--others", "--exclude-standard")
    dateien = {*diff.stdout.split("\n"), *neu.stdout.split("\n")} - {""}
    return sorted(d for d in dateien if (root / d).is_file())


def diff_text(root: Path, base_ref: str | None) -> str:
    """Unified Diff für den Judge; ohne base_ref gegen HEAD."""
    proc = _git(root, "diff", base_ref or "HEAD", "--")
    return proc.stdout if proc.returncode == 0 else ""
