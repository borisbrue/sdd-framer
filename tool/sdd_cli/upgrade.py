"""`sdd upgrade` – aktualisiert ein bestehendes SDD-Projekt nicht-destruktiv.

Was wird aktualisiert:
  - .sdd/schemas/     → immer überschreiben (kein Nutzerinhalt)
  - .sdd/templates/   → nur hinzufügen, nie überschreiben (Nutzer können eigene haben)
  - .sdd/config.yaml  → fehlende Sektionen aus dem Paket-Template ergänzen (deep merge)
  - Skill-Dateien     → fehlende nachrüsten (Provider aus skills.provider);
                        Blueprint-Fassungen mit älterer Version ersetzen,
                        eigene Dateien nie anfassen (CON-0169)
  - neue Verzeichnisse → anlegen falls noch nicht vorhanden

Was wird NICHT angefasst:
  - .sdd/specs/       → Nutzer-Specs
  - .sdd/contracts/   → Nutzer-Contracts
  - .sdd/tests/       → Nutzer-Tests
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any

import yaml


def _quelle() -> Path:
    """Das Paket-Blueprint, dieselbe Quelle wie für `sdd init`.

    Bis #126 stand hier `PACKAGE_ROOT.parent.parent`. In einer editierbaren
    Installation ist das die Wurzel des sdd-framer-Repos, dessen eigenes .sdd/
    dann als Vorlage diente. Das mischte die Repo-Config (docker.runtime: podman,
    hub, title) in fremde Projekte und ergänzte Templates aus einer veralteten
    Projektkopie. In einem Wheel zeigte der Pfad ins Leere, und upgrade tat
    still nichts.
    """
    from .init import _blueprint_root
    quelle = _blueprint_root()
    if not quelle.is_dir():
        raise FileNotFoundError(f"Paket-Blueprint nicht gefunden: {quelle}")
    return quelle


# Kopfzeile jeder ausgelieferten Skill-Datei. `sdd-blueprint: true` sagt: Die
# Datei stammt unveraendert aus dem Blueprint. Wer sie selbst pflegt, nimmt die
# Zeile heraus, und upgrade laesst die Datei in Ruhe.
_SKILL_HEADER_RE = re.compile(
    r"<!--\s*skill:\s*[\w-]+\s*\|\s*version:\s*(?P<version>\d+(?:\.\d+)*)"
    r"\s*\|\s*sdd-blueprint:\s*true\b"
)
_FRONTMATTER_RE = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)


def _skill_version(text: str) -> tuple[int, ...] | None:
    m = _SKILL_HEADER_RE.search(text[:800])
    return tuple(int(x) for x in m.group("version").split(".")) if m else None


def _replace_outdated_skills(
    target: Path, src_dir: Path, dst_dir: Path, result: dict[str, list[Path]], verbose: bool,
) -> None:
    """Ersetzt Blueprint-Skills, deren Kopfzeile eine aeltere Version traegt (#134).

    Bis dahin blieb jede vorhandene Skill-Datei stehen, auch wenn sie seit
    Monaten auf entfernte Befehle zeigte; nur `sdd init --force-skills` half,
    und das ueberschrieb auch eigene Dateien. Ein vorangestelltes YAML-
    Frontmatter (etwa `scope:`) bleibt erhalten.
    """
    for src_file in sorted(src_dir.glob("*.md")):
        dst_file = dst_dir / src_file.name
        if not dst_file.exists():
            continue
        alt = dst_file.read_text(encoding="utf-8")
        v_alt, v_neu = _skill_version(alt), _skill_version(src_file.read_text(encoding="utf-8"))
        if v_alt is None or v_neu is None or v_alt >= v_neu:
            continue
        m = _FRONTMATTER_RE.match(alt)
        prefix = m.group(0) if m else ""
        dst_file.write_text(prefix + src_file.read_text(encoding="utf-8"), encoding="utf-8")
        result["updated"].append(dst_file)
        result["skills_updated"].append(dst_file)
        if verbose:
            print(f"  ↺ {dst_file.relative_to(target)} "
                  f"({'.'.join(map(str, v_alt))} → {'.'.join(map(str, v_neu))})")


def _skill_provider(config_path: Path) -> str:
    """`skills.provider` aus der Projekt-Config, sonst claude wie bei `sdd init`."""
    try:
        cfg = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return "claude"
    skills = cfg.get("skills") if isinstance(cfg, dict) else None
    if not isinstance(skills, dict):
        return "claude"
    return str(skills.get("provider") or "claude")


def upgrade_project(target: Path, verbose: bool = False) -> dict[str, list[Path]]:
    """
    Aktualisiert das SDD-Projekt unter *target*.

    Returns:
        dict mit keys "created", "updated", "skipped" – jeweils Liste von Pfaden
    """
    target = target.resolve()
    quelle = _quelle()
    result: dict[str, list[Path]] = {
        "created": [], "updated": [], "skipped": [], "skills": [], "skills_updated": [],
    }

    # Provider vor jeder Änderung prüfen: ein unbekannter Name bricht ab, bevor
    # etwas geschrieben ist, statt ein halbes Upgrade zu hinterlassen.
    from .init import copy_skill_files, get_skill_provider
    provider = _skill_provider(target / ".sdd" / "config.yaml")
    prov = get_skill_provider(provider)

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
        src=quelle / "schemas",
        dst=target / ".sdd" / "schemas",
        force=True,
        result=result,
        verbose=verbose,
    )

    # 3. Templates nur hinzufügen, nie überschreiben
    _sync_dir(
        src=quelle / "templates",
        dst=target / ".sdd" / "templates",
        force=False,
        result=result,
        verbose=verbose,
    )

    # 4. config.yaml deep merge
    config_dst = target / ".sdd" / "config.yaml"
    config_src = quelle / "config.yaml"

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

    # 5. Fehlende Skill-Dateien nachrüsten (CON-0169, SPEC-0044 FR-06). Die Hilfe
    #    von `sdd upgrade` versprach das seit SPEC-0044, umgesetzt war es nicht
    #    (#126). Vorhandene Dateien bleiben unberührt, auch veraltete.
    erstellt, uebersprungen = copy_skill_files(target, quelle, provider=provider, force=False)
    result["created"].extend(erstellt)
    result["skipped"].extend(uebersprungen)
    result["skills"].extend(erstellt)
    if verbose:
        for datei in erstellt:
            print(f"  + {datei.relative_to(target)}")
    _replace_outdated_skills(
        target, quelle / "templates" / "agents-md" / prov.source_subdir,
        target / prov.target_dir, result, verbose,
    )

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
