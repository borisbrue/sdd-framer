from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

_CLAUDE_AVAILABLE: bool | None = None


def _check_claude() -> bool:
    global _CLAUDE_AVAILABLE
    if _CLAUDE_AVAILABLE is None:
        _CLAUDE_AVAILABLE = shutil.which("claude") is not None
    return _CLAUDE_AVAILABLE

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from sdd_cli.frontmatter import parse_safe
from sdd_cli.maintenance import run_maintenance_sweep
from sdd_cli.traceability import write_matrix
from sdd_cli.validate import validate

sys.path.insert(0, str(Path(__file__).parents[1]))
from sdd_context import get_config, reload_config

router = APIRouter()


@router.get("/status", summary="Projektübersicht")
def project_status() -> dict[str, Any]:
    cfg = get_config()
    specs, contracts, tests = [], [], []

    for md in sorted(cfg.specs_dir.rglob("*.md")):
        doc = parse_safe(md)
        if doc and doc.frontmatter.get("id"):
            specs.append(doc.frontmatter)

    for md in sorted(cfg.contracts_dir.rglob("*.md")):
        doc = parse_safe(md)
        if doc and doc.frontmatter.get("id"):
            contracts.append(doc.frontmatter)

    for md in sorted(cfg.tests_dir.rglob("*.md")):
        doc = parse_safe(md)
        if doc and doc.frontmatter.get("id"):
            tests.append(doc.frontmatter)

    gaps = sum(
        1 for s in specs
        if not (s.get("contracts") or []) or not (s.get("tests") or [])
    )

    return {
        "project": cfg.raw.get("project", {}).get("name", "SDD Project"),
        "specs": len(specs),
        "contracts": len(contracts),
        "tests": len(tests),
        "gaps": gaps,
        "has_claude_cli": _check_claude(),
        "evaluator_base_url": cfg.raw.get("evaluator", {}).get("base_url", ""),
        "project_root": str(cfg.root),
    }


@router.post("/validate", summary="sdd validate ausführen")
def run_validate() -> dict[str, Any]:
    cfg = get_config()
    report = validate(cfg)
    return {
        "ok": report.ok,
        "errors": [
            {"file": str(i.file.relative_to(cfg.root)), "message": i.message, "instruction": i.instruction}
            for i in report.errors
        ],
        "warnings": [
            {"file": str(i.file.relative_to(cfg.root)), "message": i.message, "instruction": i.instruction}
            for i in report.warnings
        ],
    }


@router.post("/trace", summary="Traceability-Matrix aktualisieren")
def run_trace() -> dict[str, Any]:
    cfg = get_config()
    path = write_matrix(cfg)
    return {"ok": True, "file": str(path.relative_to(cfg.root))}


@router.get("/formats", summary="Verfügbare Contract-Formate")
def list_formats() -> list[str]:
    from sdd_cli.templates import CONTRACT_TEMPLATES
    return list(CONTRACT_TEMPLATES.keys())


class OpenRequest(BaseModel):
    abs_file: str
    line: int = 1


@router.get("/maintenance", summary="Maintenance-Sweep durchführen")
def run_maintenance() -> dict[str, Any]:
    cfg = get_config()
    report = run_maintenance_sweep(cfg)
    return report.to_dict(cfg.root)


class ConfigRaw(BaseModel):
    yaml: str


class ConfigPatch(BaseModel):
    project_name: str | None = None
    evaluator_base_url: str | None = None
    max_retries: int | None = None
    spec_lifecycle: list[str] | None = None


@router.get("/config", summary="config.yaml lesen")
def get_config_content() -> dict[str, Any]:
    import yaml
    cfg = get_config()
    config_file = cfg.root / ".sdd" / "config.yaml"
    raw = config_file.read_text(encoding="utf-8") if config_file.exists() else ""
    return {
        "yaml": raw,
        "project_name": cfg.raw.get("project", {}).get("name", ""),
        "evaluator_base_url": cfg.raw.get("evaluator", {}).get("base_url", ""),
        "max_retries": cfg.raw.get("orchestrator", {}).get("max_retries", 3),
        "spec_lifecycle": cfg.raw.get("spec_lifecycle", ["draft", "review", "approved", "implemented", "deprecated"]),
    }


@router.put("/config", summary="config.yaml als Raw-YAML schreiben")
def save_config_raw(body: ConfigRaw) -> dict[str, Any]:
    import yaml
    try:
        yaml.safe_load(body.yaml)
    except yaml.YAMLError as e:
        raise HTTPException(status_code=422, detail=f"Ungültiges YAML: {e}")
    cfg = get_config()
    config_file = cfg.root / ".sdd" / "config.yaml"
    config_file.write_text(body.yaml, encoding="utf-8")
    reload_config()
    return {"ok": True}


@router.patch("/config", summary="Einzelne Config-Felder aktualisieren")
def patch_config_fields(body: ConfigPatch) -> dict[str, Any]:
    import yaml
    cfg = get_config()
    config_file = cfg.root / ".sdd" / "config.yaml"
    data: dict = dict(cfg.raw)

    if body.project_name is not None:
        data.setdefault("project", {})["name"] = body.project_name
    if body.evaluator_base_url is not None:
        data.setdefault("evaluator", {})["base_url"] = body.evaluator_base_url
    if body.max_retries is not None:
        data.setdefault("orchestrator", {})["max_retries"] = body.max_retries
    if body.spec_lifecycle is not None:
        data["spec_lifecycle"] = body.spec_lifecycle

    config_file.write_text(
        yaml.dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )
    reload_config()
    return {"ok": True}


@router.post("/open", summary="Datei im Editor öffnen")
def open_in_editor(body: OpenRequest) -> dict[str, Any]:
    """Öffnet eine Datei im VS Code Editor via CLI."""
    path = Path(body.abs_file)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Datei nicht gefunden: body.abs_file")

    # VS Code-Binary suchen (Flatpak, Standard, Fallback)
    candidates = ["/app/bin/code", "/usr/bin/code", shutil.which("code") or ""]
    code_bin = next((c for c in candidates if c and Path(c).exists()), None)

    if not code_bin:
        raise HTTPException(status_code=503, detail="VS Code nicht gefunden.")

    try:
        subprocess.Popen(  # noqa: S603
            [code_bin, "--goto", f"{path}:{body.line}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    return {"ok": True, "opened": str(path)}
