"""KI-gestützte Dokument-Analyse via konfigurierbarem LLM-Provider.

SPEC-0005/SPEC-0008: Provider-Auflösung via llm.analyzer in config.yaml.
Default: ClaudeCliCompletionProvider (claude --print --output-format json).
"""
from __future__ import annotations

import json
import re
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from fastapi import HTTPException

if TYPE_CHECKING:
    from sdd_cli.config import SddConfig
    from sdd_cli.llm.base import CompletionProvider

SESSION_TTL_SECONDS = 3600
MAX_QUESTIONS = 5
MAX_ANSWERED = 20       # älteste Antworten werden verdrängt (SPEC-0005 §6 NFR)

CLAUDE_INSTALL_URL = "https://claude.ai/code"

FALLBACK_SPEC_PROMPT = """\
You are an expert in Spec-Driven Development (SDD). Analyze the following Spec document
and identify gaps, missing details, or ambiguities the author should clarify.

Focus on: missing success criteria, edge cases, non-functional requirements,
underspecified user stories, missing scope boundaries.

{{answered_context}}

## Document (type: spec)

{{document_content}}

Return ONLY a JSON object:
{"questions":[{"id":"<slug>","section":"<heading>","text":"<question>","severity":"error|warning|suggestion"}],"issues":[{"section":"<h>","text":"<issue>","severity":"error|warning"}],"suggestions":[{"text":"<tip>"}]}

Rules: max 5 questions, ask in document language, reference specific sections."""

FALLBACK_CONTRACT_PROMPT = """\
You are an expert in Spec-Driven Development (SDD). Analyze the following Contract document
and identify gaps that would make it untestable or incomplete.

Focus on: missing guarantees, undefined error cases, vague invariants,
missing terms, untestable statements.

{{answered_context}}

## Document (type: contract)

{{document_content}}

Return ONLY a JSON object:
{"questions":[{"id":"<slug>","section":"<heading>","text":"<question>","severity":"error|warning|suggestion"}],"issues":[{"section":"<h>","text":"<issue>","severity":"error|warning"}],"suggestions":[{"text":"<tip>"}]}

Rules: max 5 questions, ask in document language, reference specific sections."""


# Session state

@dataclass
class AnsweredQuestion:
    id: str
    answer: str


@dataclass
class AnalysisSession:
    session_id: str
    doc_id: str
    answered: list[AnsweredQuestion] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_used: float = field(default_factory=time.time)

    def touch(self) -> None:
        self.last_used = time.time()

    def is_expired(self) -> bool:
        return (time.time() - self.last_used) > SESSION_TTL_SECONDS


_sessions: dict[str, AnalysisSession] = {}


def _get_or_create_session(session_id: str | None, doc_id: str) -> AnalysisSession:
    _purge_expired()
    if session_id and session_id in _sessions:
        session = _sessions[session_id]
        session.touch()
        return session
    new_id = session_id or str(uuid.uuid4())
    session = AnalysisSession(session_id=new_id, doc_id=doc_id)
    _sessions[new_id] = session
    return session


def _purge_expired() -> None:
    expired = [sid for sid, s in _sessions.items() if s.is_expired()]
    for sid in expired:
        del _sessions[sid]


# Prompt building

def _load_template(templates_dir: Path, doc_type: str) -> str:
    path = templates_dir / "analysis" / f"{doc_type}-prompt.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return FALLBACK_SPEC_PROMPT if doc_type == "spec" else FALLBACK_CONTRACT_PROMPT


def _build_answered_context(answered: list[AnsweredQuestion]) -> str:
    if not answered:
        return ""
    lines = ["## Already Answered Questions (do NOT repeat these)\n"]
    for a in answered:
        lines.append(f"- [{a.id}] Answer given: {a.answer}")
    return "\n".join(lines) + "\n"


def _build_prompt(template: str, content: str, answered: list[AnsweredQuestion]) -> str:
    answered_ctx = _build_answered_context(answered)
    return (
        template
        .replace("{{document_content}}", content)
        .replace("{{answered_context}}", answered_ctx)
    )


# Provider call

def _call_claude(prompt: str, provider: "CompletionProvider") -> tuple[dict[str, Any], dict[str, Any]]:
    """Ruft den LLM-Provider auf und gibt (result_dict, usage_dict) zurück."""
    try:
        completion = provider.complete(prompt)
    except RuntimeError as exc:
        msg = str(exc)
        if "nicht gefunden" in msg or "not found" in msg.lower():
            raise HTTPException(status_code=503, detail={
                "error": "provider_not_found",
                "message": msg,
                "install_url": CLAUDE_INSTALL_URL,
            })
        if "Timeout" in msg or "timeout" in msg.lower():
            raise HTTPException(status_code=504, detail={
                "error": "provider_timeout",
                "message": msg,
            })
        raise HTTPException(status_code=502, detail={
            "error": "provider_error",
            "message": msg,
        })

    inner_text = completion.text
    usage: dict[str, Any]
    if completion.usage:
        usage = {
            "provider": "anthropic",
            "model": completion.usage.model,
            "input_tokens": completion.usage.input_tokens,
            "output_tokens": completion.usage.output_tokens,
        }
    else:
        usage = {"provider": "claude-code-cli"}

    # Strip optional markdown code fence (```json ... ```)
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", inner_text, re.DOTALL)
    if fence:
        inner_text = fence.group(1)

    start, end = inner_text.find("{"), inner_text.rfind("}") + 1
    if start == -1 or end == 0:
        raise HTTPException(status_code=502, detail={
            "error": "provider_parse_error",
            "message": "LLM hat kein valides JSON zurückgegeben.",
            "raw": inner_text[:500],
        })

    try:
        parsed = json.loads(inner_text[start:end])
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=502, detail={
            "error": "provider_parse_error",
            "message": "LLM hat kein valides JSON zurückgegeben.",
            "raw": inner_text[:500],
        })

    return parsed, usage


# Public API

@dataclass
class Question:
    id: str
    section: str
    text: str
    severity: str  # "error" | "warning" | "suggestion"


@dataclass
class Issue:
    section: str
    text: str
    severity: str


@dataclass
class Suggestion:
    text: str


@dataclass
class AnalysisResult:
    session_id: str
    questions: list[Question]
    issues: list[Issue]
    suggestions: list[Suggestion]
    usage: dict[str, Any]


def analyze(
    doc_id: str,
    content: str,
    doc_type: str,
    templates_dir: Path,
    session_id: str | None = None,
    answered_questions: list[dict] | None = None,
    config: "SddConfig | None" = None,
) -> AnalysisResult:
    """Analysiert ein Dokument via LLM-Provider und gibt Nachfragen zurück."""
    if doc_type not in ("spec", "contract"):
        raise HTTPException(status_code=422, detail="doc_type muss 'spec' oder 'contract' sein.")
    if not content.strip():
        raise HTTPException(status_code=422, detail="content darf nicht leer sein.")

    session = _get_or_create_session(session_id, doc_id)

    if answered_questions:
        answered_ids = {a.id for a in session.answered}
        for aq in answered_questions:
            if aq.get("id") and aq["id"] not in answered_ids:
                session.answered.append(AnsweredQuestion(
                    id=aq["id"], answer=aq.get("answer", "")
                ))
        if len(session.answered) > MAX_ANSWERED:
            session.answered = session.answered[-MAX_ANSWERED:]

    template = _load_template(templates_dir, doc_type)
    prompt = _build_prompt(template, content, session.answered)

    if config is not None:
        from sdd_cli.llm import get_completion_provider
        provider = get_completion_provider(config, "analyzer")
    else:
        from sdd_cli.llm.providers.claude_cli import ClaudeCliCompletionProvider
        provider = ClaudeCliCompletionProvider()

    raw, usage = _call_claude(prompt, provider)

    answered_ids = {a.id for a in session.answered}
    raw_questions = raw.get("questions") or []
    questions = [
        Question(
            id=q.get("id", str(uuid.uuid4())[:8]),
            section=q.get("section", ""),
            text=q.get("text", ""),
            severity=q.get("severity", "warning"),
        )
        for q in raw_questions
        if q.get("id") not in answered_ids
    ][:MAX_QUESTIONS]

    issues = [
        Issue(section=i.get("section", ""), text=i.get("text", ""), severity=i.get("severity", "warning"))
        for i in (raw.get("issues") or [])
    ]
    suggestions = [
        Suggestion(text=s.get("text", ""))
        for s in (raw.get("suggestions") or [])
    ]

    return AnalysisResult(
        session_id=session.session_id,
        questions=questions,
        issues=issues,
        suggestions=suggestions,
        usage=usage,
    )
