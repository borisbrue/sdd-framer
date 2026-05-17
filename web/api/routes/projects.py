"""REST-Endpunkte für Projekte."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parents[3] / "tool"))
sys.path.insert(0, str(Path(__file__).parents[1]))

from sdd_cli.projects import create_project, list_projects, load_project, set_autonomy_level, VALID_AUTONOMY_LEVELS
from sdd_context import get_config

router = APIRouter()


class ProjectCreate(BaseModel):
    name: str
    owner: str = ""
    status: str = "active"
    description: str = ""


class LevelPatch(BaseModel):
    level: float


@router.get("/projects", summary="Alle Projekte auflisten")
def get_projects() -> list[dict[str, Any]]:
    cfg = get_config()
    return [p.as_dict() for p in list_projects(cfg)]


@router.get("/projects/{project_id}", summary="Einzelnes Projekt abrufen")
def get_project(project_id: str) -> dict[str, Any]:
    cfg = get_config()
    p = load_project(cfg, project_id)
    if not p:
        raise HTTPException(status_code=404, detail=f"{project_id} nicht gefunden.")
    return p.as_dict()


@router.post("/projects", status_code=201, summary="Neues Projekt anlegen")
def post_project(body: ProjectCreate) -> dict[str, Any]:
    cfg = get_config()
    p = create_project(cfg, name=body.name, owner=body.owner, status=body.status, description=body.description)
    return p.as_dict()


@router.patch("/projects/{project_id}/level", summary="Autonomy Level setzen")
def patch_project_level(project_id: str, body: LevelPatch) -> dict[str, Any]:
    cfg = get_config()
    if body.level not in VALID_AUTONOMY_LEVELS:
        raise HTTPException(
            status_code=422,
            detail=f"Ungültiges Level {body.level}. Erlaubt: {sorted(VALID_AUTONOMY_LEVELS)}",
        )
    try:
        p = set_autonomy_level(cfg, project_id, body.level)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return p.as_dict()
