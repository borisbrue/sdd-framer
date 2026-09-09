"""`sdd init` – legt die Blueprint-Struktur in einem Projekt an."""
from __future__ import annotations

import json
import re
import shutil
import stat
from dataclasses import dataclass
from importlib.resources import files as _pkg_files
from pathlib import Path
from typing import Protocol, runtime_checkable


def _blueprint_root() -> Path:
    return Path(str(_pkg_files("sdd_cli").joinpath("blueprint")))


REQUIRED_DIRS = [
    ".sdd/templates/spec",
    ".sdd/templates/contract",
    ".sdd/templates/test",
    ".sdd/schemas",
    ".sdd/specs/_archive",
    ".sdd/contracts/api",
    ".sdd/contracts/data",
    ".sdd/contracts/behavior",
    ".sdd/contracts/performance",
    ".sdd/tests/contract",
    ".sdd/tests/unit",
    ".sdd/tests/integration",
    ".sdd/tests/acceptance",
    ".sdd/tests/performance",
    ".sdd/docs/architecture",
    ".sdd/docs/diagrams",
]


# ─────────────────────────────────────────────────────────────────────────────
# Skill-Provider-Abstraktion (Strategy Pattern – SPEC-0018/SPEC-0020)
# ─────────────────────────────────────────────────────────────────────────────

@runtime_checkable
class SkillProvider(Protocol):
    """Strategy-Interface: Ein Provider definiert Quelle und Ziel der Skill-Dateien."""

    name: str
    source_subdir: str   # relativ zu .sdd/templates/agents-md/
    target_dir: str      # relativ zum Projekt-Root
    description: str


@dataclass(frozen=True)
class ClaudeSkillProvider:
    """Claude Code Custom Commands (.claude/commands/)."""

    name: str = "claude"
    source_subdir: str = "providers/claude"
    target_dir: str = ".claude/commands"
    description: str = "Claude Code Slash Commands (/sdd, /sdd-new, …)"


@dataclass(frozen=True)
class CopilotSkillProvider:
    """GitHub Copilot – Platzhalter, noch nicht implementiert."""

    name: str = "copilot"
    source_subdir: str = "providers/copilot"
    target_dir: str = ".github/copilot"
    description: str = "GitHub Copilot Instructions (coming soon)"


@dataclass(frozen=True)
class OpenAISkillProvider:
    """OpenAI / Cursor – Platzhalter, noch nicht implementiert."""

    name: str = "openai"
    source_subdir: str = "providers/openai"
    target_dir: str = ".cursor/rules"
    description: str = "Cursor / OpenAI Rules (coming soon)"


SKILL_PROVIDERS: dict[str, SkillProvider] = {
    "claude": ClaudeSkillProvider(),
    "copilot": CopilotSkillProvider(),
    "openai": OpenAISkillProvider(),
}


def get_skill_provider(name: str) -> SkillProvider:
    if name not in SKILL_PROVIDERS:
        available = ", ".join(SKILL_PROVIDERS)
        raise ValueError(
            f"Unbekannter Skill-Provider: {name!r}. Verfügbar: {available}"
        )
    return SKILL_PROVIDERS[name]


def copy_skill_files(
    target: Path,
    blueprint_root: Path,
    provider: str = "claude",
    force: bool = False,
) -> tuple[list[Path], list[Path]]:
    """Kopiert Skill-Dateien aus dem Blueprint ins Ziel-Projekt.

    Returns (created, skipped).
    Existierende Dateien werden ohne force=True übersprungen (Idempotenz, SPEC-0018 FR-02).
    """
    prov = get_skill_provider(provider)
    src_dir = (
        blueprint_root / "templates" / "agents-md" / prov.source_subdir
    )
    if not src_dir.exists():
        return [], []

    dst_dir = target / prov.target_dir
    dst_dir.mkdir(parents=True, exist_ok=True)

    created: list[Path] = []
    skipped: list[Path] = []

    for src_file in sorted(src_dir.glob("*.md")):
        dst_file = dst_dir / src_file.name
        if dst_file.exists() and not force:
            skipped.append(dst_file)
        else:
            shutil.copy(src_file, dst_file)
            created.append(dst_file)

    return created, skipped


def merge_claude_settings(target: Path, blueprint_root: Path) -> bool:
    """Mergt SDD-Permissions aus dem Blueprint in .claude/settings.json.

    Bestehende Einträge bleiben erhalten; neue werden hinzugefügt (kein Duplikat).
    Returns True wenn die Datei erstellt oder geändert wurde.
    """
    src = (
        blueprint_root / "templates" / "agents-md" / "providers" / "claude" / "settings.json"
    )
    if not src.exists():
        return False

    blueprint_settings: dict = json.loads(src.read_text(encoding="utf-8"))
    new_entries: list[str] = (
        blueprint_settings.get("permissions", {}).get("allow", [])
    )

    dst = target / ".claude" / "settings.json"
    if dst.exists():
        existing: dict = json.loads(dst.read_text(encoding="utf-8"))
    else:
        existing = {"permissions": {"allow": []}}
        dst.parent.mkdir(parents=True, exist_ok=True)

    current_allow: list[str] = existing.setdefault("permissions", {}).setdefault("allow", [])
    added = [e for e in new_entries if e not in current_allow]
    changed = bool(added)
    if added:
        current_allow.extend(added)

    # Hooks (z.B. Guardrail) additiv + idempotent mergen (SPEC-0051 FR-02)
    if _merge_hooks(existing, blueprint_settings.get("hooks", {})):
        changed = True

    if not changed:
        return False

    dst.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
    return True


def _hook_block_present(target_blocks: list, block: dict) -> bool:
    """True, wenn ein Block mit gleichem matcher und überlappendem Hook-Command existiert."""
    cmds = {h.get("command") for h in block.get("hooks", []) if h.get("type") == "command"}
    for tb in target_blocks:
        if tb.get("matcher") != block.get("matcher"):
            continue
        tb_cmds = {h.get("command") for h in tb.get("hooks", []) if h.get("type") == "command"}
        if cmds & tb_cmds:
            return True
    return False


def _merge_hooks(existing: dict, blueprint_hooks: dict) -> bool:
    """Mergt Hook-Blöcke additiv und idempotent. Returns True bei Änderung."""
    if not blueprint_hooks:
        return False
    changed = False
    hooks = existing.setdefault("hooks", {})
    for event, blocks in blueprint_hooks.items():
        target_blocks = hooks.setdefault(event, [])
        for block in blocks:
            if not _hook_block_present(target_blocks, block):
                target_blocks.append(block)
                changed = True
    return changed


def copy_guardrail_hook(target: Path, blueprint_root: Path) -> Path | None:
    """Kopiert den Guardrail-Hook-Wrapper aus dem Blueprint nach .claude/hooks/ (ausführbar)."""
    src = blueprint_root / ".claude" / "hooks" / "autonomous-guardrail.sh"
    if not src.exists():
        return None
    dst_dir = target / ".claude" / "hooks"
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / "autonomous-guardrail.sh"
    shutil.copy(src, dst)
    dst.chmod(dst.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return dst


def write_autonomous_local(target: Path) -> None:
    """Setzt permissions.defaultMode=bypassPermissions in settings.local.json (opt-in, lokal).

    Schreibt NICHT in committed settings.json; ergänzt .gitignore (SPEC-0051 FR-03).
    """
    local = target / ".claude" / "settings.local.json"
    local.parent.mkdir(parents=True, exist_ok=True)
    data: dict = json.loads(local.read_text(encoding="utf-8")) if local.exists() else {}
    data.setdefault("permissions", {})["defaultMode"] = "bypassPermissions"
    local.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    gitignore = target / ".gitignore"
    existing = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    if "settings.local.json" not in existing:
        prefix = "" if (not existing or existing.endswith("\n")) else "\n"
        gitignore.write_text(existing + prefix + ".claude/settings.local.json\n", encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# Projekt-Initialisierung
# ─────────────────────────────────────────────────────────────────────────────

def init_project(
    target: Path,
    title: str,
    force: bool = False,
    skill_provider: str = "claude",
    force_skills: bool = False,
    autonomous: bool = False,
) -> dict[str, list[Path]]:
    """Legt die SDD-Struktur an.

    Returns dict mit 'created', 'skill_created', 'skill_skipped'.
    """
    target = target.resolve()
    target.mkdir(parents=True, exist_ok=True)

    created: list[Path] = []

    # Verzeichnisse anlegen
    for rel in REQUIRED_DIRS:
        d = target / rel
        if not d.exists():
            d.mkdir(parents=True)
            created.append(d)

    # Templates und Schemas kopieren
    src_root = _blueprint_root()
    for sub in ["templates", "schemas"]:
        src = src_root / sub
        if src.exists():
            for src_file in src.rglob("*"):
                if src_file.is_dir():
                    continue
                rel = src_file.relative_to(src)
                dst_file = (target / ".sdd" / sub) / rel
                if dst_file.exists() and not force:
                    continue
                dst_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(src_file, dst_file)
                created.append(dst_file)

    # specs/README kopieren falls vorhanden
    readme_src = src_root / "specs" / "README.md"
    readme_dst = target / ".sdd" / "specs" / "README.md"
    if readme_src.exists() and (not readme_dst.exists() or force):
        shutil.copy(readme_src, readme_dst)
        created.append(readme_dst)

    # config.yaml anlegen (mit ausgefülltem Projektnamen)
    config_dst = target / ".sdd" / "config.yaml"
    if not config_dst.exists() or force:
        config_src = src_root / "config.yaml"
        text = config_src.read_text(encoding="utf-8")
        text = text.replace("<PROJECT_TITLE>", title)
        # Replace the project name value regardless of what the template contains
        text = re.sub(r'^(  name: ).*$', rf'\g<1>{title}', text, count=1, flags=re.MULTILINE)
        config_dst.write_text(text, encoding="utf-8")
        created.append(config_dst)

    # Dockerfile + entrypoint.sh nach .sdd/ kopieren.
    #
    # config.yaml verweist mit `dockerfile: .sdd/Dockerfile` auf eine Datei, die
    # das Blueprint nie auslieferte. Der Fehler fiel erst beim ersten
    # Container-Schritt auf: `sdd start` ruft mgr.build(), und das bricht mit
    # "Dockerfile nicht gefunden" ab. Dieselbe Klasse wie #16 (AGENTS.md) und
    # #55 (GitHub-Workflow) — die Konfiguration nannte eine Datei, die `sdd init`
    # nicht anlegte.
    #
    # Der entrypoint gehoert mit dazu: ohne ihn scheitert das COPY im Dockerfile.
    for name in ("Dockerfile", "entrypoint.sh"):
        src_file = src_root / "container" / name
        dst_file = target / ".sdd" / name
        if src_file.exists() and (not dst_file.exists() or force):
            shutil.copy(src_file, dst_file)
            if name.endswith(".sh"):
                dst_file.chmod(0o755)
            created.append(dst_file)

    # AGENTS.md im Projekt-Root anlegen.
    #
    # Die Vorlage lag im Blueprint, wurde aber nur nach .sdd/templates/ kopiert
    # und nie in den Projekt-Root. `sdd validate` warnte deshalb in jedem frischen
    # Projekt und verwies auf `sdd new agents-md` — einen Befehl, der seinerseits
    # auf `sdd init` zurueckverweist und mit exit 1 endet. Der Hinweis "in sdd init
    # integriert" stimmt erst mit dieser Zeile.
    agents_src = src_root / "templates" / "agents-md" / "default.md"
    agents_dst = target / "AGENTS.md"
    if agents_src.exists() and (not agents_dst.exists() or force):
        shutil.copy(agents_src, agents_dst)
        created.append(agents_dst)

    # Skill-Dateien kopieren
    skill_created, skill_skipped = copy_skill_files(
        target, src_root, provider=skill_provider, force=force_skills,
    )

    # Claude-Settings mergen + Guardrail-Hook installieren (nur beim Claude-Provider)
    if skill_provider == "claude":
        merge_claude_settings(target, src_root)
        hook = copy_guardrail_hook(target, src_root)
        if hook is not None:
            created.append(hook)
        if autonomous:
            write_autonomous_local(target)

    # Globale mkcert-Zertifikate kopieren (wenn ~/.local/share/sdd/certs/ vorhanden)
    global_certs = Path.home() / ".local/share/sdd/certs"
    if global_certs.exists() and (global_certs / "cert.pem").exists():
        cert_dst = target / ".certs"
        cert_dst.mkdir(exist_ok=True)
        for name in ("cert.pem", "key.pem", "rootCA.pem"):
            dst_cert = cert_dst / name
            src_cert = global_certs / name
            if not dst_cert.exists() and src_cert.exists():
                shutil.copy(src_cert, dst_cert)
                created.append(dst_cert)

    return {
        "created": created,
        "skill_created": skill_created,
        "skill_skipped": skill_skipped,
    }
