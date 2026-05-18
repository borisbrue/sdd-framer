"""Obsidian Vault Synchronisation – bidirektionaler Export/Import (SPEC-0009)."""
from __future__ import annotations

import re
import signal
import time
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Iterator

import yaml

from .config import SddConfig
from .frontmatter import parse, parse_safe

# Muster für gültige Artefakt-IDs
_ID_PATTERN = re.compile(r"\b(SPEC|CON|TST|ADR)-(\d{4})\b")
# Muster für Wiki-Links beim Import  → reine IDs
_WIKI_LINK_PATTERN = re.compile(r"\[\[((SPEC|CON|TST|ADR)-\d{4})[^\]]*\]\]")

CONFLICTS_FILE = ".sdd/obsidian-conflicts.yaml"
WARNINGS_LOG = ".sdd/obsidian-warnings.log"
EXPORT_STAMP_FILE = ".sdd/obsidian-export-stamp.yaml"


# ─── Config-Helpers ───────────────────────────────────────────────────────────

@dataclass
class ObsidianConfig:
    vault_path: Path | None
    subfolder: str
    watch_interval_secs: int
    auto_wiki_links: bool


def obsidian_config(cfg: SddConfig, vault_override: str | None = None) -> ObsidianConfig:
    raw = cfg.raw.get("obsidian", {})
    vault_str = vault_override or raw.get("vault_path")
    vault_path = Path(vault_str).expanduser() if vault_str else None
    subfolder = raw.get("subfolder", "SDD") or "SDD"
    interval = int(raw.get("watch_interval_secs", 5))
    if interval < 1:
        raise ValueError(f"obsidian.watch_interval_secs muss ≥ 1 sein, ist {interval}")
    auto_links = bool(raw.get("auto_wiki_links", True))
    return ObsidianConfig(
        vault_path=vault_path,
        subfolder=subfolder,
        watch_interval_secs=interval,
        auto_wiki_links=auto_links,
    )


def _require_vault(ocfg: ObsidianConfig) -> Path:
    if ocfg.vault_path is None:
        raise ValueError("obsidian.vault_path nicht konfiguriert. "
                         "Setze vault_path in .sdd/config.yaml oder übergib --vault.")
    vault = ocfg.vault_path
    if not vault.exists():
        raise FileNotFoundError(f"Vault-Pfad existiert nicht: {vault}")
    return vault


def _check_cycle(vault: Path, project_root: Path) -> None:
    try:
        vault.resolve().relative_to(project_root.resolve())
        raise ValueError(
            f"vault_path '{vault}' ist ein Unterverzeichnis des SDD-Projekts '{project_root}'. "
            "Cycle-Prevention verhindert dies."
        )
    except ValueError as e:
        if "Cycle-Prevention" in str(e):
            raise
        # Kein Cycle – relative_to hat ValueError geworfen weil kein Subpfad


# ─── Slug-Map: ID → Dateiname-Slug ────────────────────────────────────────────

def _build_slug_map(cfg: SddConfig) -> dict[str, str]:
    """Baut eine Map von ID → slug (Dateiname ohne .md) aus allen Artefakten."""
    slug_map: dict[str, str] = {}
    dirs = [
        cfg.specs_dir,
        cfg.contracts_dir,
        cfg.tests_dir,
        cfg.adr_dir,
    ]
    for d in dirs:
        if not d.exists():
            continue
        for md in d.rglob("*.md"):
            stem = md.stem  # z.B. "SPEC-0001-user-login"
            m = re.match(r"^((SPEC|CON|TST|ADR)-\d{4})", stem)
            if m:
                slug_map[m.group(1)] = stem
    return slug_map


# ─── Wiki-Link Konvertierung ──────────────────────────────────────────────────

def ids_to_wiki_links(body: str, slug_map: dict[str, str]) -> str:
    """Ersetzt ID-Referenzen im Body durch Wiki-Links, wenn ID im slug_map bekannt."""
    def replace(m: re.Match) -> str:
        full_id = m.group(0)  # z.B. "SPEC-0001"
        slug = slug_map.get(full_id)
        return f"[[{slug}]]" if slug else full_id

    return _ID_PATTERN.sub(replace, body)


def wiki_links_to_ids(body: str) -> str:
    """Konvertiert Wiki-Links zurück in reine IDs."""
    def replace(m: re.Match) -> str:
        return m.group(1)  # z.B. "SPEC-0001"

    return _WIKI_LINK_PATTERN.sub(replace, body)


# ─── Artefakte iterieren ──────────────────────────────────────────────────────

@dataclass
class Artifact:
    source_path: Path
    artifact_id: str
    slug: str
    subdir: str  # "specs", "contracts", "tests", "adrs"
    frontmatter: dict
    body: str


def _subdir_for(path: Path, cfg: SddConfig) -> str | None:
    try:
        path.relative_to(cfg.specs_dir)
        return "specs"
    except ValueError:
        pass
    try:
        path.relative_to(cfg.contracts_dir)
        return "contracts"
    except ValueError:
        pass
    try:
        path.relative_to(cfg.tests_dir)
        return "tests"
    except ValueError:
        pass
    try:
        path.relative_to(cfg.adr_dir)
        return "adrs"
    except ValueError:
        pass
    return None


def _collect_artifacts(cfg: SddConfig) -> list[Artifact]:
    artifacts: list[Artifact] = []
    dirs = [cfg.specs_dir, cfg.contracts_dir, cfg.tests_dir, cfg.adr_dir]
    for d in dirs:
        if not d.exists():
            continue
        for md in sorted(d.rglob("*.md")):
            doc = parse_safe(md)
            if not doc:
                continue
            art_id = doc.frontmatter.get("id", "")
            if not _ID_PATTERN.match(art_id):
                continue
            stem = md.stem
            subdir = _subdir_for(md, cfg)
            if subdir is None:
                continue
            artifacts.append(Artifact(
                source_path=md,
                artifact_id=art_id,
                slug=stem,
                subdir=subdir,
                frontmatter=doc.frontmatter,
                body=doc.body,
            ))
    return artifacts


# ─── Export-Stempel ───────────────────────────────────────────────────────────

def _load_export_stamps(cfg: SddConfig) -> dict[str, float]:
    """Lädt Export-Zeitstempel als Unix-Timestamps (float)."""
    stamp_file = cfg.root / EXPORT_STAMP_FILE
    if not stamp_file.exists():
        return {}
    with stamp_file.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _save_export_stamps(cfg: SddConfig, stamps: dict[str, float]) -> None:
    stamp_file = cfg.root / EXPORT_STAMP_FILE
    stamp_file.parent.mkdir(parents=True, exist_ok=True)
    with stamp_file.open("w", encoding="utf-8") as f:
        yaml.safe_dump(stamps, f, allow_unicode=True, sort_keys=True)


# ─── Export ───────────────────────────────────────────────────────────────────

@dataclass
class ExportResult:
    written: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    dry_run: bool = False


def export(cfg: SddConfig, vault_override: str | None = None, dry_run: bool = False) -> ExportResult:
    ocfg = obsidian_config(cfg, vault_override)
    vault = _require_vault(ocfg)
    _check_cycle(vault, cfg.root)

    sdd_root = vault / ocfg.subfolder
    slug_map = _build_slug_map(cfg)
    artifacts = _collect_artifacts(cfg)
    stamps = _load_export_stamps(cfg)
    result = ExportResult(dry_run=dry_run)

    for art in artifacts:
        target = sdd_root / art.subdir / f"{art.slug}.md"
        proj_updated = str(art.frontmatter.get("updated", ""))

        # Überschreiben-Logik: nur wenn Projekt neuer ist (Vergleich über updated:-Feld)
        if target.exists():
            existing_doc = parse_safe(target)
            vault_updated = str((existing_doc.frontmatter.get("updated", "") if existing_doc else ""))
            if vault_updated and proj_updated and vault_updated >= proj_updated:
                result.skipped.append(str(target))
                continue

        body = art.body
        if ocfg.auto_wiki_links:
            body = ids_to_wiki_links(body, slug_map)

        if not dry_run:
            target.parent.mkdir(parents=True, exist_ok=True)
            fm_text = yaml.safe_dump(art.frontmatter, sort_keys=False, allow_unicode=True).rstrip("\n")
            target.write_text(f"---\n{fm_text}\n---\n{body}", encoding="utf-8")
            # Stempel = mtime der gerade geschriebenen Vault-Datei
            stamps[art.artifact_id] = target.stat().st_mtime

        result.written.append(str(target))

    # Index erzeugen
    if not dry_run:
        _write_index(sdd_root, artifacts, dry_run)
        _save_export_stamps(cfg, stamps)
    else:
        result.written.append(str(sdd_root / "index.md") + " (index)")

    return result


def _write_index(sdd_root: Path, artifacts: list[Artifact], dry_run: bool) -> None:
    if dry_run:
        return
    sdd_root.mkdir(parents=True, exist_ok=True)
    lines = ["# SDD Artefakte\n"]
    by_type: dict[str, list[Artifact]] = {}
    for art in artifacts:
        by_type.setdefault(art.subdir, []).append(art)

    for subdir in ("specs", "contracts", "tests", "adrs"):
        group = by_type.get(subdir, [])
        if not group:
            continue
        lines.append(f"\n## {subdir.capitalize()}\n")
        for art in group:
            title = art.frontmatter.get("title", art.artifact_id)
            lines.append(f"- [[{art.slug}]] – {title}")

    index_path = sdd_root / "index.md"
    index_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ─── Import ───────────────────────────────────────────────────────────────────

@dataclass
class ImportResult:
    imported: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


_VALID_ID_RE = re.compile(r"^(SPEC|CON|TST|ADR)-\d{4}$")


def _warn(cfg: SddConfig, message: str) -> None:
    log = cfg.root / WARNINGS_LOG
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as f:
        f.write(message + "\n")


def _record_conflict(cfg: SddConfig, art_id: str, vault_path: Path,
                     project_path: Path) -> None:
    conflicts_file = cfg.root / CONFLICTS_FILE
    conflicts_file.parent.mkdir(parents=True, exist_ok=True)
    existing: list[dict] = []
    if conflicts_file.exists():
        with conflicts_file.open("r", encoding="utf-8") as f:
            existing = yaml.safe_load(f) or []

    from datetime import datetime
    existing.append({
        "id": art_id,
        "vault_path": str(vault_path),
        "project_path": str(project_path),
        "detected_at": datetime.now().isoformat(timespec="seconds"),
    })
    with conflicts_file.open("w", encoding="utf-8") as f:
        yaml.safe_dump(existing, f, allow_unicode=True, sort_keys=False)


def _target_path_for(cfg: SddConfig, art_id: str, slug: str) -> Path | None:
    prefix = art_id.split("-")[0]
    mapping = {
        "SPEC": cfg.specs_dir,
        "CON": cfg.contracts_dir,
        "TST": cfg.tests_dir,
        "ADR": cfg.adr_dir,
    }
    base = mapping.get(prefix)
    if base is None:
        return None
    # Suche nach vorhandener Datei mit diesem Slug
    for md in base.rglob("*.md"):
        if md.stem == slug:
            return md
    # Fallback: direkt im Basisverzeichnis
    return base / f"{slug}.md"


def import_vault(cfg: SddConfig, vault_override: str | None = None) -> ImportResult:
    ocfg = obsidian_config(cfg, vault_override)
    vault = _require_vault(ocfg)
    _check_cycle(vault, cfg.root)

    sdd_root = vault / ocfg.subfolder
    stamps = _load_export_stamps(cfg)
    result = ImportResult()

    for vault_file in sorted(sdd_root.rglob("*.md")):
        # Sicherheitsprüfung: kein Pfad-Traversal
        try:
            vault_file.resolve().relative_to(vault.resolve())
        except ValueError:
            raise ValueError(f"Path-Traversal erkannt: {vault_file} liegt außerhalb {vault}")

        if vault_file.name == "index.md":
            continue

        # Frontmatter parsen
        doc = parse_safe(vault_file)
        if doc is None:
            msg = f"[WARNUNG] Konnte {vault_file.name} nicht parsen (ungültiges YAML-Frontmatter)"
            result.warnings.append(msg)
            _warn(cfg, msg)
            result.skipped.append(str(vault_file))
            continue

        art_id = doc.frontmatter.get("id", "")
        if not _VALID_ID_RE.match(art_id):
            msg = f"[WARNUNG] Unbekannte ID '{art_id}' in {vault_file.name} – übersprungen"
            result.warnings.append(msg)
            _warn(cfg, msg)
            result.skipped.append(str(vault_file))
            continue

        # ID muss zum Dateinamen passen
        expected_prefix = vault_file.stem.split("-")[0] + "-" + vault_file.stem.split("-")[1]
        if art_id != expected_prefix:
            msg = (f"[WARNUNG] id '{art_id}' stimmt nicht mit Dateiname '{vault_file.name}' "
                   "überein – übersprungen")
            result.warnings.append(msg)
            _warn(cfg, msg)
            result.skipped.append(str(vault_file))
            continue

        project_path = _target_path_for(cfg, art_id, vault_file.stem)
        if project_path is None:
            result.skipped.append(str(vault_file))
            continue

        # Conflict-Erkennung: beide Seiten nach dem letzten Export geändert?
        last_export: float | None = stamps.get(art_id)
        if last_export is not None and project_path.exists():
            vault_mtime = vault_file.stat().st_mtime
            proj_mtime = project_path.stat().st_mtime
            if vault_mtime > last_export and proj_mtime > last_export:
                _record_conflict(cfg, art_id, vault_file, project_path)
                result.conflicts.append(art_id)
                continue

        # Wiki-Links zurückkonvertieren
        body = wiki_links_to_ids(doc.body)

        # updated-Feld aktualisieren
        fm = dict(doc.frontmatter)
        fm["updated"] = str(date.today())

        fm_text = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True).rstrip("\n")
        project_path.parent.mkdir(parents=True, exist_ok=True)
        project_path.write_text(f"---\n{fm_text}\n---\n{body}", encoding="utf-8")
        result.imported.append(str(project_path))

    return result


# ─── Watch ────────────────────────────────────────────────────────────────────

def watch(cfg: SddConfig, vault_override: str | None = None,
          interval: int | None = None) -> None:
    """Polling-Loop: prüft den Vault auf Änderungen und importiert automatisch."""
    ocfg = obsidian_config(cfg, vault_override)
    effective_interval = interval if interval is not None else ocfg.watch_interval_secs
    vault = _require_vault(ocfg)

    sdd_root = vault / ocfg.subfolder
    known_mtimes: dict[str, float] = {}

    # Sauberer Shutdown auf SIGINT
    _running = [True]

    def _stop(signum, frame):
        _running[0] = False

    signal.signal(signal.SIGINT, _stop)

    while _running[0]:
        changed: list[Path] = []
        for f in sdd_root.rglob("*.md"):
            try:
                mtime = f.stat().st_mtime
            except OSError:
                continue
            key = str(f)
            if known_mtimes.get(key) != mtime:
                if key in known_mtimes:
                    changed.append(f)
                known_mtimes[key] = mtime

        if changed:
            result = import_vault(cfg, vault_override)
            if result.conflicts:
                for c in result.conflicts:
                    pass  # Conflicts werden in conflicts.yaml gespeichert

        time.sleep(effective_interval)
