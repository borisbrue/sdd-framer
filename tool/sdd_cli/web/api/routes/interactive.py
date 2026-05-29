"""Interaktive Pipeline-Endpunkte – SPEC-0028.

FR-01  POST /api/specs/{id}/review              Spec-Review durch Agent
FR-02  POST /api/specs/{id}/propose-contracts   Contract-Vorschläge durch Agent
FR-05  POST /api/specs/{id}/generate-holdouts   Holdout-Szenarien (Contract-Kontext)
FR-06  GET/PUT /api/specs/{id}/contracts/{cid}  Contract inline lesen/schreiben
       POST /api/specs/{id}/contracts/{cid}/assist
FR-07  GET/PUT /api/specs/{id}/holdouts/{hid}   Holdout inline lesen/schreiben
       POST /api/specs/{id}/holdouts/{hid}/assist
FR-09  POST /api/specs/{id}/run-tests           pytest im Container
FR-11  GET  /api/specs/{id}/job                 Polling-Status
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any
import sdd_context

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parents[3] / "tool"))
sys.path.insert(0, str(Path(__file__).parents[1]))

# Ensure podman/docker and sdd are findable in subprocess calls
_extra_path = ":".join([
    str(Path.home() / ".local/bin"),
    str(Path(sys.executable).parent),
    str(Path.home() / ".local/share/uv/tools/sdd-framer/bin"),
    str(Path.home() / ".local/share/uv/tools/sdd-cli/bin"),
])
os.environ["PATH"] = _extra_path + ":" + os.environ.get("PATH", "")

from sdd_context import get_config
from sdd_cli.frontmatter import parse_safe, Document
from sdd_cli.pipeline_jobs import JobManager
from sdd_cli.dev_container import container_name, get_runtime

router = APIRouter(tags=["interactive"])

_REVIEW_DIR = "reviews"
_HOL_PREFIX = "HOL-"


# ── helpers ───────────────────────────────────────────────────────────────────

def _find_spec(cfg, spec_id: str) -> Document:
    for md in cfg.specs_dir.rglob("*.md"):
        doc = parse_safe(md)
        if doc and doc.frontmatter.get("id") == spec_id:
            return doc
    raise HTTPException(404, f"Spec {spec_id} nicht gefunden")


def _find_contract(cfg, cid: str) -> Document:
    for md in cfg.contracts_dir.rglob("*.md"):
        doc = parse_safe(md)
        if doc and doc.frontmatter.get("id") == cid:
            return doc
    raise HTTPException(404, f"Contract {cid} nicht gefunden")


def _find_holdout(cfg, hid: str) -> Document:
    holdout_dir = cfg.holdout_dir
    for md in holdout_dir.rglob("*.md"):
        doc = parse_safe(md)
        if doc and doc.frontmatter.get("id") == hid:
            return doc
    raise HTTPException(404, f"Holdout {hid} nicht gefunden")


def _next_con_id(cfg) -> str:
    ids = []
    for md in cfg.contracts_dir.rglob("*.md"):
        doc = parse_safe(md)
        if doc:
            raw = doc.frontmatter.get("id", "")
            if raw.startswith("CON-"):
                try:
                    ids.append(int(raw[4:]))
                except ValueError:
                    pass
    return f"CON-{(max(ids, default=0) + 1):04d}"


def _next_hol_id(cfg) -> str:
    holdout_dir = cfg.holdout_dir
    ids = []
    if holdout_dir.exists():
        for md in holdout_dir.rglob("*.md"):
            doc = parse_safe(md)
            if doc:
                raw = doc.frontmatter.get("id", "")
                if raw.startswith("HOL-"):
                    try:
                        ids.append(int(raw[4:]))
                    except ValueError:
                        pass
    return f"HOL-{(max(ids, default=0) + 1):04d}"


def _link_contract_to_spec(spec_doc: Document, con_id: str) -> None:
    contracts = spec_doc.frontmatter.get("contracts") or []
    if con_id not in contracts:
        contracts.append(con_id)
        spec_doc.frontmatter["contracts"] = contracts
        spec_doc.write()


def _get_provider(cfg):
    from sdd_cli.llm import get_completion_provider
    return get_completion_provider(cfg, "ai_routes")


def _mark_gate_phase(cfg, spec_id: str, phase: str) -> None:
    try:
        from sdd_cli.gate import ExecutionGate
        g = ExecutionGate(cfg.root)
        g.mark_phase_started(spec_id, phase)
        g.mark_phase_complete(spec_id, phase)
    except Exception:
        pass


# ── FR-01: Spec-Review ────────────────────────────────────────────────────────

@router.post("/specs/{spec_id}/review")
def review_spec(spec_id: str) -> dict[str, Any]:
    cfg = get_config()
    spec_doc = _find_spec(cfg, spec_id)
    jobs = JobManager(cfg)
    jobs.start(spec_id, "review")

    prompt = f"""Du bist ein SDD-Spec-Reviewer. Analysiere die folgende Spec auf:
1. Fehlende oder unklare funktionale Anforderungen
2. Widersprüche zwischen Anforderungen
3. Fehlende Erfolgskriterien
4. Unklare Nicht-Ziele
5. Fehlende Abhängigkeiten

Antworte als JSON:
{{
  "summary": "Kurzzusammenfassung (1-2 Sätze)",
  "issues": [
    {{"severity": "high|medium|low", "section": "Abschnitt", "text": "Problem"}}
  ],
  "suggestions": ["Verbesserungsvorschlag"]
}}

Spec:
---
{spec_doc.body[:8000]}
"""
    try:
        provider = _get_provider(cfg)
        result = provider.complete(prompt, max_tokens=2048, timeout=90)
        import json as _json
        try:
            data = _json.loads(result.text)
        except Exception:
            import re
            m = re.search(r"\{.*\}", result.text, re.DOTALL)
            data = _json.loads(m.group()) if m else {"summary": result.text, "issues": [], "suggestions": []}

        review_dir = cfg.sdd_dir / _REVIEW_DIR
        review_dir.mkdir(parents=True, exist_ok=True)
        review_path = review_dir / f"{spec_id}-review.md"
        lines = [f"# Review: {spec_id}\n", f"**Summary:** {data.get('summary', '')}\n\n"]
        for iss in data.get("issues", []):
            lines.append(f"- [{iss.get('severity','?').upper()}] **{iss.get('section','')}**: {iss.get('text','')}\n")
        for sug in data.get("suggestions", []):
            lines.append(f"- {sug}\n")
        review_path.write_text("".join(lines), encoding="utf-8")

        _mark_gate_phase(cfg, spec_id, "spec-review")
        jobs.finish(spec_id, ok=True, result=data)
        return {"ok": True, "output": data.get("summary", "Review abgeschlossen"), **data}
    except Exception as e:
        jobs.finish(spec_id, ok=False)
        return {"ok": False, "output": str(e)}


# ── FR-02: Contracts vorschlagen ──────────────────────────────────────────────

@router.post("/specs/{spec_id}/propose-contracts")
def propose_contracts(spec_id: str) -> dict[str, Any]:
    cfg = get_config()
    spec_doc = _find_spec(cfg, spec_id)
    jobs = JobManager(cfg)
    jobs.start(spec_id, "propose-contracts")

    prompt = f"""Du bist ein SDD-Contract-Designer. Analysiere die Spec und schlage Contracts vor.

Für jeden Contract erstelle:
- title: Kurzer Titel
- type: api | behavior | data | performance
- format: openapi | markdown | json-schema | slo
- guarantee: Ein Satz was dieser Contract garantiert

Antworte als JSON-Array:
[
  {{"title": "...", "type": "api", "format": "openapi", "guarantee": "..."}}
]

Spec (Anforderungen):
---
{spec_doc.body[:6000]}
"""
    try:
        provider = _get_provider(cfg)
        result = provider.complete(prompt, max_tokens=2048, timeout=90)
        import json as _json, re as _re
        try:
            proposals = _json.loads(result.text)
        except Exception:
            m = _re.search(r"\[.*\]", result.text, _re.DOTALL)
            proposals = _json.loads(m.group()) if m else []

        created = []
        for prop in proposals[:6]:
            con_id = _next_con_id(cfg)
            slug = prop.get("title", con_id).lower().replace(" ", "-")[:40]
            slug = _re.sub(r"[^a-z0-9-]", "", slug)
            con_type = prop.get("type", "behavior")
            type_dir = cfg.contracts_dir / con_type
            type_dir.mkdir(parents=True, exist_ok=True)
            con_path = type_dir / f"{con_id}-{slug}.md"
            fm = {
                "id": con_id,
                "project": "PRJ-0001",
                "title": prop.get("title", con_id),
                "type": con_type,
                "format": prop.get("format", "markdown"),
                "spec": spec_id,
                "version": "0.1.0",
                "status": "draft",
            }
            import yaml as _yaml
            body = f"# Contract: {prop.get('title', con_id)}\n\n## Garantie\n\n{prop.get('guarantee', '')}\n"
            con_path.write_text(f"---\n{_yaml.safe_dump(fm, allow_unicode=True)}---\n{body}", encoding="utf-8")
            _link_contract_to_spec(spec_doc, con_id)
            created.append({"id": con_id, "title": prop.get("title"), "path": str(con_path.relative_to(cfg.root))})

        _mark_gate_phase(cfg, spec_id, "contracts-proposed")
        jobs.finish(spec_id, ok=True, result={"contracts": created})
        return {"ok": True, "output": f"{len(created)} Contract(s) erstellt", "contracts": created}
    except Exception as e:
        jobs.finish(spec_id, ok=False)
        return {"ok": False, "output": str(e)}


# ── FR-05: Holdouts generieren ────────────────────────────────────────────────

@router.post("/specs/{spec_id}/generate-holdouts")
def generate_holdouts(spec_id: str) -> dict[str, Any]:
    cfg = get_config()
    spec_doc = _find_spec(cfg, spec_id)
    jobs = JobManager(cfg)
    jobs.start(spec_id, "generate-holdouts")

    contract_ids: list[str] = spec_doc.frontmatter.get("contracts") or []
    contract_texts: list[str] = []
    for cid in contract_ids:
        try:
            doc = _find_contract(cfg, cid)
            contract_texts.append(f"### {cid}: {doc.frontmatter.get('title','')}\n{doc.body[:2000]}")
        except HTTPException:
            pass

    if not contract_texts:
        jobs.finish(spec_id, ok=False)
        return {"ok": False, "output": "Keine Contracts verknüpft – erst Contracts anlegen"}

    prompt = f"""Du bist ein SDD-Holdout-Designer. Erstelle Evaluierungs-Szenarien
ausschließlich basierend auf den folgenden Contracts (KEIN Sourcecode-Kontext).

Für jedes Szenario:
- title: Kurzer Titel
- input: Was dem System gegeben wird
- expected: Was das System liefern soll
- evaluation_hint: Wie ein LLM-Evaluator prüfen soll

Antworte als JSON-Array (3-5 Szenarien):
[
  {{"title": "...", "input": "...", "expected": "...", "evaluation_hint": "..."}}
]

Contracts:
{chr(10).join(contract_texts[:4000])}
"""
    try:
        provider = _get_provider(cfg)
        result = provider.complete(prompt, max_tokens=2048, timeout=90)
        import json as _json, re as _re, yaml as _yaml
        try:
            scenarios = _json.loads(result.text)
        except Exception:
            m = _re.search(r"\[.*\]", result.text, _re.DOTALL)
            scenarios = _json.loads(m.group()) if m else []

        holdout_dir = cfg.holdout_dir
        holdout_dir.mkdir(parents=True, exist_ok=True)
        created = []
        for sc in scenarios[:6]:
            hol_id = _next_hol_id(cfg)
            slug = sc.get("title", hol_id).lower().replace(" ", "-")[:40]
            slug = _re.sub(r"[^a-z0-9-]", "", slug)
            hol_path = holdout_dir / f"{hol_id}-{slug}.md"
            fm = {
                "id": hol_id,
                "spec": spec_id,
                "title": sc.get("title", hol_id),
                "status": "draft",
            }
            body = (
                f"# Holdout: {sc.get('title', hol_id)}\n\n"
                f"## Input\n\n{sc.get('input', '')}\n\n"
                f"## Expected\n\n{sc.get('expected', '')}\n\n"
                f"## Evaluation Hint\n\n{sc.get('evaluation_hint', '')}\n"
            )
            hol_path.write_text(f"---\n{_yaml.safe_dump(fm, allow_unicode=True)}---\n{body}", encoding="utf-8")
            created.append({"id": hol_id, "title": sc.get("title"), "path": str(hol_path.relative_to(cfg.root))})

        jobs.finish(spec_id, ok=True, result={"holdouts": created})
        return {"ok": True, "output": f"{len(created)} Holdout(s) erstellt", "holdouts": created}
    except Exception as e:
        jobs.finish(spec_id, ok=False)
        return {"ok": False, "output": str(e)}


# ── Holdout-Liste ─────────────────────────────────────────────────────────────

@router.get("/holdouts/{hol_id}")
def get_single_holdout(hol_id: str) -> dict[str, Any]:
    cfg = get_config()
    doc = _find_holdout(cfg, hol_id)
    return {
        "id": hol_id,
        "title": doc.frontmatter.get("title", hol_id),
        "status": doc.frontmatter.get("status", "draft"),
        "spec": doc.frontmatter.get("spec", ""),
        "body": doc.body,
        "abs_file": str(doc.path.resolve()),
    }


@router.get("/specs/{spec_id}/holdouts")
def list_holdouts(spec_id: str) -> dict[str, Any]:
    cfg = get_config()
    holdout_dir = cfg.holdout_dir
    items = []
    if holdout_dir.exists():
        for md in sorted(holdout_dir.glob("HOL-*.md")):
            doc = parse_safe(md)
            if doc and doc.frontmatter.get("spec") == spec_id:
                items.append({
                    "id": doc.frontmatter.get("id"),
                    "title": doc.frontmatter.get("title", md.stem),
                    "status": doc.frontmatter.get("status", "draft"),
                    "body": doc.body,
                    "abs_file": str(md.resolve()),
                })
    return {"holdouts": items}


class StatusPatch(BaseModel):
    status: str


@router.patch("/specs/{spec_id}/holdouts/{hol_id}/status")
def patch_holdout_status(spec_id: str, hol_id: str, payload: StatusPatch) -> dict[str, Any]:
    cfg = get_config()
    doc = _find_holdout(cfg, hol_id)
    doc.frontmatter["status"] = payload.status
    doc.write()
    return {"ok": True, "id": hol_id, "status": payload.status}


# ── FR-06: Contract inline lesen / schreiben / assist ─────────────────────────

@router.get("/specs/{spec_id}/contracts/{con_id}")
def get_contract(spec_id: str, con_id: str) -> dict[str, Any]:
    cfg = get_config()
    doc = _find_contract(cfg, con_id)
    return {"id": con_id, "frontmatter": doc.frontmatter, "body": doc.body, "path": str(doc.path)}


class PutBody(BaseModel):
    body: str


@router.put("/specs/{spec_id}/contracts/{con_id}")
def put_contract(spec_id: str, con_id: str, payload: PutBody) -> dict[str, Any]:
    cfg = get_config()
    doc = _find_contract(cfg, con_id)
    doc.body = payload.body
    doc.write()
    return {"ok": True, "id": con_id}


class AssistBody(BaseModel):
    question: str
    context: str = ""


@router.post("/specs/{spec_id}/contracts/{con_id}/assist")
def assist_contract(spec_id: str, con_id: str, payload: AssistBody) -> dict[str, Any]:
    cfg = get_config()
    doc = _find_contract(cfg, con_id)
    prompt = (
        f"Du hilfst bei einem SDD-Contract.\n\n"
        f"Contract ({con_id}):\n{doc.body[:3000]}\n\n"
        f"Frage: {payload.question}\n"
        f"{('Zusatzkontext: ' + payload.context) if payload.context else ''}"
    )
    try:
        provider = _get_provider(cfg)
        result = provider.complete(prompt, max_tokens=1024, timeout=60)
        return {"ok": True, "output": result.text}
    except Exception as e:
        return {"ok": False, "output": str(e)}


# ── FR-07: Holdout inline lesen / schreiben / assist ──────────────────────────

@router.get("/specs/{spec_id}/holdouts/{hol_id}")
def get_holdout(spec_id: str, hol_id: str) -> dict[str, Any]:
    cfg = get_config()
    doc = _find_holdout(cfg, hol_id)
    return {"id": hol_id, "frontmatter": doc.frontmatter, "body": doc.body, "path": str(doc.path)}


@router.put("/specs/{spec_id}/holdouts/{hol_id}")
def put_holdout(spec_id: str, hol_id: str, payload: PutBody) -> dict[str, Any]:
    cfg = get_config()
    doc = _find_holdout(cfg, hol_id)
    doc.body = payload.body
    doc.write()
    return {"ok": True, "id": hol_id}


@router.post("/specs/{spec_id}/holdouts/{hol_id}/assist")
def assist_holdout(spec_id: str, hol_id: str, payload: AssistBody) -> dict[str, Any]:
    cfg = get_config()
    doc = _find_holdout(cfg, hol_id)
    prompt = (
        f"Du hilfst bei einem SDD-Holdout-Szenario (nur Contract-Kontext, kein Sourcecode).\n\n"
        f"Holdout ({hol_id}):\n{doc.body[:3000]}\n\n"
        f"Frage: {payload.question}\n"
        f"{('Zusatzkontext: ' + payload.context) if payload.context else ''}"
    )
    try:
        provider = _get_provider(cfg)
        result = provider.complete(prompt, max_tokens=1024, timeout=60)
        return {"ok": True, "output": result.text}
    except Exception as e:
        return {"ok": False, "output": str(e)}


# ── FR-09: Tests im Container ─────────────────────────────────────────────────

@router.post("/specs/{spec_id}/run-tests")
def run_tests_in_container(spec_id: str) -> dict[str, Any]:
    cfg = get_config()
    jobs = JobManager(cfg)
    jobs.start(spec_id, "run-tests")
    try:
        runtime = get_runtime(cfg)
        cname = container_name(spec_id)
        if runtime.inspect_status(cname) != "running":
            jobs.finish(spec_id, ok=False)
            return {"ok": False, "output": f"Container {cname} läuft nicht. Starte ihn zuerst."}

        # Stream output line-by-line into the LogEventBus so the WebSocket Log-Panel shows it live
        try:
            bus = sdd_context.get_log_event_bus()
            bus.mark_active(spec_id)
        except Exception:
            bus = None

        cmd = [runtime.cli(), "exec", cname, "bash", "-c",
               "export PATH=/usr/local/bin:/usr/bin:/bin:$PATH && "
               "cd /workspace && "
               "pip install -q -e '.[dev]' 2>&1 | tail -3 && "
               "pytest tests/ -x --tb=short -q 2>&1"]

        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        assert proc.stdout is not None
        collected: list[str] = []
        for line in proc.stdout:
            line = line.rstrip("\n")
            collected.append(line)
            if bus:
                try:
                    bus.publish(spec_id, line)
                except Exception:
                    pass
        proc.wait()

        ok = proc.returncode == 0
        jobs.finish(spec_id, ok=ok, result={"returncode": proc.returncode})
        return {"ok": ok, "output": "\n".join(collected)}
    except Exception as e:
        jobs.finish(spec_id, ok=False)
        return {"ok": False, "output": str(e)}


# ── FR-11: Job-Status ─────────────────────────────────────────────────────────

@router.get("/specs/{spec_id}/job")
def get_job(spec_id: str) -> dict[str, Any]:
    cfg = get_config()
    job = JobManager(cfg).get(spec_id)
    if not job:
        return {"spec_id": spec_id, "status": "idle"}
    from dataclasses import asdict
    return asdict(job)
