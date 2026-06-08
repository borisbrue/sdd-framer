from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from sdd_cli.frontmatter import parse_safe
from sdd_cli.ids import next_id
from sdd_cli.templates import CONTRACT_TEMPLATES, copy_skeleton, load_template, render, slugify

sys.path.insert(0, str(Path(__file__).parents[1]))
from sdd_context import get_config

router = APIRouter()

SUBDIR_MAP = {
    "openapi": "api", "asyncapi": "api", "graphql": "api", "grpc": "api",
    "json-schema": "data", "avro": "data", "protobuf": "data",
    "gherkin": "behavior", "markdown": "behavior",
    "slo-yaml": "performance",
}
EXT_MAP = {
    "openapi": "openapi.yaml", "asyncapi": "asyncapi.yaml",
    "graphql": "graphql", "grpc": "proto",
    "json-schema": "schema.json", "avro": "avsc", "protobuf": "proto",
    "gherkin": "feature", "markdown": "md",
    "slo-yaml": "slo.yaml",
}


class ContractCreate(BaseModel):
    spec_id: str
    format: str
    title: str = ""


def _contract_dict(md: Path, cfg_root: Path, *, with_body: bool = False) -> dict[str, Any]:
    doc = parse_safe(md)
    if not doc:
        return {}
    fm = doc.frontmatter
    artifact = fm.get("artifact", "")
    abs_artifact = str(cfg_root / artifact) if artifact else ""
    d: dict[str, Any] = {
        "id": fm.get("id"),
        "title": fm.get("title", ""),
        "type": fm.get("type", ""),
        "format": fm.get("format", ""),
        "spec": fm.get("spec", ""),
        "status": fm.get("status", "draft"),
        "version": fm.get("version", ""),
        "artifact": artifact,
        "abs_artifact": abs_artifact,
        "tests": fm.get("tests") or [],
        "file": str(md.relative_to(cfg_root)),
        "abs_file": str(md),
    }
    if with_body:
        d["body"] = doc.body
        # Artifact-Inhalt mitliefern, wenn vorhanden
        artifact_path = cfg_root / artifact if artifact else None
        if artifact_path and artifact_path.exists():
            d["artifact_content"] = artifact_path.read_text(encoding="utf-8")
    return d


def _find_contract(contract_id: str) -> tuple[Path, Any] | None:
    cfg = get_config()
    for md in cfg.contracts_dir.rglob("*.md"):
        doc = parse_safe(md)
        if doc and doc.frontmatter.get("id") == contract_id:
            return md, cfg
    return None


@router.get("/contracts", summary="Alle Contracts auflisten")
def list_contracts() -> list[dict[str, Any]]:
    cfg = get_config()
    result = []
    for md in sorted(cfg.contracts_dir.rglob("*.md")):
        d = _contract_dict(md, cfg.root)
        if d.get("id"):
            result.append(d)
    return result


@router.get("/contracts/{contract_id}", summary="Einen Contract abrufen")
def get_contract(contract_id: str) -> dict[str, Any]:
    cfg = get_config()
    for md in cfg.contracts_dir.rglob("*.md"):
        doc = parse_safe(md)
        if doc and doc.frontmatter.get("id") == contract_id:
            return _contract_dict(md, cfg.root, with_body=True)
    raise HTTPException(status_code=404, detail=f"{contract_id} nicht gefunden.")


class StatusPatch(BaseModel):
    status: str


@router.patch("/contracts/{contract_id}/status", summary="Contract-Status setzen")
def patch_contract_status(contract_id: str, body: StatusPatch) -> dict[str, Any]:
    found = _find_contract(contract_id)
    if not found:
        raise HTTPException(status_code=404, detail=f"{contract_id} nicht gefunden.")
    md, _ = found
    doc = parse_safe(md)
    if not doc:
        raise HTTPException(status_code=500, detail=f"{contract_id} nicht lesbar.")
    doc.frontmatter["status"] = body.status
    doc.write()
    return {"ok": True, "id": contract_id, "status": body.status}


class BodyPatch(BaseModel):
    body: str


@router.patch("/contracts/{contract_id}/body", summary="Contract-Body überschreiben")
def patch_contract_body(contract_id: str, body: BodyPatch) -> dict[str, Any]:
    found = _find_contract(contract_id)
    if not found:
        raise HTTPException(status_code=404, detail=f"{contract_id} nicht gefunden.")
    md, _ = found
    doc = parse_safe(md)
    if not doc:
        raise HTTPException(status_code=500, detail=f"{contract_id} nicht lesbar.")
    doc.body = body.body
    doc.write()
    return {"ok": True, "id": contract_id}


@router.post("/contracts", status_code=201, summary="Neuen Contract anlegen")
def create_contract(body: ContractCreate) -> dict[str, Any]:
    cfg = get_config()
    fmt = body.format
    if fmt not in CONTRACT_TEMPLATES:
        raise HTTPException(status_code=422, detail=f"Unbekanntes Format: {fmt}")

    cid = next_id(cfg, "contract")
    slug = slugify(body.title or fmt)
    subdir = SUBDIR_MAP[fmt]
    target = cfg.contracts_dir / subdir / f"{cid}-{slug}.md"
    target.parent.mkdir(parents=True, exist_ok=True)

    artifact_rel = f"contracts/{subdir}/{slug}.{EXT_MAP[fmt]}"
    tmpl, skeleton = load_template(cfg, "contract", contract_format=fmt)
    text = render(tmpl, {
        "id": cid,
        "title": body.title or f"{fmt} contract",
        "spec": body.spec_id,
        "artifact": artifact_rel,
    })
    target.write_text(text, encoding="utf-8")
    if skeleton:
        copy_skeleton(cfg, skeleton, cfg.root / artifact_rel)

    # Link contract back to spec frontmatter
    if body.spec_id:
        spec_files = list(cfg.specs_dir.rglob(f"{body.spec_id}-*.md"))
        if spec_files:
            spec_doc = parse_safe(spec_files[0])
            if spec_doc:
                existing = spec_doc.frontmatter.get("contracts") or []
                if cid not in existing:
                    spec_doc.frontmatter["contracts"] = existing + [cid]
                    spec_doc.write()

    return {"id": cid, "file": str(target.relative_to(cfg.root)), "abs_file": str(target)}
