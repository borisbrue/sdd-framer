"""Claude AI endpoints for spec generation and improvement."""
from __future__ import annotations

import asyncio
import json as json_lib
import logging
import re
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
            timeout=300,
        )
    except RuntimeError as exc:
        log.error("AI-Call Fehler (%s): %s", operation, exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    log.info("AI-Call abgeschlossen: operation=%s tokens_out=%s",
             operation, result.usage.output_tokens if result.usage else "?")

    text = result.text
    if result.usage:
        entry = usage_store.record_usage(
            operation=operation,
            input_tokens=result.usage.input_tokens,
            output_tokens=result.usage.output_tokens,
            cache_creation_tokens=result.usage.cache_creation_tokens,
            cache_read_tokens=result.usage.cache_read_tokens,
            model=result.usage.model,
        )
    else:
        entry: dict[str, Any] = {}
    return text, entry


# Artifact generation hints per contract format
_ARTIFACT_HINT: dict[str, str] = {
    "openapi": (
        "Vollständige OpenAPI 3.1.0 YAML-Spezifikation mit realistischen Pfaden, Operationen "
        "und Schemas, die direkt auf den Funktionalen Anforderungen basieren. "
        "Keine Platzhalter wie /example — verwende echte Ressourcennamen aus dem Kontext."
    ),
    "gherkin": (
        "Vollständige Gherkin-Feature-Datei (# language: de) mit mindestens 3 Szenarien "
        "(Angenommen/Wenn/Dann), direkt abgeleitet aus den Akzeptanzkriterien der Spec."
    ),
    "json-schema": (
        "Vollständiges JSON Schema (draft-07) mit $schema, title, required und properties "
        "für alle relevanten Datenstrukturen aus dem Kontext."
    ),
    "slo-yaml": (
        "SLO-YAML mit konkreten Metriken und Targets aus den NFRs der Spec. "
        "Format: slos: [{name, objective, sli, description}]"
    ),
    "asyncapi": (
        "AsyncAPI 2.6.0 YAML mit realistischen Channels und Message-Schemas "
        "basierend auf den Anforderungen."
    ),
    "markdown": (
        "Vollständiger Markdown-Text mit Überschriften, der das Verhalten oder die "
        "Schnittstelle detailliert beschreibt."
    ),
}


# Request / Response models

class GenerateSpecRequest(BaseModel):
    title: str
    description: str = ""
    context: str = ""


class ImproveSpecRequest(BaseModel):
    spec_id: str
    current_content: str
    instructions: str


class ImproveSectionRequest(BaseModel):
    spec_id: str
    section_heading: str
    section_content: str
    instructions: str
    full_spec_content: str = ""
    linked_spec_ids: list[str] = []


class FixFindingRequest(BaseModel):
    spec_id: str
    finding_text: str
    finding_section: str = ""
    full_spec_content: str
    instructions: str = ""


class SuggestContractsRequest(BaseModel):
    spec_id: str
    spec_content: str


class ContractRef(BaseModel):
    id: str
    title: str
    format: str = ""


class SuggestTestsRequest(BaseModel):
    spec_id: str
    spec_content: str
    contracts: list[ContractRef] = []


class TestSuggestion(BaseModel):
    title: str
    level: str
    contract_id: str
    description: str


class SuggestTestsStructuredResponse(BaseModel):
    suggestions: list[TestSuggestion]
    usage: dict[str, Any]


class ContractSuggestion(BaseModel):
    title: str
    format: str
    description: str


class SuggestContractsStructuredResponse(BaseModel):
    suggestions: list[ContractSuggestion]
    usage: dict[str, Any]


class AiResponse(BaseModel):
    result: str
    usage: dict[str, Any]


# Endpoints

@router.post("/generate-spec", response_model=AiResponse)
async def generate_spec(body: GenerateSpecRequest) -> AiResponse:
    """Generates only the 'Kontext & Motivation' section — the frontend fills the rest from a template."""
    prompt = (
        f"Schreibe den Inhalt für Abschnitt '1. Kontext & Motivation' einer Spec mit dem Titel: **{body.title}**.\n\n"
    )
    if body.description:
        prompt += f"Nutzerhinweis: {body.description}\n\n"
    if body.context:
        prompt += f"Weiterer Kontext: {body.context}\n\n"
    prompt += (
        "Der Abschnitt soll in 3–5 Sätzen beschreiben:\n"
        "- Den Ist-Zustand und das konkrete Problem\n"
        "- Die Motivation / den Auslöser für dieses Feature\n"
        "- Wer die betroffenen Nutzer oder Stakeholder sind\n\n"
        "Gib NUR den Abschnitt-Inhalt zurück — kein Heading, kein Frontmatter, keine Code-Fences. "
        "Antworte in der gleichen Sprache wie der Titel."
    )
    text, entry = await asyncio.to_thread(_call, "generate-spec", prompt)
    return AiResponse(result=text, usage=entry)


@router.post("/improve-spec", response_model=AiResponse)
async def improve_spec(body: ImproveSpecRequest) -> AiResponse:
    prompt = (
        f"Improve the following Spec ({body.spec_id}) according to these instructions:\n\n"
        f"**Instructions:** {body.instructions}\n\n"
        f"**Current content:**\n\n{body.current_content}\n\n"
        "Return only the improved Markdown body (no frontmatter, no code fences)."
    )
    text, entry = await asyncio.to_thread(_call, "improve-spec", prompt)
    return AiResponse(result=text, usage=entry)


@router.post("/suggest-contracts", response_model=AiResponse)
async def suggest_contracts(body: SuggestContractsRequest) -> AiResponse:
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
    text, entry = await asyncio.to_thread(_call, "suggest-contracts", prompt)
    return AiResponse(result=text, usage=entry)


@router.post("/improve-section", response_model=AiResponse)
async def improve_section(body: ImproveSectionRequest) -> AiResponse:
    # Fetch linked spec bodies on demand
    linked_parts: list[str] = []
    for sid in body.linked_spec_ids[:5]:
        spec_body = await asyncio.to_thread(_read_spec_body, sid)
        if spec_body and spec_body.strip():
            linked_parts.append(f"### {sid}\n\n{spec_body.strip()}")

    section_label = body.section_heading or "(Preamble)"
    prompt = (
        f"Improve the following section of Spec {body.spec_id}.\n\n"
        f"**Section:** {section_label}\n\n"
        f"**Current content:**\n\n{body.section_content}\n\n"
        f"**Instructions:** {body.instructions}\n\n"
    )
    if body.full_spec_content:
        prompt += f"**Spec-Struktur (Inhaltsverzeichnis, kein Fließtext):**\n\n{body.full_spec_content}\n\n"
    if linked_parts:
        prompt += "**Linked specs (context only):**\n\n" + "\n\n---\n\n".join(linked_parts) + "\n\n"
    prompt += (
        "Return ONLY the improved section content — no heading line, no frontmatter, no code fences. "
        "Preserve Markdown style. Respond in the same language as the spec."
    )
    text, entry = await asyncio.to_thread(_call, "improve-section", prompt)
    return AiResponse(result=text, usage=entry)


@router.post("/suggest-contracts-structured", response_model=SuggestContractsStructuredResponse)
async def suggest_contracts_structured(body: SuggestContractsRequest) -> SuggestContractsStructuredResponse:
    prompt = (
        f"Analysiere folgendes Spec ({body.spec_id}) und schlage passende Contracts vor.\n\n"
        f"**Spec-Inhalt:**\n\n{body.spec_content}\n\n"
        "Antworte NUR mit einem JSON-Array ohne weiteren Text oder Code-Fences. Format:\n"
        '[{"title": "...", "format": "<eines der erlaubten Formate>", "description": "..."}]\n\n'
        f"Erlaubte Werte für format: {_get_supported_formats_str()}.\n"
        "Schlage für jede verifizierbares Interface/Schnittstelle einen Contract vor (max. 5). "
        "Antworte in der gleichen Sprache wie das Spec."
    )
    text, entry = await asyncio.to_thread(_call, "suggest-contracts-structured", prompt)
    suggestions: list[ContractSuggestion] = []
    try:
        match = re.search(r"\[[\s\S]*?\]", text)
        if match:
            raw = json_lib.loads(match.group(0))
            suggestions = [ContractSuggestion(**s) for s in raw if isinstance(s, dict)]
        else:
            log.warning("suggest-contracts-structured: kein JSON-Array in Antwort gefunden. raw=%r", text[:200])
    except Exception as exc:
        log.warning("suggest-contracts-structured: JSON-Parse-Fehler: %s — raw=%r", exc, text[:200])
    return SuggestContractsStructuredResponse(suggestions=suggestions, usage=entry)


@router.post("/suggest-tests-structured", response_model=SuggestTestsStructuredResponse)
async def suggest_tests_structured(body: SuggestTestsRequest) -> SuggestTestsStructuredResponse:
    contracts_list = "\n".join(
        f'- {c.id}: "{c.title}" [{c.format}]' for c in body.contracts
    ) or "  (keine Contracts angegeben)"
    valid_levels = "unit, integration, contract, acceptance, performance, property"
    prompt = (
        f"Analysiere folgendes Spec ({body.spec_id}) und schlage passende Tests vor.\n\n"
        f"**Spec-Inhalt:**\n\n{body.spec_content}\n\n"
        f"**Vorhandene Contracts:**\n{contracts_list}\n\n"
        "Antworte NUR mit einem JSON-Array ohne weiteren Text oder Code-Fences. Format:\n"
        '[{"title": "...", "level": "<eines der erlaubten Level>", '
        '"contract_id": "<ID eines der Contracts>", "description": "..."}]\n\n'
        f"Erlaubte Werte für level: {valid_levels}.\n"
        "Schlage für jeden Contract mindestens einen sinnvollen Test vor (max. 6 gesamt). "
        "Antworte in der gleichen Sprache wie das Spec."
    )
    text, entry = await asyncio.to_thread(_call, "suggest-tests-structured", prompt)
    suggestions: list[TestSuggestion] = []
    try:
        match = re.search(r"\[[\s\S]*?\]", text)
        if match:
            raw = json_lib.loads(match.group(0))
            suggestions = [TestSuggestion(**s) for s in raw if isinstance(s, dict)]
        else:
            log.warning("suggest-tests-structured: kein JSON-Array in Antwort gefunden. raw=%r", text[:200])
    except Exception as exc:
        log.warning("suggest-tests-structured: JSON-Parse-Fehler: %s — raw=%r", exc, text[:200])
    return SuggestTestsStructuredResponse(suggestions=suggestions, usage=entry)


@router.post("/fix-finding", response_model=AiResponse)
async def fix_finding(body: FixFindingRequest) -> AiResponse:
    section_hint = f" in Abschnitt '{body.finding_section}'" if body.finding_section else ""
    extra = f"\n\n**Weitere Anweisungen:** {body.instructions}" if body.instructions else ""
    prompt = (
        f"Behebe folgendes Problem{section_hint} in Spec {body.spec_id}.\n\n"
        f"**Problem:** {body.finding_text}{extra}\n\n"
        f"**Aktueller Spec-Inhalt:**\n\n{body.full_spec_content}\n\n"
        "Gib NUR den verbesserten Markdown-Body zurück — kein Frontmatter, keine Code-Fences. "
        "Alle nicht betroffenen Abschnitte unverändert lassen. "
        "Antworte in der gleichen Sprache wie das Spec."
    )
    text, entry = await asyncio.to_thread(_call, "fix-finding", prompt)
    return AiResponse(result=text, usage=entry)


class FillContractRequest(BaseModel):
    contract_id: str
    spec_context: str  # sections 1, 2, 4 from the spec


class FillTestRequest(BaseModel):
    test_id: str
    spec_context: str
    contract_description: str = ""


class ImplementTestRequest(BaseModel):
    test_id: str


@router.post("/fill-contract", response_model=AiResponse)
async def fill_contract(body: FillContractRequest) -> AiResponse:
    """Generate body + artifact for a contract and write them to disk."""
    try:
        from sdd_cli.frontmatter import parse_safe
        cfg = get_config()
        contract_doc = None
        for md in cfg.contracts_dir.rglob("*.md"):
            doc = parse_safe(md)
            if doc and doc.frontmatter.get("id") == body.contract_id:
                contract_doc = doc
                break
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if not contract_doc:
        raise HTTPException(status_code=404, detail=f"{body.contract_id} nicht gefunden.")

    fmt   = contract_doc.frontmatter.get("format", "markdown")
    title = contract_doc.frontmatter.get("title", "")
    artifact_rel = contract_doc.frontmatter.get("artifact", "")
    artifact_hint = _ARTIFACT_HINT.get(fmt, "Inhalt passend zum Format.")

    prompt = (
        f"Erstelle Inhalte für einen SDD-Contract.\n\n"
        f"**Contract:** {title} (Format: {fmt}, ID: {body.contract_id})\n\n"
        f"**Spec-Kontext:**\n{body.spec_context}\n\n"
        "Antworte NUR mit einem JSON-Objekt ohne weiteren Text oder Code-Fences:\n"
        '{"body": "...", "artifact": "..."}\n\n'
        f"- `body`: Markdown-Text für die Contract-Beschreibungsdatei "
        f"(Zweck, Garantien, Geltungsbereich). Kein Frontmatter, keine Überschrift.\n"
        f"- `artifact`: {artifact_hint}\n\n"
        "Antworte in der gleichen Sprache wie der Spec-Kontext."
    )
    text, entry = await asyncio.to_thread(_call, "fill-contract", prompt)

    try:
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            data = json_lib.loads(match.group(0))
            if data.get("body"):
                contract_doc.body = data["body"]
                contract_doc.write()
            if data.get("artifact") and artifact_rel:
                artifact_path = cfg.root / artifact_rel
                artifact_path.parent.mkdir(parents=True, exist_ok=True)
                artifact_path.write_text(data["artifact"], encoding="utf-8")
    except Exception as exc:
        log.warning("fill-contract: Schreibfehler: %s", exc)

    return AiResponse(result="ok", usage=entry)


@router.post("/fill-test", response_model=AiResponse)
async def fill_test(body: FillTestRequest) -> AiResponse:
    """Generate body for a test and write it to disk."""
    try:
        from sdd_cli.frontmatter import parse_safe
        cfg = get_config()
        test_doc = None
        for base in cfg.all_test_dirs:
            for md in base.rglob("*.md"):
                doc = parse_safe(md)
                if doc and doc.frontmatter.get("id") == body.test_id:
                    test_doc = doc
                    break
            if test_doc:
                break
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if not test_doc:
        raise HTTPException(status_code=404, detail=f"{body.test_id} nicht gefunden.")

    level       = test_doc.frontmatter.get("level", "")
    title       = test_doc.frontmatter.get("title", "")
    contract_id = test_doc.frontmatter.get("contract", "")
    contract_ctx = f"\n**Contract-Beschreibung:** {body.contract_description}" if body.contract_description else ""

    prompt = (
        f"Erstelle den Body für einen SDD-Test.\n\n"
        f"**Test:** {title} (Level: {level}, ID: {body.test_id})\n"
        f"**Zugehöriger Contract:** {contract_id}{contract_ctx}\n\n"
        f"**Spec-Kontext:**\n{body.spec_context}\n\n"
        "Beschreibe konkret (Markdown, keine Frontmatter, keine # Überschrift):\n"
        "1. Was wird geprüft?\n"
        "2. Vorbedingungen\n"
        "3. Ablauf\n"
        "4. Erwartetes Ergebnis\n"
        "5. Negativfälle / Edge Cases\n"
        "6. Verknüpfung mit dem Contract\n"
        "7. Hinweise zur Implementierung (Framework, Tools)\n\n"
        "Antworte in der gleichen Sprache wie der Spec-Kontext."
    )
    text, entry = await asyncio.to_thread(_call, "fill-test", prompt)

    try:
        test_doc.body = text
        test_doc.write()
    except Exception as exc:
        log.warning("fill-test: Schreibfehler: %s", exc)

    return AiResponse(result="ok", usage=entry)


@router.post("/implement-test", response_model=AiResponse)
async def implement_test(body: ImplementTestRequest) -> AiResponse:
    """Generate pytest implementation for a test stub and write it to disk."""
    try:
        from sdd_cli.frontmatter import parse_safe
        cfg = get_config()
        tst_doc = None
        for base in cfg.all_test_dirs:
            for md in base.rglob("*.md"):
                doc = parse_safe(md)
                if doc and doc.frontmatter.get("id") == body.test_id:
                    tst_doc = doc
                    break
            if tst_doc:
                break
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if not tst_doc:
        raise HTTPException(status_code=404, detail=f"{body.test_id} nicht gefunden.")

    tst_id     = body.test_id
    title      = tst_doc.frontmatter.get("title", "")
    level      = tst_doc.frontmatter.get("level", "unit")
    contract_id = tst_doc.frontmatter.get("contract", "")
    tst_body   = (tst_doc.body or "").strip()
    class_name = "Test" + tst_id.replace("-", "")

    # Derive stub path (mirror _derive_stub_path logic)
    artifact_fm = tst_doc.frontmatter.get("artifact", "")
    if artifact_fm and "<" not in artifact_fm:
        stub_path = cfg.root / artifact_fm
    else:
        slug = tst_id.lower().replace("-", "_")
        stub_path = cfg.project_tests_dir / level / f"test_{slug}.py"

    # Read linked contract + artifact
    con_title, con_fmt, artifact_content, artifact_rel = "", "", "", ""
    if contract_id:
        try:
            from sdd_cli.frontmatter import parse_safe as _ps
            for md in cfg.contracts_dir.rglob("*.md"):
                doc = _ps(md)
                if doc and doc.frontmatter.get("id") == contract_id:
                    con_title = doc.frontmatter.get("title", "")
                    con_fmt = doc.frontmatter.get("format", "")
                    artifact_rel = doc.frontmatter.get("artifact", "")
                    if artifact_rel:
                        p = cfg.root / artifact_rel
                        if p.exists():
                            artifact_content = p.read_text(encoding="utf-8")
                    break
        except Exception as exc:
            log.warning("implement-test: Contract-Artefakt nicht lesbar: %s", exc)

    artifact_section = ""
    if artifact_content:
        artifact_section = (
            f"\n**Contract-Artefakt** (`{artifact_rel}`):\n"
            f"{artifact_content[:3000]}\n"
        )

    prompt = (
        f"Schreibe ein ausführbares pytest-Modul für folgenden SDD-Test.\n\n"
        f"**Test-ID:** {tst_id}\n"
        f"**Titel:** {title}\n"
        f"**Level:** {level}\n"
        f"**Contract:** {contract_id} – {con_title} (Format: {con_fmt})\n"
        f"**Ausgabe-Datei:** {stub_path.name}\n\n"
        f"**Testbeschreibung:**\n{tst_body}\n"
        f"{artifact_section}\n"
        "**Anforderungen:**\n"
        "- Nur valider Python-Code, KEINE Markdown-Fences, keine Prosa\n"
        "- Verfügbare Imports: pathlib, pytest, yaml, jsonschema (alle installiert)\n"
        f"- Testklasse: `{class_name}` mit Methoden die `test_` beginnen\n"
        "- KEIN pytest.skip(), KEIN raise NotImplementedError — alle Tests sollen laufen\n"
        "- Kein Netzwerkzugriff: Mocks, In-Memory-Objekte oder statische Dateivalidierung\n"
        f"- Contract-Artefakt liegt unter: `{artifact_rel}` (Pfad relativ zu Repo-Root)\n"
        "- Pfad zu Repo-Root aus Testdatei: `Path(__file__).resolve().parents[2]`\n"
    )
    text, entry = await asyncio.to_thread(_call, "implement-test", prompt)

    code = text.strip()
    if code.startswith("```"):
        lines = code.splitlines()
        end = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
        code = "\n".join(lines[1:end])

    written = False
    if "import pytest" in code and "def test_" in code:
        try:
            stub_path.parent.mkdir(parents=True, exist_ok=True)
            stub_path.write_text(code, encoding="utf-8")
            written = True
            log.info("implement-test: %s geschrieben nach %s", tst_id, stub_path)
        except Exception as exc:
            log.warning("implement-test: Schreibfehler: %s", exc)
    else:
        log.warning("implement-test: kein valider pytest-Code für %s generiert", tst_id)

    result_msg = stub_path.name if written else "error: kein valider pytest-Code generiert"
    return AiResponse(result=result_msg, usage=entry)


def _get_supported_formats_str() -> str:
    try:
        from sdd_cli.templates import CONTRACT_TEMPLATES
        return ", ".join(CONTRACT_TEMPLATES.keys())
    except Exception:
        return "openapi, asyncapi, graphql, grpc, json-schema, markdown"


def _read_spec_body(spec_id: str) -> str | None:
    """Read a spec's Markdown body by ID without raising HTTP errors."""
    try:
        from sdd_cli.frontmatter import parse_safe
        cfg = get_config()
        for md in cfg.specs_dir.rglob("*.md"):
            doc = parse_safe(md)
            if doc and doc.frontmatter.get("id") == spec_id:
                return doc.body
    except Exception:
        pass
    return None


@router.get("/usage")
def get_usage() -> dict[str, Any]:
    return {
        "summary": usage_store.get_summary(),
        "records": usage_store.get_all(),
    }
