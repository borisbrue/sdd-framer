"""Async Analyse-Endpunkte (SPEC-0016, CON-0049/0052/0053)."""
from __future__ import annotations

import asyncio
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, field_validator

sys.path.insert(0, str(Path(__file__).parents[1]))
from analysis_repository import AnalysisRepository, PersistedAnalysis
from analyzer import analyze
from job_store import MAX_CONCURRENT_JOBS_PER_DOC, JobStore, get_job_store
from sdd_context import get_config

FIX_HINT_PROMPT = """\
You are an expert in Spec-Driven Development (SDD).
A reviewer found the following question/issue in a document and you must suggest a concrete fix.

Question/Issue: {question_text}
Section: {section}

## Document

{content}

Return ONLY a JSON object with a ready-to-use markdown snippet the author can paste into the document:
{{"suggested_fix": "<markdown text>"}}

Rules:
- Write in the same language as the document.
- Provide concrete, copy-pasteable markdown (headings, tables, bullet lists as appropriate).
- Do NOT explain — just produce the fix text.
"""

router = APIRouter(prefix="/docs", tags=["analyze-async"])

MAX_CONTENT_CHARS = 50_000


# ─── Request / Response models ────────────────────────────────────────────────

class StartRequest(BaseModel):
    content: str
    doc_type: str
    dismissed_ids: list[str] = []
    session_id: str | None = None

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("content darf nicht leer sein.")
        return v[:MAX_CONTENT_CHARS]

    @field_validator("doc_type")
    @classmethod
    def valid_doc_type(cls, v: str) -> str:
        if v not in ("spec", "contract"):
            raise ValueError("doc_type muss 'spec' oder 'contract' sein.")
        return v


class StartResponse(BaseModel):
    job_id: str
    status: str


class StatusResponse(BaseModel):
    status: str
    result_id: str | None = None
    error: str | None = None


class DismissRequest(BaseModel):
    item_id: str
    dismissed: bool

    @field_validator("item_id")
    @classmethod
    def item_id_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("item_id darf nicht leer sein.")
        return v


class DismissResponse(BaseModel):
    dismissed_ids: list[str]


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_repo() -> AnalysisRepository:
    cfg = get_config()
    base = cfg.root / ".sdd" / "analyses"
    return AnalysisRepository(base)


# ─── Background task ──────────────────────────────────────────────────────────

async def _run_analysis(
    job_id: str,
    doc_id: str,
    content: str,
    doc_type: str,
    dismissed_ids: list[str],
    session_id: str | None,
    store: JobStore,
    repo: AnalysisRepository,
) -> None:
    store.update_running(job_id)
    try:
        cfg = get_config()
        answered: list[dict[str, Any]] = [
            {"id": did, "answer": "[dismissed]"} for did in dismissed_ids
        ]
        result = await asyncio.to_thread(
            analyze,
            doc_id=doc_id,
            content=content,
            doc_type=doc_type,
            templates_dir=cfg.templates_dir,
            session_id=session_id,
            answered_questions=answered,
            config=cfg,
        )
        result_id = AnalysisRepository.make_result_id(job_id)
        analysis = PersistedAnalysis(
            result_id=result_id,
            doc_id=doc_id,
            timestamp=result_id.split("_")[0],
            session_id=result.session_id,
            dismissed_ids=list(dismissed_ids),
            questions=[asdict(q) for q in result.questions],
            issues=[asdict(i) for i in result.issues],
            suggestions=[asdict(s) for s in result.suggestions],
            usage=result.usage,
        )
        repo.save(analysis)
        store.update_complete(job_id, result_id)
    except Exception as exc:
        store.update_failed(job_id, str(exc))


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/{doc_id}/analyze/start", response_model=StartResponse, status_code=202)
async def start_analysis(
    doc_id: str,
    body: StartRequest,
    background_tasks: BackgroundTasks,
) -> StartResponse:
    store = get_job_store()
    if store.active_count(doc_id) >= MAX_CONCURRENT_JOBS_PER_DOC:
        raise HTTPException(status_code=429, detail="Zu viele gleichzeitige Analyse-Jobs für dieses Dokument.")

    store.cleanup_expired()
    store.apply_timeouts()

    repo = _get_repo()
    job = store.create(doc_id)

    background_tasks.add_task(
        _run_analysis,
        job_id=job.job_id,
        doc_id=doc_id,
        content=body.content,
        doc_type=body.doc_type,
        dismissed_ids=body.dismissed_ids,
        session_id=body.session_id,
        store=store,
        repo=repo,
    )
    return StartResponse(job_id=job.job_id, status=job.status)


@router.get("/{doc_id}/analyze/status/{job_id}", response_model=StatusResponse)
def get_status(doc_id: str, job_id: str) -> StatusResponse:
    store = get_job_store()
    store.apply_timeouts()
    job = store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job nicht gefunden.")
    return StatusResponse(status=job.status, result_id=job.result_id, error=job.error)


@router.get("/{doc_id}/analyses")
def list_analyses(doc_id: str) -> list[dict]:
    repo = _get_repo()
    return repo.list(doc_id)


@router.get("/{doc_id}/analyses/{result_id}")
def get_analysis(doc_id: str, result_id: str) -> dict:
    repo = _get_repo()
    analysis = repo.get(doc_id, result_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analyse nicht gefunden.")
    return analysis.to_dict()


@router.patch("/{doc_id}/analyses/{result_id}/dismiss", response_model=DismissResponse)
def dismiss_item(doc_id: str, result_id: str, body: DismissRequest) -> DismissResponse:
    repo = _get_repo()
    updated = repo.update_dismiss(doc_id, result_id, body.item_id, body.dismissed)
    if updated is None:
        raise HTTPException(status_code=404, detail="Analyse nicht gefunden.")
    return DismissResponse(dismissed_ids=updated)


# ─── Fix-Hint ─────────────────────────────────────────────────────────────────

class FixHintRequest(BaseModel):
    content: str
    question_text: str
    section: str = ""

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("content darf nicht leer sein.")
        return v[:MAX_CONTENT_CHARS]

    @field_validator("question_text")
    @classmethod
    def question_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("question_text darf nicht leer sein.")
        return v


class FixHintResponse(BaseModel):
    suggested_fix: str


@router.post("/{doc_id}/analyze/fix-hint", response_model=FixHintResponse)
def request_fix_hint(doc_id: str, body: FixHintRequest) -> FixHintResponse:
    """Liefert einen konkreten Markdown-Änderungsvorschlag für eine einzelne Nachfrage."""
    import json
    import re

    cfg = get_config()
    from sdd_cli.llm import get_completion_provider
    provider = get_completion_provider(cfg, "analyzer")

    prompt = FIX_HINT_PROMPT.format(
        question_text=body.question_text,
        section=body.section or "—",
        content=body.content,
    )

    try:
        completion = provider.complete(prompt)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail={"error": "provider_error", "message": str(exc)}) from exc

    inner = completion.text
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", inner, re.DOTALL)
    if fence:
        inner = fence.group(1)
    start, end = inner.find("{"), inner.rfind("}") + 1
    if start == -1 or end == 0:
        raise HTTPException(status_code=502, detail="LLM hat kein valides JSON zurückgegeben.")
    try:
        parsed = json.loads(inner[start:end])
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="LLM hat kein valides JSON zurückgegeben.") from exc

    fix = parsed.get("suggested_fix", "")
    if not fix:
        raise HTTPException(status_code=502, detail="Kein Vorschlag vom LLM erhalten.")
    return FixHintResponse(suggested_fix=fix)
