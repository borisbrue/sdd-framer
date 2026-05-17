"""GitHub Copilot endpoints for spec generation and improvement.

Uses the GitHub Copilot Chat API (https://api.githubcopilot.com), which is
OpenAI-compatible. Requires a GITHUB_TOKEN with Copilot access in the environment.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parents[1]))
import usage_store  # noqa: E402

router = APIRouter(prefix="/copilot", tags=["copilot"])

COPILOT_BASE_URL = os.environ.get("GITHUB_COPILOT_URL", "https://api.githubcopilot.com")
MODEL = os.environ.get("GITHUB_COPILOT_MODEL", "gpt-4o")

# Same SDD methodology prompt as the Claude integration.
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


def _client():
    try:
        import openai as _openai
    except ImportError as exc:
        raise HTTPException(status_code=503, detail="openai SDK nicht installiert.") from exc
    key = os.environ.get("GITHUB_TOKEN")
    if not key:
        raise HTTPException(status_code=503, detail="GITHUB_TOKEN nicht konfiguriert.")
    return _openai.OpenAI(base_url=COPILOT_BASE_URL, api_key=key)


def _call(operation: str, user_message: str) -> tuple[str, dict[str, Any]]:
    client = _client()
    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=2048,
        messages=[
            {"role": "system", "content": SDD_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )
    usage = response.usage
    input_tok  = usage.prompt_tokens if usage else 0
    output_tok = usage.completion_tokens if usage else 0
    entry = usage_store.record_usage(
        operation=operation,
        input_tokens=input_tok,
        output_tokens=output_tok,
        cache_creation_tokens=0,
        cache_read_tokens=0,
        model=MODEL,
        provider="copilot",
    )
    text = response.choices[0].message.content or "" if response.choices else ""
    return text, entry


# ── Request / Response models ─────────────────────────────────────────────────

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


# ── Endpoints ─────────────────────────────────────────────────────────────────

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
