"""AgentFlowFacade – Agentic Flow Endpunkte (SPEC-0032, CON-0114).

Facade-Pattern: POST /api/agent/flow/start, /reply, GET /{session_id}.
Delegiert an SPEC-0016 (review) und SPEC-0007 (implement) ohne eigenen Job-Store.
"""
from __future__ import annotations

import sys
import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parents[1]))
from flow_session import (
    VALID_FLOW_TYPES,
    FlowSession,
    get_flow_session_store,
    get_hotfix_steps,
    get_new_spec_steps,
)

router = APIRouter(prefix="/agent/flow", tags=["agent-flow"])


# ─── Pydantic models ──────────────────────────────────────────────────────────

class FlowStartRequest(BaseModel):
    flow_type: str
    spec_id: str | None = None


class FlowReplyRequest(BaseModel):
    answer: str


# ─── Backend delegates (module-level so tests can patch them) ─────────────────

def _start_review_job(spec_id: str) -> str:
    """Creates a SPEC-0016 AnalysisJob. Returns job_id (INV-04)."""
    from job_store import get_job_store
    return get_job_store().create(spec_id).job_id


def _start_implement_job(spec_id: str) -> str:
    """Creates a SPEC-0007 PipelineRun. Returns run_id (INV-04)."""
    from routes.orchestrate import RunState, _active, _runs
    run_id = f"{spec_id}-flow-{int(time.time() * 1000)}"
    _runs[run_id] = RunState(run_id=run_id, spec_id=spec_id)
    _active[spec_id] = run_id
    return run_id


def _create_hotfix_record(answers: dict[str, str]) -> str:
    return str(uuid.uuid4())


# ─── State machine ────────────────────────────────────────────────────────────

def _advance(session: FlowSession, answer: str) -> dict[str, Any]:
    """Advance state machine one step. Returns FlowReplyResponse shape."""
    ft = session.flow_type

    if ft == "new-spec":
        return _advance_multistep(session, answer, get_new_spec_steps())

    if ft == "hotfix":
        result = _advance_multistep(session, answer, get_hotfix_steps())
        if result.get("done"):
            job_id = _create_hotfix_record(session.answers)
            session.job_id = job_id
            result["job_id"] = job_id
        return result

    if ft == "review":
        return _advance_delegated(session, answer, _start_review_job)

    if ft == "implement":
        return _advance_delegated(session, answer, _start_implement_job)

    session.state = "done"
    return {"done": True, "state": "done"}


def _advance_multistep(
    session: FlowSession, answer: str, steps: list[str]
) -> dict[str, Any]:
    session.answers[str(session.step_index)] = answer
    session.step_index += 1
    if session.step_index < len(steps):
        session.state = "awaiting_input"
        session.current_prompt = steps[session.step_index]
        return {"done": False, "prompt": session.current_prompt, "state": session.state}
    session.state = "done"
    session.current_prompt = None
    return {"done": True, "state": "done"}


def _advance_delegated(
    session: FlowSession,
    answer: str,
    start_job_fn: Any,
) -> dict[str, Any]:
    """Handle review/implement flows: optional spec_id input → decision → delegation."""
    if session.state == "awaiting_input":
        session.spec_id = answer.strip()
        session.answers[str(session.step_index)] = answer
        session.step_index += 1
        prompt = f"Starten für {session.spec_id}? (ja/nein)"
        session.current_prompt = prompt
        session.state = "awaiting_decision"
        return {
            "done": False,
            "prompt": prompt,
            "state": "awaiting_decision",
            "awaiting_decision": True,
        }

    # state == awaiting_decision
    if answer.lower() == "ja":
        if session.job_id:
            # Mid-job decision point (FR-05): resume running job
            session.state = "running"
            session.current_prompt = None
            return {"done": False, "state": "running", "job_id": session.job_id}
        # Initial confirmation: start the delegated job
        job_id = start_job_fn(session.spec_id or "")
        session.job_id = job_id
        session.state = "done"
        session.current_prompt = None
        return {"done": True, "state": "done", "job_id": job_id}

    # answer == "nein"
    if session.job_id:
        # Mid-job decision (FR-05): discard step, continue job
        session.state = "running"
        session.current_prompt = None
        return {"done": False, "state": "running", "job_id": session.job_id}
    # Initial cancel: done without job
    session.state = "done"
    session.current_prompt = None
    return {"done": True, "state": "done"}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _to_state_dict(s: FlowSession) -> dict[str, Any]:
    d: dict[str, Any] = {
        "session_id": s.session_id,
        "flow_type": s.flow_type,
        "state": s.state,
        "step_index": s.step_index,
        "answers": s.answers,
    }
    if s.current_prompt is not None:
        d["current_prompt"] = s.current_prompt
    if s.job_id is not None:
        d["job_id"] = s.job_id
    if s.spec_id is not None:
        d["spec_id"] = s.spec_id
    return d


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/start", summary="Startet einen neuen Agentic Flow (FR-01)")
def start_flow(body: FlowStartRequest) -> dict[str, Any]:
    if body.flow_type not in VALID_FLOW_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Ungültiger flow_type: {body.flow_type!r}",
        )
    if body.flow_type in ("review", "implement") and not body.spec_id:
        raise HTTPException(
            status_code=422,
            detail=f"spec_id ist Pflichtfeld bei flow_type={body.flow_type!r}",
        )
    session = get_flow_session_store().create(body.flow_type, body.spec_id)
    return {
        "session_id": session.session_id,
        "prompt": session.current_prompt,
        "state": session.state,
    }


@router.post("/{session_id}/reply", summary="Sendet eine Nutzer-Antwort (FR-02)")
def reply_to_flow(session_id: str, body: FlowReplyRequest) -> dict[str, Any]:
    store = get_flow_session_store()
    session = store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session nicht gefunden oder abgelaufen")

    if session.state in ("done", "failed"):
        raise HTTPException(
            status_code=409, detail=f"Session ist bereits {session.state!r} (INV-01)"
        )
    if session.state == "running":
        raise HTTPException(status_code=409, detail="Session läuft – kein Input erwartet")

    if session.state == "awaiting_decision" and body.answer.lower() not in ("ja", "nein"):
        raise HTTPException(
            status_code=422,
            detail="Nur 'ja' oder 'nein' bei awaiting_decision erlaubt (INV-02)",
        )

    result = _advance(session, body.answer)
    store.save(session)
    return result


@router.get("/{session_id}", summary="Gibt den aktuellen Flow-State zurück (FR-06)")
def get_flow_state(session_id: str) -> dict[str, Any]:
    session = get_flow_session_store().get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session nicht gefunden oder abgelaufen")
    return _to_state_dict(session)
