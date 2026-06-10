from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from sdd_cli.frontmatter import parse_safe
from sdd_cli.ids import next_id
from sdd_cli.templates import load_template, render, slugify
from sdd_cli.validate import validate

sys.path.insert(0, str(Path(__file__).parents[1]))
from analysis_repository import AnalysisRepository
from sdd_context import get_config

router = APIRouter()


class SpecCreate(BaseModel):
    title: str
    owner: str = ""
    priority: str = "medium"


class SpecUpdate(BaseModel):
    body: str


class StatusPatch(BaseModel):
    status: str


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


@router.patch("/specs/{spec_id}/status", summary="Spec-Status setzen")
def patch_spec_status(spec_id: str, body: StatusPatch) -> dict[str, Any]:
    cfg = get_config()
    for md in cfg.specs_dir.rglob("*.md"):
        doc = parse_safe(md)
        if doc and doc.frontmatter.get("id") == spec_id:
            doc.frontmatter["status"] = body.status
            doc.write()
            return {"ok": True, "id": spec_id, "status": body.status}
    raise HTTPException(status_code=404, detail=f"{spec_id} nicht gefunden.")


@router.post("/specs/{spec_id}/approve", summary="Gate-Prüfung und Freigabe")
def approve_spec(spec_id: str) -> dict[str, Any]:
    """Prüft alle Gate-Bedingungen. Setzt status=approved wenn alle bestehen."""
    cfg = get_config()

    # Spec-Datei finden
    spec_md: Path | None = None
    for md in cfg.specs_dir.rglob("*.md"):
        doc = parse_safe(md)
        if doc and doc.frontmatter.get("id") == spec_id:
            spec_md = md
            break
    if spec_md is None:
        raise HTTPException(status_code=404, detail=f"{spec_id} nicht gefunden.")

    checks: list[dict[str, Any]] = []

    # ── 1. Validation ──────────────────────────────────────────────────────────
    report = validate(cfg)
    spec_errors = [e for e in report.errors if spec_id in str(e.file) or spec_id in e.message]
    if spec_errors:
        checks.append({
            "name": "Validation",
            "passed": False,
            "message": "; ".join(e.message for e in spec_errors[:3]),
        })
    else:
        checks.append({"name": "Validation", "passed": True, "message": "Keine Fehler"})

    # ── 2. Mindestens ein Contract ─────────────────────────────────────────────
    contracts = [
        md for md in cfg.contracts_dir.rglob("*.md")
        if (doc := parse_safe(md)) and doc.frontmatter.get("spec") == spec_id
    ]
    if contracts:
        checks.append({"name": "Contract", "passed": True, "message": f"{len(contracts)} Contract(s) definiert"})
    else:
        checks.append({"name": "Contract", "passed": False, "message": "Kein Contract definiert"})

    # ── 3. Mindestens ein Test ─────────────────────────────────────────────────
    tests_dir = cfg.root / cfg.raw.get("tests_dir", ".sdd/tests")
    tests = [
        md for md in tests_dir.rglob("*.md")
        if (doc := parse_safe(md)) and doc.frontmatter.get("spec") == spec_id
    ]
    if tests:
        checks.append({"name": "Test", "passed": True, "message": f"{len(tests)} Test(s) definiert"})
    else:
        checks.append({"name": "Test", "passed": False, "message": "Kein Test definiert"})

    # ── 4. KI-Analyse: keine offenen Fehler ───────────────────────────────────
    analyses_base = cfg.root / ".sdd" / "analyses"
    repo = AnalysisRepository(analyses_base)
    summaries = repo.list(spec_id, limit=1)
    if summaries:
        latest = repo.get(spec_id, summaries[0]["result_id"])
        if latest:
            open_errors = [
                q for q in latest.questions
                if q.get("severity") == "error" and q.get("id") not in latest.dismissed_ids
            ]
            if open_errors:
                checks.append({
                    "name": "KI-Analyse",
                    "passed": False,
                    "message": f"{len(open_errors)} offene Fehler-Nachfrage(n) in letzter Analyse",
                })
            else:
                checks.append({"name": "KI-Analyse", "passed": True, "message": "Keine offenen Fehler"})
        else:
            checks.append({"name": "KI-Analyse", "passed": True, "message": "Keine Analyse vorhanden — übersprungen"})
    else:
        checks.append({"name": "KI-Analyse", "passed": True, "message": "Keine Analyse vorhanden — übersprungen"})

    # ── Entscheidung ───────────────────────────────────────────────────────────
    all_passed = all(c["passed"] for c in checks)
    if all_passed:
        doc = parse_safe(spec_md)
        doc.frontmatter["status"] = "approved"
        doc.write()

    return {
        "approved": all_passed,
        "status": "approved" if all_passed else "review",
        "checks": checks,
    }


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
