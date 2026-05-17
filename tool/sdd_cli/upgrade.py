"""`sdd upgrade` – aktualisiert ein bestehendes SDD-Projekt nicht-destruktiv.

Was wird aktualisiert:
  - .sdd/schemas/     → immer überschreiben (kein Nutzerinhalt)
  - .sdd/templates/   → nur hinzufügen, nie überschreiben (Nutzer können eigene haben)
  - .sdd/config.yaml  → fehlende Sektionen aus dem Paket-Template ergänzen (deep merge)
  - neue Verzeichnisse → anlegen falls noch nicht vorhanden

Was wird NICHT angefasst:
  - .sdd/specs/       → Nutzer-Specs
  - .sdd/contracts/   → Nutzer-Contracts
  - .sdd/tests/       → Nutzer-Tests
  - .sdd/docs/adr/    → Nutzer-ADRs
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import yaml

PACKAGE_ROOT = Path(__file__).resolve().parent
BLUEPRINT_ROOT = PACKAGE_ROOT.parent.parent  # tool/ → sdd-framer/


def upgrade_project(target: Path, verbose: bool = False) -> dict[str, list[Path]]:
    """
    Aktualisiert das SDD-Projekt unter *target*.

    Returns:
        dict mit keys "created", "updated", "skipped" – jeweils Liste von Pfaden
    """
    target = target.resolve()
    result: dict[str, list[Path]] = {"created": [], "updated": [], "skipped": []}

    # 1. Neue Verzeichnisse anlegen (aus init.py REQUIRED_DIRS)
    from .init import REQUIRED_DIRS
    for rel in REQUIRED_DIRS:
        d = target / rel
        if not d.exists():
            d.mkdir(parents=True)
            result["created"].append(d)
            if verbose:
                print(f"  + {rel}/")

    # 2. Schemas immer aktualisieren (keine Nutzerinhalte)
    _sync_dir(
        src=BLUEPRINT_ROOT / ".sdd" / "schemas",
        dst=target / ".sdd" / "schemas",
        force=True,
        result=result,
        verbose=verbose,
    )

    # 3. Templates nur hinzufügen, nie überschreiben
    _sync_dir(
        src=BLUEPRINT_ROOT / ".sdd" / "templates",
        dst=target / ".sdd" / "templates",
        force=False,
        result=result,
        verbose=verbose,
    )

    # 4. config.yaml deep merge
    config_dst = target / ".sdd" / "config.yaml"
    config_src = BLUEPRINT_ROOT / ".sdd" / "config.yaml"

    if config_src.exists() and config_dst.exists():
        existing = yaml.safe_load(config_dst.read_text(encoding="utf-8")) or {}
        template = yaml.safe_load(config_src.read_text(encoding="utf-8")) or {}
        merged = _deep_merge_keep_existing(existing, template)

        if merged != existing:
            config_dst.write_text(
                yaml.dump(merged, default_flow_style=False, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
            result["updated"].append(config_dst)
            if verbose:
                _show_new_keys(existing, template)
        else:
            result["skipped"].append(config_dst)
    elif config_src.exists() and not config_dst.exists():
        # Sollte nicht vorkommen (kein .sdd/config.yaml → kein SDD-Projekt)
        shutil.copy(config_src, config_dst)
        result["created"].append(config_dst)

    return result


def _sync_dir(
    src: Path,
    dst: Path,
    force: bool,
    result: dict[str, list[Path]],
    verbose: bool,
) -> None:
    """Kopiert Dateien von src nach dst.

    force=True  → überschreibt vorhandene Dateien
    force=False → überspringt vorhandene Dateien
    """
    if not src.exists():
        return
    dst.mkdir(parents=True, exist_ok=True)
    for src_file in src.rglob("*"):
        if src_file.is_dir():
            continue
        rel = src_file.relative_to(src)
        dst_file = dst / rel
        dst_file.parent.mkdir(parents=True, exist_ok=True)
        if dst_file.exists() and not force:
            result["skipped"].append(dst_file)
            continue
        action = "updated" if dst_file.exists() else "created"
        shutil.copy(src_file, dst_file)
        result[action].append(dst_file)
        if verbose:
            prefix = "↺" if action == "updated" else "+"
            print(f"  {prefix} {dst_file.relative_to(dst_file.parents[2])}")


def _deep_merge_keep_existing(base: dict[str, Any], template: dict[str, Any]) -> dict[str, Any]:
    """Deep merge: base-Werte gewinnen – nur fehlende Schlüssel aus template übernehmen."""
    result: dict[str, Any] = dict(base)
    for key, tval in template.items():
        if key not in result:
            result[key] = tval
        elif isinstance(tval, dict) and isinstance(result[key], dict):
            result[key] = _deep_merge_keep_existing(result[key], tval)
        # else: base gewinnt
    return result


def _show_new_keys(existing: dict, template: dict, prefix: str = "") -> None:
    """Zeigt neu hinzugefügte Top-Level-Schlüssel an."""
    for key in template:
        if key not in existing:
            print(f"    + config: {prefix}{key}")
        elif isinstance(template[key], dict) and isinstance(existing.get(key), dict):
            _show_new_keys(existing[key], template[key], prefix=f"{prefix}{key}.")
