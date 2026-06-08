"""Claude AI endpoints for spec generation and improvement."""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

log = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parents[1]))
import usage_store
from sdd_context import get_config

router = APIRouter(prefix="/ai", tags=["ai"])

SDD_SYSTEM_PROMPT = """\
You are an expert in Spec-Driven Development (SDD). SDD organises software requirements into three
artefacts that live as Markdown files with YAML frontmatter:

1. **Spec** – A single, self-contained requirement. Frontmatter fields: id (SPEC-XXXX), title,
   status (draft|active|deprecated), priority (low|medium|high|critical), owner, tags,
   depends_on, created, updated. The Markdown body explains the requirement in plain language.

2. **Contract** – A machine-verifiable interface agreement attached to a Spec. Frontmatter: id
   (CON-XXXX), title, spec (parent SPEC id), status, format (openapi|jsonschema|asyncapi|
   graphql|grpc|custom), artifact (path to schema file), version. Body describes the contract.

3. **Test** – An automated test that validates a Contract. Frontmatter: id (TST-XXXX), title,
   spec (parent SPEC id), contract (parent CON id), status, level (unit|integration|contract|
   acceptance|performance|property), framework, file, version. Body is optional documentation.

Rules:
- Every Contract must reference exactly one Spec.
- Every Test must reference exactly one Contract and its parent Spec.
- A Spec without a Contract cannot be validated.
- IDs are uppercase with zero-padded four-digit numbers: SPEC-0001, CON-0001, TST-0001.

When generating content, produce clean, concise Markdown. When suggesting structure, be concrete
about which Contracts and Tests are needed. Respond in the same language the user writes in.
"""

# Lazy module-level provider — initialized once on first request (§4.6 provider lifecycle)
_provider = None


def _get_provider():
    global _provider
    if _provider is None:
        from sdd_cli.llm import get_completion_provider
        _provider = get_completion_provider(get_config(), "ai_routes")
    return _provider


def _call(operation: str, user_message: str) -> tuple[str, dict[str, Any]]:
    """Call LLM provider with cached system prompt. Returns (text, usage_entry)."""
    provider = _get_provider()
    log.info("AI-Call gestartet: operation=%s provider=%s", operation, type(provider).__name__)
    try:
        result = provider.complete(
            user_message,
            max_tokens=2048,
            system_prompt=SDD_SYSTEM_PROMPT,
        )
    except RuntimeError as exc:
        log.error("AI-Call Fehler (%s): %s", operation, exc)
        raise HTTPException(status_code=503, detail=str(exc))
    log.info("AI-Call abgeschlossen: operation=%s tokens_out=%s",
             operation, result.usage.output_tokens if result.usage else "?")

    text = result.text
    entry: dict[str, Any] = {}
    if result.usage:
        entry = usage_store.record_usage(
            operation=operation,
            input_tokens=result.usage.input_tokens,
            output_tokens=result.usage.output_tokens,
            cache_creation_tokens=result.usage.cache_creation_tokens,
            cache_read_tokens=result.usage.cache_read_tokens,
            model=result.usage.model,
        )
    return text, entry


# Request / Response models

class GenerateSpecRequest(BaseModel):
    title: str
    description: str = ""
    context: str = ""


class ImproveSpecRequest(BaseModel):
    spec_id: str
    current_content: str
    instructions: str


class SuggestContractsRequest(BaseModel):
    spec_id: str
    spec_content: str


class AiResponse(BaseModel):
    result: str
    usage: dict[str, Any]


# Endpoints

@router.post("/generate-spec", response_model=AiResponse)
def generate_spec(body: GenerateSpecRequest) -> AiResponse:
    prompt = f"Write the Markdown body for a Spec with the title: **{body.title}**."
    if body.description:
        prompt += f"\n\nDescription: {body.description}"
    if body.context:
        prompt += f"\n\nAdditional context: {body.context}"
    prompt += (
        "\n\nWrite only the Markdown body (no frontmatter, no code fences). "
        "Be concise but complete. Include: purpose, acceptance criteria (as a checklist), "
        "and any important constraints or non-goals."
    )
    text, entry = _call("generate-spec", prompt)
    return AiResponse(result=text, usage=entry)


@router.post("/improve-spec", response_model=AiResponse)
def improve_spec(body: ImproveSpecRequest) -> AiResponse:
    prompt = (
        f"Improve the following Spec ({body.spec_id}) according to these instructions:\n\n"
        f"**Instructions:** {body.instructions}\n\n"
        f"**Current content:**\n\n{body.current_content}\n\n"
        "Return only the improved Markdown body (no frontmatter, no code fences)."
    )
    text, entry = _call("improve-spec", prompt)
    return AiResponse(result=text, usage=entry)


@router.post("/suggest-contracts", response_model=AiResponse)
def suggest_contracts(body: SuggestContractsRequest) -> AiResponse:
    prompt = (
        f"Given the following Spec ({body.spec_id}), suggest which Contracts should be "
        f"created to make it verifiable.\n\n"
        f"**Spec content:**\n\n{body.spec_content}\n\n"
        "For each suggested Contract, state:\n"
        "- A short title\n"
        "- The recommended format (openapi / jsonschema / asyncapi / graphql / grpc / custom)\n"
        "- What the artifact should describe (1-2 sentences)\n\n"
        "Format your response as a Markdown list."
    )
    text, entry = _call("suggest-contracts", prompt)
    return AiResponse(result=text, usage=entry)


@router.get("/usage")
def get_usage() -> dict[str, Any]:
    return {
        "summary": usage_store.get_summary(),
        "records": usage_store.get_all(),
    }
