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

Return ONLY a JSON object (keep each text field under 120 characters):
{"questions":[{"id":"<slug>","section":"<heading>","text":"<question>","severity":"error|warning|suggestion"}],"issues":[{"section":"<h>","text":"<issue>","severity":"error|warning"}],"suggestions":[{"text":"<tip>"}]}

Rules: max 5 questions, max 5 issues, max 3 suggestions. Ask in document language. Reference specific sections."""

FALLBACK_CONTRACT_PROMPT = """\
You are an expert in Spec-Driven Development (SDD). Analyze the following Contract document
and identify gaps that would make it untestable or incomplete.

Focus on: missing guarantees, undefined error cases, vague invariants,
missing terms, untestable statements.

{{answered_context}}

## Document (type: contract)

{{document_content}}

Return ONLY a JSON object (keep each text field under 120 characters):
{"questions":[{"id":"<slug>","section":"<heading>","text":"<question>","severity":"error|warning|suggestion"}],"issues":[{"section":"<h>","text":"<issue>","severity":"error|warning"}],"suggestions":[{"text":"<tip>"}]}

Rules: max 5 questions, max 5 issues, max 3 suggestions. Ask in document language. Reference specific sections."""


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

def _try_parse_json(text: str) -> "dict[str, Any] | None":
    """Versucht JSON zu parsen; repariert abgeschnittene Responses."""
    # 1. Normaler Parse bis zum letzten }
    end = text.rfind("}") + 1
    if end > 0:
        try:
            return json.loads(text[:end])
        except (json.JSONDecodeError, ValueError):
            pass

    # 2. Repair: fehlende schließende Klammern ergänzen
    depth_curly = depth_square = 0
    in_string = escaped = False
    last_complete = 0
    for i, ch in enumerate(text):
        if escaped:
            escaped = False
            continue
        if ch == "\\" and in_string:
            escaped = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth_curly += 1
        elif ch == "}":
            depth_curly -= 1
        elif ch == "[":
            depth_square += 1
        elif ch == "]":
            depth_square -= 1
        if depth_curly == 0 and depth_square == 0 and i > 0:
            last_complete = i + 1

    # Schließe abgeschnittene Arrays/Objekte
    repair = text[:last_complete] if last_complete else text
    repair += "]" * max(0, depth_square) + "}" * max(0, depth_curly)
    try:
        return json.loads(repair)
    except (json.JSONDecodeError, ValueError):
        return None


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

    start = inner_text.find("{")
    if start == -1:
        raise HTTPException(status_code=502, detail={
            "error": "provider_parse_error",
            "message": "LLM hat kein valides JSON zurückgegeben.",
            "raw": inner_text[:500],
        })

    candidate = inner_text[start:]
    parsed = _try_parse_json(candidate)
    if parsed is None:
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
    suggested_fix: str | None = None


@dataclass
class Suggestion:
    text: str
    suggested_fix: str | None = None


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
        Issue(
            section=i.get("section", ""),
            text=i.get("text", ""),
            severity=i.get("severity", "warning"),
            suggested_fix=i.get("suggested_fix") or None,
        )
        for i in (raw.get("issues") or [])
    ]
    suggestions = [
        Suggestion(
            text=s.get("text", ""),
            suggested_fix=s.get("suggested_fix") or None,
        )
        for s in (raw.get("suggestions") or [])
    ]

    return AnalysisResult(
        session_id=session.session_id,
        questions=questions,
        issues=issues,
        suggestions=suggestions,
        usage=usage,
    )
