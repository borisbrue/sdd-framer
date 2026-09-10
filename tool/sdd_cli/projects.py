"""Projektverwaltung für SDD – liest/schreibt .sdd/projects/*.yaml."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import yaml

from .config import SddConfig

VALID_AUTONOMY_LEVELS = {1, 2, 3, 3.5, 4}


@dataclass
class Project:
    id: str
    name: str
    owner: str
    status: str          # active | archived | planning
    description: str
    created: str
    autonomy_level: float = 1   # 1 | 2 | 3 | 3.5 | 4 (Dark Factory Level)
    file: Path = field(repr=False, default=Path("."))

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "owner": self.owner,
            "status": self.status,
            "description": self.description,
            "created": self.created,
            "autonomy_level": self.autonomy_level,
        }


def _load_yaml(path: Path) -> dict:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def list_projects(config: SddConfig) -> list[Project]:
    pdir = config.projects_dir
    if not pdir.exists():
        return []
    projects = []
    for yf in sorted(pdir.glob("*.yaml")):
        raw = _load_yaml(yf)
        if not raw.get("id"):
            continue
        raw_level = raw.get("autonomy_level", 1)
        try:
            level = float(str(raw_level))
        except (TypeError, ValueError):
            level = 1.0
        if level not in VALID_AUTONOMY_LEVELS:
            level = 1.0
        projects.append(Project(
            id=raw["id"],
            name=raw.get("name", ""),
            owner=raw.get("owner", ""),
            status=raw.get("status", "active"),
            description=raw.get("description", ""),
            created=str(raw.get("created", "")),
            autonomy_level=level,
            file=yf,
        ))
    return projects


def load_project(config: SddConfig, project_id: str) -> Project | None:
    for p in list_projects(config):
        if p.id == project_id:
            return p
    return None


def _next_project_id(config: SddConfig) -> str:
    prefix = config.prefix("project")
    padding = config.id_padding()
    existing = {p.id for p in list_projects(config)}
    numbers = [int(i.split("-")[1]) for i in existing if re.match(rf"^{prefix}-\d+$", i)]
    nxt = (max(numbers) + 1) if numbers else 1
    return f"{prefix}-{str(nxt).zfill(padding)}"


def save_project(project: Project) -> None:
    """Schreibt einen Project-Datensatz zurück in seine YAML-Datei."""
    data = project.as_dict()
    project.file.write_text(
        yaml.dump(data, allow_unicode=True, default_flow_style=False),
        encoding="utf-8",
    )


def set_autonomy_level(config: SddConfig, project_id: str, level: float) -> Project:
    """Setzt autonomy_level eines Projekts und persistiert die Änderung."""
    if level not in VALID_AUTONOMY_LEVELS:
        raise ValueError(
            f"Ungültiges Autonomy Level: {level}. "
            f"Erlaubt: {sorted(VALID_AUTONOMY_LEVELS)}"
        )
    project = load_project(config, project_id)
    if project is None:
        raise ValueError(f"Projekt nicht gefunden: {project_id}")
    project.autonomy_level = level
    save_project(project)
    return project


def create_project(
    config: SddConfig,
    name: str,
    owner: str = "",
    status: str = "active",
    description: str = "",
    autonomy_level: float = 1,
) -> Project:
    pdir = config.projects_dir
    pdir.mkdir(parents=True, exist_ok=True)

    if autonomy_level not in VALID_AUTONOMY_LEVELS:
        autonomy_level = 1

    pid = _next_project_id(config)
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    target = pdir / f"{pid}-{slug}.yaml"

    data = {
        "id": pid,
        "name": name,
        "owner": owner,
        "status": status,
        "description": description,
        "created": str(date.today()),
        "autonomy_level": autonomy_level,
    }
    target.write_text(yaml.dump(data, allow_unicode=True, default_flow_style=False), encoding="utf-8")

    return Project(**{**data, "file": target})
