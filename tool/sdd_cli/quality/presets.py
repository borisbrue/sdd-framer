"""Presets für `sdd quality init` (SPEC-0054 FR-13/FR-14).

Ein Preset ist ein Verzeichnis im Blueprint. `quality.yaml` wird nach `.sdd/quality.yaml`
kopiert, alle übrigen Dateien nach `.sdd/quality/`. Danach gehören die Dateien dem Projekt.
"""
from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from pathlib import Path

PRESETS_DIR = Path(__file__).resolve().parents[1] / "blueprint" / "presets" / "quality"


@dataclass
class InstallResult:
    written: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    new_files: list[tuple[str, str]] = field(default_factory=list)


def available_presets() -> list[str]:
    return sorted(p.name for p in PRESETS_DIR.iterdir() if p.is_dir()) if PRESETS_DIR.is_dir() else []


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


def install_preset(root: Path, name: str) -> InstallResult:
    quelle = PRESETS_DIR / name
    if not quelle.is_dir():
        raise KeyError(name)
    result = InstallResult()
    for datei in sorted(p for p in quelle.rglob("*") if p.is_file()):
        rel_quelle = datei.relative_to(quelle).as_posix()
        if "__pycache__" in rel_quelle:
            continue
        ziel = ".sdd/quality.yaml" if rel_quelle == "quality.yaml" else f".sdd/quality/{rel_quelle}"
        write_or_propose(root, ziel, datei.read_text(encoding="utf-8"), result)
    return result
