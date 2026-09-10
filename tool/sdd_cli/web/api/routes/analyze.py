"""PUT /api/docs/{doc_id}/analyze – KI-gestützte Dokument-Analyse."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, field_validator

sys.path.insert(0, str(Path(__file__).parents[1]))
from analyzer import analyze
from sdd_context import get_config

router = APIRouter(prefix="/docs", tags=["analyze"])

MAX_CONTENT_CHARS = 50_000


# ─── Request / Response models ────────────────────────────────────────────────

class AnsweredQuestion(BaseModel):
    id: str
    answer: str = ""


class AnalyzeRequest(BaseModel):
    content: str
    doc_type: str            # "spec" | "contract"
    session_id: str | None = None
    answered_questions: list[AnsweredQuestion] = []

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


class QuestionOut(BaseModel):
    id: str
    section: str
    text: str
    severity: str


class IssueOut(BaseModel):
    section: str
    text: str
    severity: str
    suggested_fix: str | None = None


class SuggestionOut(BaseModel):
    text: str
    suggested_fix: str | None = None


class AnalyzeResponse(BaseModel):
    session_id: str
    questions: list[QuestionOut]
    issues: list[IssueOut]
    suggestions: list[SuggestionOut]
    usage: dict[str, Any]


# ─── Endpoint ─────────────────────────────────────────────────────────────────

@router.put("/{doc_id}/analyze", response_model=AnalyzeResponse)
def analyze_doc(doc_id: str, body: AnalyzeRequest) -> AnalyzeResponse:
    """Analysiert ein Spec- oder Contract-Dokument und gibt Nachfragen zurück."""
    cfg = get_config()

    result = analyze(
        doc_id=doc_id,
        content=body.content,
        doc_type=body.doc_type,
        templates_dir=cfg.templates_dir,
        session_id=body.session_id,
        answered_questions=[aq.model_dump() for aq in body.answered_questions],
        config=cfg,
    )

    return AnalyzeResponse(
        session_id=result.session_id,
        questions=[QuestionOut(id=q.id, section=q.section, text=q.text, severity=q.severity)
                   for q in result.questions],
        issues=[IssueOut(section=i.section, text=i.text, severity=i.severity, suggested_fix=i.suggested_fix)
                for i in result.issues],
        suggestions=[SuggestionOut(text=s.text, suggested_fix=s.suggested_fix) for s in result.suggestions],
        usage=result.usage,
    )
