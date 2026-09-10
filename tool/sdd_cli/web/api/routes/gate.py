"""Execution Gate API – CON-0027, SPEC-0014.

All endpoints under /api/gate/{spec_id}/...
Sub-router of CON-0007 (orchestrate-api).
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Ensure sdd_cli is importable
sys.path.insert(0, str(Path(__file__).parents[3] / "tool"))
sys.path.insert(0, str(Path(__file__).parents[1]))

from sdd_context import get_config

from sdd_cli.conflict_detector import ConflictDetector
from sdd_cli.gate import ExecutionGate
from sdd_cli.test_generator import TestGenerator

router = APIRouter()


# ─── Request/Response models ──────────────────────────────────────────────────

class ProposeContractsRequest(BaseModel):
    contracts: list[str] = []


class ConflictUpdateRequest(BaseModel):
    action: str
    reason: str | None = None
    resolve_strategy: str | None = None


class ApproveRequest(BaseModel):
    fr_coverage: str = ""
    scenarios_covered: str = ""


class ForceExecuteRequest(BaseModel):
    override_reason: str | None = None


# ─── GET /gate/{spec_id}/status ──────────────────────────────────────────────

@router.get("/gate/{spec_id}/status", summary="Gate-Status abrufen (CON-0027)")
def get_gate_status(spec_id: str) -> dict[str, Any]:
    cfg = get_config()
    g = ExecutionGate(cfg.root)
    data = g._load(spec_id)
    result = g.check(spec_id)
    return {
        "spec_id": spec_id,
        "pipeline_phase": data.get("pipeline_phase"),
        "blocked": result.blocked,
        "phase_history": data.get("phase_history", []),
        "blocking_issues": data.get("blocking_issues", []),
        "conflict_report_ref": data.get("conflict_report_ref"),
        "override": data.get("override"),
    }


# ─── POST /gate/{spec_id}/spec-review ────────────────────────────────────────

@router.post("/gate/{spec_id}/spec-review", status_code=202,
             summary="Phase 2: Spec-Review starten")
def spec_review(spec_id: str) -> dict[str, Any]:
    cfg = get_config()
    g = ExecutionGate(cfg.root)
    allowed = g.can_start_phase(spec_id, "spec-review")
    if not allowed.allowed:
        raise HTTPException(status_code=409, detail=allowed.reason)
    g.mark_phase_started(spec_id, "spec-review")
    g.mark_phase_complete(spec_id, "spec-review")
    return {"spec_id": spec_id, "phase": "spec-review", "result": "ok"}


# ─── POST /gate/{spec_id}/contract-propose ───────────────────────────────────

@router.post("/gate/{spec_id}/contract-propose", status_code=202,
             summary="Phase 3: Contracts vorschlagen")
def contract_propose(spec_id: str, body: ProposeContractsRequest | None = None) -> dict[str, Any]:
    contracts = body.contracts if body else []
    cfg = get_config()
    g = ExecutionGate(cfg.root)
    allowed = g.can_start_phase(spec_id, "contracts-proposed")
    if not allowed.allowed:
        raise HTTPException(status_code=409, detail=allowed.reason)
    g.mark_phase_started(spec_id, "contracts-proposed")
    g.mark_phase_complete(spec_id, "contracts-proposed", proposed=contracts)
    return {"spec_id": spec_id, "phase": "contracts-proposed", "proposed": contracts}


# ─── POST /gate/{spec_id}/contract-review ────────────────────────────────────

@router.post("/gate/{spec_id}/contract-review", status_code=202,
             summary="Phase 5: Konfliktanalyse starten (CON-0027)")
def contract_review(spec_id: str, body: ProposeContractsRequest | None = None) -> dict[str, Any]:
    contracts = body.contracts if body else []
    cfg = get_config()
    g = ExecutionGate(cfg.root)
    allowed = g.can_start_phase(spec_id, "contracts-review")
    if not allowed.allowed:
        raise HTTPException(status_code=409, detail=allowed.reason)
    g.mark_phase_started(spec_id, "contracts-review")

    d = ConflictDetector(cfg.root)
    report = d.analyze(spec_id, contracts)

    open_high = sum(
        1 for c in report.conflicts
        if c.get("severity") == "high" and c.get("status") == "open"
    )
    if open_high == 0:
        g.mark_phase_complete(
            spec_id, "contracts-review",
            conflicts_found=report.impact_summary["total_conflicts"],
        )
    else:
        g.mark_phase_complete(
            spec_id, "contracts-review", result="failed",
            conflicts_found=report.impact_summary["total_conflicts"],
            open_high=open_high,
        )

    return report.to_dict()


# ─── POST /gate/{spec_id}/test-generate ──────────────────────────────────────

@router.post("/gate/{spec_id}/test-generate", status_code=202,
             summary="Phase 6: Tests generieren (CON-0027)")
def test_generate(spec_id: str, body: ProposeContractsRequest | None = None) -> dict[str, Any]:
    contracts = body.contracts if body else []
    cfg = get_config()
    g = ExecutionGate(cfg.root)
    allowed = g.can_start_phase(spec_id, "tests-generated")
    if not allowed.allowed:
        raise HTTPException(status_code=409, detail=allowed.reason)
    g.mark_phase_started(spec_id, "tests-generated")

    gen = TestGenerator(cfg.root)
    result = gen.generate(spec_id, contracts)

    if result.success:
        g.mark_phase_complete(
            spec_id, "tests-generated",
            files_generated=[f["path"] for f in result.generated_files],
        )
    else:
        g.mark_phase_complete(
            spec_id, "tests-generated", result="failed",
            syntax_errors=result.syntax_errors,
        )
        raise HTTPException(
            status_code=422,
            detail={"message": "Syntaxfehler in generierten Tests", "errors": result.syntax_errors},
        )

    return {
        "spec_id": spec_id,
        "generated_files": result.generated_files,
        "success": result.success,
    }


# ─── POST /gate/{spec_id}/approve ────────────────────────────────────────────

@router.post("/gate/{spec_id}/approve", status_code=200,
             summary="Phase 8: Spec genehmigen (spec-approved → execute-unlocked)")
def approve_spec(spec_id: str, body: ApproveRequest) -> dict[str, Any]:
    cfg = get_config()
    g = ExecutionGate(cfg.root)
    allowed = g.can_start_phase(spec_id, "spec-approved")
    if not allowed.allowed:
        raise HTTPException(status_code=409, detail=allowed.reason)

    consistency = {
        "fr_coverage": body.fr_coverage,
        "scenarios_covered": body.scenarios_covered,
        "contracts_consistent": True,
    }
    g.mark_phase_complete(spec_id, "spec-approved", consistency_check=consistency)
    g.mark_phase_complete(spec_id, "execute-unlocked")

    try:
        from sdd_cli.frontmatter import parse_safe, patch_status
        for md in cfg.specs_dir.rglob("*.md"):
            doc = parse_safe(md)
            if doc and doc.frontmatter.get("id") == spec_id:
                patch_status(md, "approved")
                break
    except Exception:
        pass

    return {"spec_id": spec_id, "phase": "execute-unlocked", "approved": True}


# ─── GET /gate/{spec_id}/conflicts ───────────────────────────────────────────

@router.get("/gate/{spec_id}/conflicts", summary="Konflikte auflisten (CON-0027)")
def list_conflicts(spec_id: str, status: str | None = None) -> list[dict]:
    cfg = get_config()
    report_path = cfg.root / ".sdd" / "conflict-reports" / f"{spec_id}-conflicts.json"
    if not report_path.exists():
        raise HTTPException(status_code=404, detail=f"Kein Konfliktbericht für {spec_id}")
    d = ConflictDetector(cfg.root)
    return d.list_conflicts(spec_id, status_filter=status)


# ─── PATCH /gate/{spec_id}/conflicts/{cf_id} ─────────────────────────────────

@router.patch("/gate/{spec_id}/conflicts/{cf_id}",
              summary="Konflikt auflösen oder bestätigen (CON-0027)")
def update_conflict(spec_id: str, cf_id: str, body: ConflictUpdateRequest) -> dict[str, Any]:
    cfg = get_config()
    d = ConflictDetector(cfg.root)
    action = body.action
    try:
        if action == "acknowledge":
            d.acknowledge(spec_id, cf_id, body.reason)
        elif action == "resolve":
            d.resolve(spec_id, cf_id, body.reason or body.resolve_strategy or "")
        else:
            raise HTTPException(status_code=422, detail=f"Unbekannte Aktion: {action!r}")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {"id": cf_id, "action": action, "updated": True}
