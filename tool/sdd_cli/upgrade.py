"""`sdd upgrade` – aktualisiert ein bestehendes SDD-Projekt nicht-destruktiv.

Was wird aktualisiert:
  - .sdd/schemas/     → immer überschreiben (kein Nutzerinhalt)
  - .sdd/templates/   → nur hinzufügen, nie überschreiben (Nutzer können eigene haben)
  - .sdd/config.yaml  → fehlende Sektionen aus dem Paket-Template ergänzen (deep merge)
  - Skill-Dateien     → fehlende nachrüsten (Provider aus skills.provider),
                        vorhandene nie überschreiben (CON-0169)
  - neue Verzeichnisse → anlegen falls noch nicht vorhanden

Was wird NICHT angefasst:
  - .sdd/specs/       → Nutzer-Specs
  - .sdd/contracts/   → Nutzer-Contracts
  - .sdd/tests/       → Nutzer-Tests
"""
from __future__ import annotations

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
    result: dict[str, list] = {"created": [], "updated": [], "skipped": [], "skills": [],
                               "roles_new": [], "obsolete_blocks": [], "migrations": [],
                               "migration_conflicts": []}

    # Provider vor jeder Änderung prüfen: ein unbekannter Name bricht ab, bevor
    # etwas geschrieben ist, statt ein halbes Upgrade zu hinterlassen.
    from .init import copy_skill_files, get_skill_provider
    provider = _skill_provider(target / ".sdd" / "config.yaml")
    get_skill_provider(provider)

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

    # 6a. Nicht mehr gelesene Config-Blöcke auskommentieren (SPEC-0058 FR-04, CON-0210 INV-02).
    for block in comment_out_obsolete_blocks(target / ".sdd" / "config.yaml"):
        result["obsolete_blocks"].append(block)
        if verbose:
            print(f"  # config: {block} auskommentiert (SPEC-0058)")

    # 6b. task_routing + llm.local_llm → Rollen-Profile (SPEC-0062 FR-07, CON-0215).
    from .pipeline.config_migration import migrate_task_routing
    migration = migrate_task_routing(target / ".sdd" / "config.yaml")
    result["migrations"].extend(migration.messages)
    result["migration_conflicts"].extend(migration.conflicts)
    if migration.changed and config_dst not in result["updated"]:
        result["updated"].append(config_dst)

    # 6. Rechnerlokale Dateien (config.local.yaml, Usage-DB) in die .gitignore eintragen;
    #    Projekte von vor SPEC-0060 kennen den Eintrag für die Usage-DB noch nicht.
    from .init import ignore_local_config
    if ignore_local_config(target):
        result["updated"].append(target / ".gitignore")

    # 7. Rollen der Pipeline (SPEC-0053 FR-02): fehlende anlegen, lokal geänderte nicht
    #    überschreiben, sondern die neue Version als <rolle>.md.new daneben legen.
    from .pipeline.roles import install_roles
    angelegt, neu, gleich = install_roles(target)
    result["created"].extend(angelegt)
    result["skipped"].extend(gleich)
    result["roles_new"] = neu
    if verbose:
        for datei in [*angelegt, *neu]:
            print(f"  + {datei.relative_to(target)}")

    # 7b. Golden Cases der Rollen-Evals (SPEC-0055 FR-02): nur fehlende Fälle.
    from .pipeline.evals.cases import install_cases
    faelle = install_cases(target)
    result["created"].extend(faelle)
    if verbose:
        for fall in faelle:
            print(f"  + {fall.relative_to(target)}/")

    # 8. Web-Usage aus .sdd/ai_usage.json nach token_usage übernehmen (SPEC-0060 FR-08).
    migriert = migrate_ai_usage_json(target)
    if migriert is not None:
        result["updated"].append(migriert)
        if verbose:
            print(f"  ↺ {migriert.relative_to(target)} → token_usage")

    return result


OBSOLETE_BLOCKS = ("llm_pool", "local_agent", "autopilot")
OBSOLETE_PREFIX = "# [SPEC-0058] "


def comment_out_obsolete_blocks(config_path: Path) -> list[str]:
    """Kommentiert die Top-Level-Blöcke aus OBSOLETE_BLOCKS zeilengenau aus.

    Ein Block reicht von seiner Schlüsselzeile bis vor die nächste Zeile, die in Spalte 0 mit
    einem anderen Zeichen als Leerzeichen oder `-` beginnt (ein Kommentar in Spalte 0 gehört schon
    zum nächsten Abschnitt); Leerzeilen am Ende bleiben unkommentiert. Alle anderen Zeilen bleiben byte-gleich (CON-0210 INV-02).
    Gibt die Namen der auskommentierten Blöcke zurück.
    """
    if not config_path.is_file():
        return []
    zeilen = config_path.read_text(encoding="utf-8").splitlines(keepends=True)
    gefunden: list[str] = []
    i = 0
    while i < len(zeilen):
        kopf = zeilen[i].split(":", 1)[0]
        if zeilen[i][:1].isalpha() and kopf in OBSOLETE_BLOCKS and ":" in zeilen[i]:
            ende = i + 1
            while ende < len(zeilen) and (zeilen[ende][:1] in (" ", "\t", "-")
                                          or not zeilen[ende].strip()):
                ende += 1
            while ende > i + 1 and not zeilen[ende - 1].strip():
                ende -= 1
            for j in range(i, ende):
                if zeilen[j].strip():
                    zeilen[j] = OBSOLETE_PREFIX + zeilen[j]
            gefunden.append(kopf)
            i = ende
        else:
            i += 1
    if gefunden:
        config_path.write_text("".join(zeilen), encoding="utf-8")
    return gefunden


def migrate_ai_usage_json(target: Path) -> Path | None:
    """Übernimmt `.sdd/ai_usage.json` einmalig in `token_usage` und benennt die Datei um.

    Die Einträge bekommen den Kontext `origin: web`; die Datei heißt danach
    `ai_usage.json.migrated`, damit ein zweites Upgrade nichts doppelt übernimmt.
    Gibt den Pfad der umbenannten Datei zurück oder None, wenn es nichts zu tun gab.
    """
    import json
    import sqlite3
    from datetime import datetime, timezone

    from .estimation import TOKEN_USAGE_TABLE, init_token_usage_table_at

    quelle = target / ".sdd" / "ai_usage.json"
    if not quelle.is_file():
        return None
    try:
        eintraege = json.loads(quelle.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(eintraege, list):
        return None

    def _zeit(wert: object) -> str:
        try:
            ts = datetime.fromisoformat(str(wert))
        except ValueError:
            ts = datetime.now(timezone.utc)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def _n(e: dict, k: str) -> int:
        wert = e.get(k)
        return wert if isinstance(wert, int) and wert >= 0 else 0

    db = init_token_usage_table_at(target / ".sdd")
    with sqlite3.connect(db) as conn:
        for e in eintraege:
            if not isinstance(e, dict):
                continue
            kontext = {"origin": "web", "operation": e.get("operation"),
                       "provider": e.get("provider", "claude")}
            conn.execute(
                f"""INSERT INTO {TOKEN_USAGE_TABLE}
                    (timestamp, component, model, input_tokens, output_tokens,
                     cache_read_tokens, cache_write_tokens, source, context_json)
                    VALUES (?, 'ai_routes', ?, ?, ?, ?, ?, 'reported', ?)""",
                (_zeit(e.get("ts")), str(e.get("model") or ""), _n(e, "input_tokens"),
                 _n(e, "output_tokens"), _n(e, "cache_read_tokens"),
                 _n(e, "cache_creation_tokens"),
                 json.dumps({k: v for k, v in kontext.items() if v is not None})),
            )
    ziel = quelle.with_name("ai_usage.json.migrated")
    quelle.replace(ziel)
    return ziel


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
