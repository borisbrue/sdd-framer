"""Execute-Flow: POST /api/orchestrate + GET /api/pipeline/{run_id} + GET /api/pipeline/active.

SPEC-0007 §3 — Pipeline-State-Store (In-Memory, TTL 1h). Seit SPEC-0062 ein Adapter: dahinter läuft
`sdd pipeline run SPEC --auto` als eigener Prozess, die `run_id` ist die Run-ID der Pipeline
(CON-0021 0.4.0, CON-0216 INV-04/05).
"""
from __future__ import annotations

import asyncio
import datetime
import os
import subprocess
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


def _gate_events(cfg: Any, run_id: str) -> dict[str, dict]:
    """Letztes `gate`-Ereignis je Schritt aus dem Run-Protokoll (öffentliche Facade `store`)."""
    from sdd_cli.pipeline.store import RunNotFound, RunStore

    try:
        store = RunStore.open(cfg.root, run_id)
    except RunNotFound:
        return {}
    schritte: dict[str, dict] = {}
    for ereignis in store.read_jsonl("events.jsonl"):
        detail = ereignis.get("detail") or {}
        if ereignis.get("type") == "gate" and detail.get("gate"):
            schritte[detail["gate"]] = detail
    return schritte


def _build_report(state: RunState, gates: dict[str, dict], reason: str | None) -> dict:
    """PipelineReport (CON-0021) aus den Ereignissen `holdout` und `finalize` (CON-0216 INV-05)."""
    holdout = gates.get("holdout", {}).get("result") or {}
    return {
        "pass_rate":        holdout.get("rate"),
        "pr_url":           gates.get("finalize", {}).get("pr") or None,
        "issue_url":        state.issue_url,
        "failed_scenarios": [s.get("id", "") for s in holdout.get("scenarios", [])
                             if not s.get("passed")],
        "reason":           reason,
        "explanation":      None,
    }


def _final_status(exit_code: int, body: OrchestrateRequest, gates: dict[str, dict],
                  aborted: bool) -> str:
    if aborted:
        return "aborted"
    if exit_code == 3:
        return "paused"
    if exit_code != 0:
        return "failed"
    if body.dry_run:
        return "dry_run"
    return "merged" if gates.get("automerge", {}).get("result") == "merged" else "labeled"


def pipeline_argv(run_id: str, body: OrchestrateRequest) -> list[str]:
    """`sdd pipeline run SPEC --auto` mit den Optionen der Anfrage (CON-0216 INV-05)."""
    argv = ["pipeline", "run", body.spec_id, "--auto", "--run-id", run_id]
    if body.dry_run:
        argv.append("--dry-run")
    if body.no_pr:
        argv += ["--steps", "holdout"]
    if body.base_url:
        argv += ["--base-url", body.base_url]
    return argv


# Patched in tests: Prozessstart des Adapters.
_popen = subprocess.Popen


# ─── Background worker ───────────────────────────────────────────────────────

def _run_pipeline_bg(run_id: str, body: OrchestrateRequest) -> None:
    """Adapter (SPEC-0062 FR-03): startet `sdd pipeline run --auto` als eigenen Prozess."""
    import sdd_cli

    state = _runs.get(run_id)
    if not state:
        return

    def on_step(msg: str) -> None:
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        state.log.append(f"[{ts}] {msg}")
        state.current_step = msg

    cfg = get_config()
    argv = pipeline_argv(run_id, body)
    on_step("▶ sdd " + " ".join(argv))
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(
        [str(Path(sdd_cli.__file__).resolve().parents[1]),
         *filter(None, [os.environ.get("PYTHONPATH")])])}
    reason: str | None = None
    exit_code = 1
    try:
        proc = _popen([sys.executable, "-c", "from sdd_cli.main import cli; cli()", *argv],
                      cwd=cfg.root, env=env, stdout=subprocess.PIPE,
                      stderr=subprocess.STDOUT, text=True)
        state.active_proc = proc
        for zeile in proc.stdout or []:
            if zeile.strip():
                on_step(zeile.rstrip())
                reason = zeile.strip()
        exit_code = proc.wait()
    except OSError as exc:
        on_step(f"✗ Fehler: {exc}")
        reason = str(exc)
    finally:
        state.active_proc = None
        _active.pop(body.spec_id, None)

    gates = _gate_events(cfg, run_id)
    state.status = _final_status(exit_code, body, gates, state.abort_requested)
    if state.status == "paused":
        from sdd_cli.pipeline.store import RunNotFound, RunStore

        try:
            wartet_auf_arbeit = RunStore.open(cfg.root, run_id).read_work() is not None
        except RunNotFound:
            wartet_auf_arbeit = False
        befehl = "done" if wartet_auf_arbeit else "decide"
        on_step(f"⏸ Wartet auf Claude Code: sdd pipeline {befehl} {run_id} "
                f"(oder /sdd-supervise {body.spec_id})")
    else:
        state.current_step = ""
    report = _build_report(state, gates, None if exit_code == 0 else reason)
    state.attempts = [{"attempt": 1, "branch": "", "build_passed": None,
                       "eval_pass_rate": report["pass_rate"], "pr_url": report["pr_url"],
                       "error": report["reason"], "explanation": ""}]
    state.report = report


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

    from sdd_cli.pipeline.store import new_run_id

    max_attempts = cfg.raw.get("orchestrator", {}).get("max_retries", 3)
    run_id = new_run_id(body.spec_id)
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
    if state.status not in ("running", "paused"):
        raise HTTPException(
            status_code=409,
            detail=f"Lauf ist nicht aktiv (status={state.status!r})",
        )
    state.abort_requested = True
    if state.status == "paused":
        state.status = "aborted"
        state.current_step = ""
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
