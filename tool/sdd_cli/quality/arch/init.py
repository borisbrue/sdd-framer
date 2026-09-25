"""Schichtvorschlag für `sdd arch init` (SPEC-0054 FR-07)."""
from __future__ import annotations

import re
from pathlib import Path

IGNORED = {".git", ".sdd", ".venv", "venv", "node_modules", "__pycache__", "build", "dist",
           ".idea", ".vscode"}


def _name(verzeichnis: str) -> str:
    return re.sub(r"[^a-z0-9_-]", "-", verzeichnis.lower()).strip("-") or "layer"


def suggest_architecture(root: Path) -> dict:
    """Eine Schicht je Top-Level-Verzeichnis mit Dateien, ohne Regeln."""
    layers = {}
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        if d.name in IGNORED or d.name.startswith("."):
            continue
        if any(f.is_file() for f in d.rglob("*")):
            layers[_name(d.name)] = [f"{d.name}/**"]
    return {"version": 1, "layers": layers, "rules": []}
