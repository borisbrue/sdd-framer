"""Execute-Flow: POST /api/orchestrate + GET /api/pipeline/{run_id} + GET /api/pipeline/active.

SPEC-0007 §3 — Pipeline-State-Store (In-Memory, TTL 1h).
"""
from __future__ import annotations

import asyncio
import datetime
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parents[1]))
from sdd_context import get_config

router = APIRouter()

# ─── State ───────────────────────────────────────────────────────────────────

@dataclass
class RunState:
    run_id: str
    spec_id: str
    status: str = "running"
    current_step: str = "Pipeline gestartet…"
    attempts: list[dict] = field(default_factory=list)
    max_attempts: int = 3
    issue_url: str | None = None
    report: dict | None = None  # PipelineReport per SPEC-0007 §3.2; None while running
    created_at: float = field(default_factory=time.monotonic)
    log: list[str] = field(default_factory=list)
    abort_requested: bool = False
    active_proc: Any = field(default=None, repr=False, compare=False)

_runs: dict[str, RunState] = {}
_active: dict[str, str] = {}   # spec_id → run_id
_TTL = 3600.0


def _cleanup() -> None:
    now = time.monotonic()
    stale = [k for k, v in _runs.items() if now - v.created_at > _TTL]
    for k in stale:
        run = _runs.pop(k, None)
        if run:
            _active.pop(run.spec_id, None)


def _to_dict(state: RunState) -> dict[str, Any]:
    d: dict[str, Any] = {
        "run_id":       state.run_id,
        "spec_id":      state.spec_id,
        "status":       state.status,
        "attempts":     state.attempts,
        "max_attempts": state.max_attempts,
        "log":          list(state.log),
        "report":       state.report,  # None while running; PipelineReport dict after completion
    }
    if state.current_step:
        d["current_step"] = state.current_step
    if state.issue_url:
        d["issue_url"] = state.issue_url
    return d


def _build_report(state: RunState, final_status: str) -> dict:
    last = state.attempts[-1] if state.attempts else None
    return {
        "pass_rate":        last["eval_pass_rate"] if last and last["eval_pass_rate"] is not None else 0.0,
        "pr_url":           next((a["pr_url"] for a in reversed(state.attempts) if a["pr_url"]), None),
        "issue_url":        state.issue_url,
        "failed_scenarios": [],
        "reason":           last["error"] if last else None,
        "explanation":      last["explanation"] if last and final_status == "dry_run" else None,
    }


# ─── Background worker ───────────────────────────────────────────────────────

def _run_pipeline_bg(run_id: str, body: OrchestrateRequest) -> None:
    from sdd_cli.frontmatter import parse_safe, patch_status
    from sdd_cli.orchestrator import persist_pipeline_report, run_pipeline

    state = _runs.get(run_id)
    if not state:
        return

    def on_step(msg: str) -> None:
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        state.log.append(f"[{ts}] {msg}")
        state.current_step = msg

    on_step("Pipeline gestartet…")

    cfg = get_config()

    project_id = body.project_id
    if not project_id:
        for md in cfg.specs_dir.rglob("*.md"):
            doc = parse_safe(md)
            if doc and doc.frontmatter.get("id") == body.spec_id:
                project_id = doc.frontmatter.get("project", "")
                break

    try:
        report = run_pipeline(
            cfg,
            spec_id=body.spec_id,
            base_url=body.base_url or None,
            build_cmd=None,
            max_retries=cfg.raw.get("orchestrator", {}).get("max_retries", 3),
            no_pr=body.no_pr,
            dry_run=body.dry_run,
            project_id=project_id,
            on_step=on_step,
            on_proc=lambda p: setattr(state, "active_proc", p),
            is_aborted=lambda: state.abort_requested,
        )
        persist_pipeline_report(cfg, report)

        state.attempts = [
            {
                "attempt":        a.attempt,
                "branch":         a.branch,
                "build_passed":   a.build_passed,
                "eval_pass_rate": a.eval_pass_rate,
                "pr_url":         a.pr_url,
                "error":          a.error,
                "explanation":    a.explanation,
            }
            for a in report.attempts
        ]
        state.status = report.final_status
        if report.issue_url:
            state.issue_url = report.issue_url
        state.report = _build_report(state, report.final_status)

        if report.final_status in ("labeled", "merged"):
            for md in cfg.specs_dir.rglob("*.md"):
                doc = parse_safe(md)
                if doc and doc.frontmatter.get("id") == body.spec_id:
                    try:
                        patch_status(md, "implemented")
                    except Exception:
                        pass
                    break

    except Exception as exc:
        on_step(f"✗ Fehler: {exc}")
        state.status = "failed"
        state.attempts = [{
            "attempt": 1, "branch": "", "build_passed": None,
            "eval_pass_rate": None, "pr_url": None,
            "error": str(exc), "explanation": "",
        }]
        state.report = {
            "pass_rate": 0.0, "pr_url": None, "issue_url": None,
            "failed_scenarios": [], "reason": str(exc), "explanation": None,
        }
    finally:
        state.active_proc = None
        state.current_step = ""
        _active.pop(body.spec_id, None)


# ─── Gate helpers ────────────────────────────────────────────────────────────

def _load_gate_phase(spec_id: str, cfg: Any) -> str | None:
    import json as _json
    p = cfg.root / ".sdd" / "pipeline" / f"{spec_id}-gate.json"
    if p.exists():
        try:
            return _json.loads(p.read_text(encoding="utf-8")).get("pipeline_phase")
        except Exception:
            pass
    return None


def _log_gate_override(
    spec_id: str, reason: str, blocked_phase: str | None, cfg: Any
) -> None:
    import json as _json
    p = cfg.root / ".sdd" / "pipeline" / f"{spec_id}-gate.json"
    try:
        data = _json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except Exception:
        data = {}
    data["override"] = {
        "triggered_at": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "reason": reason,
        "blocked_phase": blocked_phase or "unknown",
    }
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(_json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# ─── Schema ──────────────────────────────────────────────────────────────────

class OrchestrateRequest(BaseModel):
    spec_id:         str
    project_id:      str = ""
    dry_run:         bool = False
    no_pr:           bool = False
    base_url:        str = ""
    force:           bool = False
    override_reason: str | None = None


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.post("/orchestrate", status_code=202, summary="Pipeline starten (SPEC-0007)")
def start_orchestrate(
    body: OrchestrateRequest,
    background_tasks: BackgroundTasks,
) -> dict[str, str]:
    _cleanup()

    from sdd_cli.llm import claude_available

    if not claude_available():
        raise HTTPException(
            status_code=503,
            detail="claude CLI nicht gefunden. Installiere Claude Code CLI und logge dich ein.",
        )

    cfg = get_config()
    from sdd_cli.frontmatter import parse_safe

    spec_doc = None
    for md in cfg.specs_dir.rglob("*.md"):
        doc = parse_safe(md)
        if doc and doc.frontmatter.get("id") == body.spec_id:
            spec_doc = doc
            break

    if spec_doc is None:
        raise HTTPException(status_code=404, detail=f"Spec nicht gefunden: {body.spec_id}")

    spec_status = spec_doc.frontmatter.get("status")
    if spec_status != "approved":
        raise HTTPException(
            status_code=422,
            detail=f"Spec muss status=approved haben (aktuell: {spec_status!r})",
        )

    # Gate check: pipeline_phase must be execute-unlocked (INV-07 CON-0021)
    gate_phase = _load_gate_phase(body.spec_id, cfg)
    if gate_phase != "execute-unlocked":
        if body.force:
            if not body.override_reason:
                raise HTTPException(
                    status_code=422,
                    detail="override_reason ist erforderlich bei force=true",
                )
            _log_gate_override(body.spec_id, body.override_reason, gate_phase, cfg)
        else:
            raise HTTPException(
                status_code=409,
                detail=f"Execution Gate nicht bestanden: pipeline_phase={gate_phase!r}.",
            )

    if body.spec_id in _active:
        existing = _active[body.spec_id]
        raise HTTPException(status_code=409, detail=f"Lauf {existing} läuft bereits")

    max_attempts = cfg.raw.get("orchestrator", {}).get("max_retries", 3)
    run_id = f"{body.spec_id}-{int(time.time() * 1000)}"
    _runs[run_id] = RunState(run_id=run_id, spec_id=body.spec_id, max_attempts=max_attempts)
    _active[body.spec_id] = run_id

    background_tasks.add_task(_run_pipeline_bg, run_id, body)
    return {"run_id": run_id}


@router.get("/pipeline/active", summary="Aktiven Lauf für eine Spec (SPEC-0007)")
def get_active_run(spec_id: str = Query(...)) -> dict[str, Any]:
    run_id = _active.get(spec_id)
    if not run_id or run_id not in _runs:
        raise HTTPException(status_code=404, detail=f"Kein aktiver Lauf für {spec_id}")
    return _to_dict(_runs[run_id])


@router.post("/pipeline/{run_id}/abort", summary="Pipeline-Run abbrechen (SPEC-0007)")
def abort_pipeline_run(run_id: str) -> dict[str, Any]:
    state = _runs.get(run_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"Lauf nicht gefunden: {run_id}")
    if state.status != "running":
        raise HTTPException(
            status_code=409,
            detail=f"Lauf ist nicht aktiv (status={state.status!r})",
        )
    state.abort_requested = True
    proc = state.active_proc
    if proc is not None:
        try:
            proc.terminate()
        except Exception:
            pass
    return {"aborted": True, "run_id": run_id}


@router.get("/pipeline/{run_id}/log", summary="Live-Log SSE stream (SPEC-0007)")
async def stream_pipeline_log(run_id: str) -> StreamingResponse:
    if run_id not in _runs:
        raise HTTPException(status_code=404, detail=f"Lauf nicht gefunden: {run_id}")

    async def _generate():
        offset = 0
        deadline = time.monotonic() + _TTL
        while time.monotonic() < deadline:
            state = _runs.get(run_id)
            if not state:
                yield "event: done\ndata: \n\n"
                return
            new_lines = state.log[offset:]
            for line in new_lines:
                safe = line.replace("\n", " ")
                yield f"data: {safe}\n\n"
            offset += len(new_lines)
            if state.status != "running":
                # Small delay so the final _step() writes flush
                await asyncio.sleep(0.3)
                final = _runs.get(run_id)
                if final:
                    for line in final.log[offset:]:
                        yield f"data: {line.replace(chr(10), ' ')}\n\n"
                yield "event: done\ndata: \n\n"
                return
            await asyncio.sleep(0.5)
        yield "event: done\ndata: \n\n"

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/pipeline/{run_id}", summary="Pipeline-Status (SPEC-0007)")
def get_pipeline_run(run_id: str) -> dict[str, Any]:
    _cleanup()
    if run_id not in _runs:
        raise HTTPException(status_code=404, detail=f"Lauf nicht gefunden: {run_id}")
    return _to_dict(_runs[run_id])
