from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from sdd_cli.frontmatter import parse_safe
from sdd_cli.ids import next_id
from sdd_cli.templates import load_template, render, slugify

sys.path.insert(0, str(Path(__file__).parents[1]))
from sdd_context import get_config

router = APIRouter()


class SpecCreate(BaseModel):
    title: str
    owner: str = ""
    priority: str = "medium"


class SpecUpdate(BaseModel):
    body: str


def _spec_dict(md: Path, cfg_root: Path, *, with_body: bool = False) -> dict[str, Any]:
    doc = parse_safe(md)
    if not doc:
        return {}
    fm = doc.frontmatter
    d: dict[str, Any] = {
        "id": fm.get("id"),
        "title": fm.get("title", ""),
        "status": fm.get("status", "draft"),
        "priority": fm.get("priority", "medium"),
        "owner": fm.get("owner", ""),
        "contracts": fm.get("contracts") or [],
        "tests": fm.get("tests") or [],
        "adrs": fm.get("adrs") or [],
        "depends_on": fm.get("depends_on") or [],
        "tags": fm.get("tags") or [],
        "version": fm.get("version", ""),
        "created": str(fm.get("created", "")),
        "updated": str(fm.get("updated", "")),
        "file": str(md.relative_to(cfg_root)),
        "abs_file": str(md),
    }
    if with_body:
        d["body"] = doc.body
    return d


@router.get("/specs", summary="Alle Specs auflisten")
def list_specs() -> list[dict[str, Any]]:
    cfg = get_config()
    result = []
    for md in sorted(cfg.specs_dir.rglob("*.md")):
        if md.name == "README.md":
            continue
        d = _spec_dict(md, cfg.root)
        if d.get("id"):
            result.append(d)
    return result


@router.get("/specs/{spec_id}", summary="Eine Spec abrufen")
def get_spec(spec_id: str) -> dict[str, Any]:
    cfg = get_config()
    for md in cfg.specs_dir.rglob("*.md"):
        doc = parse_safe(md)
        if doc and doc.frontmatter.get("id") == spec_id:
            return _spec_dict(md, cfg.root, with_body=True)
    raise HTTPException(status_code=404, detail=f"{spec_id} nicht gefunden.")


@router.put("/specs/{spec_id}", summary="Spec-Body aktualisieren")
def update_spec(spec_id: str, payload: SpecUpdate) -> dict[str, Any]:
    cfg = get_config()
    for md in cfg.specs_dir.rglob("*.md"):
        doc = parse_safe(md)
        if doc and doc.frontmatter.get("id") == spec_id:
            # Frontmatter-Block aus Original behalten, Body ersetzen
            raw = md.read_text(encoding="utf-8")
            if raw.startswith("---"):
                end = raw.find("---", 3)
                if end != -1:
                    frontmatter_block = raw[: end + 3]
                    md.write_text(frontmatter_block + "\n" + payload.body, encoding="utf-8")
                    return _spec_dict(md, cfg.root, with_body=True)
            md.write_text(payload.body, encoding="utf-8")
            return _spec_dict(md, cfg.root, with_body=True)
    raise HTTPException(status_code=404, detail=f"{spec_id} nicht gefunden.")


@router.post("/specs", status_code=201, summary="Neue Spec anlegen")
def create_spec(body: SpecCreate) -> dict[str, Any]:
    cfg = get_config()
    sid = next_id(cfg, "spec")
    slug = slugify(body.title)
    target = cfg.specs_dir / f"{sid}-{slug}.md"
    target.parent.mkdir(parents=True, exist_ok=True)

    tmpl, _ = load_template(cfg, "spec")
    text = render(tmpl, {"id": sid, "title": body.title, "owner": body.owner})
    target.write_text(text, encoding="utf-8")

    return {"id": sid, "file": str(target.relative_to(cfg.root)), "abs_file": str(target)}
