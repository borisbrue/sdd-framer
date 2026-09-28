"""Nicht überschreibendes Schreiben von Projektdateien (CON-0197 INV-02).

Genutzt von `sdd arch init` und `sdd stack apply` (SPEC-0057). Die früheren Presets für
`sdd quality init` sind durch Stack-Vorlagen ersetzt.
"""
from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class InstallResult:
    written: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    new_files: list[tuple[str, str]] = field(default_factory=list)


def write_or_propose(root: Path, rel: str, inhalt: str, result: InstallResult) -> None:
    """Schreibt eine Projektdatei oder legt `<datei>.new` samt Diff an (CON-0197 INV-02)."""
    ziel = root / rel
    if not ziel.exists():
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text(inhalt, encoding="utf-8")
        result.written.append(rel)
        return
    alt = ziel.read_text(encoding="utf-8")
    if alt == inhalt:
        result.unchanged.append(rel)
        return
    (root / f"{rel}.new").write_text(inhalt, encoding="utf-8")
    diff = "".join(difflib.unified_diff(alt.splitlines(keepends=True),
                                        inhalt.splitlines(keepends=True),
                                        fromfile=rel, tofile=f"{rel}.new"))
    result.new_files.append((rel, diff))
