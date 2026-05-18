"""`sdd init` – legt die Blueprint-Struktur in einem Projekt an."""
from __future__ import annotations

import re
import shutil
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
    ".sdd/templates/adr",
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
    ".sdd/docs/adr",
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


# ─────────────────────────────────────────────────────────────────────────────
# Projekt-Initialisierung
# ─────────────────────────────────────────────────────────────────────────────

def init_project(
    target: Path,
    title: str,
    force: bool = False,
    skill_provider: str = "claude",
    force_skills: bool = False,
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

    # Skill-Dateien kopieren
    skill_created, skill_skipped = copy_skill_files(
        target, src_root, provider=skill_provider, force=force_skills,
    )

    return {
        "created": created,
        "skill_created": skill_created,
        "skill_skipped": skill_skipped,
    }
