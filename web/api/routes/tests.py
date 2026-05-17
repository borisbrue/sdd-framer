from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from sdd_cli.frontmatter import parse_safe
from sdd_cli.ids import next_id
from sdd_cli.templates import load_template, render, slugify
from sdd_cli import test_runner as _test_runner

sys.path.insert(0, str(Path(__file__).parents[1]))
from sdd_context import get_config

router = APIRouter()

TEST_LEVELS = ["unit", "integration", "contract", "acceptance", "performance", "property"]


class TestCreate(BaseModel):
    spec_id: str
    contract_id: str
    level: str
    title: str = ""


def _test_dict(md: Path, cfg_root: Path, *, with_body: bool = False) -> dict[str, Any]:
    doc = parse_safe(md)
    if not doc:
        return {}
    fm = doc.frontmatter
    d: dict[str, Any] = {
        "id": fm.get("id"),
        "project": fm.get("project", ""),
        "title": fm.get("title", ""),
        "level": fm.get("level", ""),
        "spec": fm.get("spec", ""),
        "contract": fm.get("contract", ""),
        "status": fm.get("status", "draft"),
        "version": fm.get("version", ""),
        "framework": fm.get("framework", ""),
        "file": str(md.relative_to(cfg_root)),
        "abs_file": str(md),
    }
    if with_body:
        d["body"] = doc.body
    return d


@router.get("/tests", summary="Alle Tests auflisten")
def list_tests() -> list[dict[str, Any]]:
    cfg = get_config()
    result = []
    for md in sorted(cfg.tests_dir.rglob("*.md")):
        d = _test_dict(md, cfg.root)
        if d.get("id"):
            result.append(d)
    return result


@router.get("/tests/{test_id}", summary="Einen Test abrufen")
def get_test(test_id: str) -> dict[str, Any]:
    cfg = get_config()
    for md in cfg.tests_dir.rglob("*.md"):
        doc = parse_safe(md)
        if doc and doc.frontmatter.get("id") == test_id:
            return _test_dict(md, cfg.root, with_body=True)
    raise HTTPException(status_code=404, detail=f"{test_id} nicht gefunden.")


@router.post("/tests", status_code=201, summary="Neuen Test anlegen")
def create_test(body: TestCreate) -> dict[str, Any]:
    cfg = get_config()
    tid = next_id(cfg, "test")
    slug = slugify(body.title or body.level)
    target = cfg.tests_dir / body.level / f"{tid}-{slug}.md"
    target.parent.mkdir(parents=True, exist_ok=True)

    tmpl, _ = load_template(cfg, "test")
    text = render(tmpl, {
        "id": tid,
        "title": body.title or f"{body.level} test",
        "spec": body.spec_id,
        "contract": body.contract_id,
    })
    text = text.replace("level: contract", f"level: {body.level}", 1)
    target.write_text(text, encoding="utf-8")

    return {"id": tid, "file": str(target.relative_to(cfg.root)), "abs_file": str(target)}


@router.get("/specs/{spec_id}/test-results", summary="Letzten Test-Run einer Spec abrufen")
def get_test_results(spec_id: str) -> dict[str, Any]:
    cfg = get_config()
    report = _test_runner.latest_report(cfg, spec_id)
    if report is None:
        raise HTTPException(
            status_code=404,
            detail=f"Noch kein Test-Run für {spec_id} gefunden. POST /specs/{spec_id}/test-run aufrufen.",
        )
    return report.to_json()


@router.post("/specs/{spec_id}/test-run", summary="Test-Run für eine Spec auslösen")
def trigger_test_run(spec_id: str) -> dict[str, Any]:
    cfg = get_config()
    try:
        report = _test_runner.run(cfg, spec_id)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    return report.to_json()
