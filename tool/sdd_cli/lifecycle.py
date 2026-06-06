"""Content-Update-Lifecycle: Status-Transitionen und LLM Contract-Review.

Implementiert SPEC-0010:
- SHA-256-basiertes Content-Tracking (ohne status:/updated:-Zeilen)
- Automatische Statusübergänge (approved/implemented → review)
- Audit-Log (.sdd/audit.log)
- LLM Contract-Review mit TST-Datei-Generierung
- Pending-Contracts-Abfrage

Implementiert SPEC-0019:
- start_spec(): approved → in-progress, Test-Stubs generieren
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .config import SddConfig
from .frontmatter import Document, parse_safe, patch_status

_STRIP_LINES_RE = re.compile(r"^\s*(updated|status)\s*:", re.MULTILINE)

CONTENT_HASHES_FILE = ".sdd/content-hashes.json"
AUDIT_LOG_FILE = ".sdd/audit.log"

_EDIT_TRANSITIONS: dict[str, str] = {
    "approved": "review",
    "implemented": "review",
}


# ─────────────────────────────────────────────────────────────────────────────
# Hash-Hilfsfunktionen
# ─────────────────────────────────────────────────────────────────────────────

def compute_content_hash(text: str) -> str:
    """SHA-256 des Dateiinhalts ohne updated:- und status:-Zeilen."""
    lines = [
        line for line in text.splitlines(keepends=True)
        if not _STRIP_LINES_RE.match(line)
    ]
    return hashlib.sha256("".join(lines).encode("utf-8")).hexdigest()


def load_hashes(config: SddConfig) -> dict[str, str]:
    path = config.root / CONTENT_HASHES_FILE
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_hashes(config: SddConfig, hashes: dict[str, str]) -> None:
    path = config.root / CONTENT_HASHES_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(hashes, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def rebuild_hashes(config: SddConfig) -> dict[str, str]:
    """Berechnet alle Hashes neu (Erstlauf / Rebuild)."""
    hashes: dict[str, str] = {}
    for base_dir in (config.specs_dir, config.contracts_dir):
        if not base_dir.exists():
            continue
        for md in base_dir.rglob("*.md"):
            doc = parse_safe(md)
            if not doc or not doc.frontmatter:
                continue
            artifact_id = doc.frontmatter.get("id")
            if artifact_id:
                hashes[artifact_id] = compute_content_hash(
                    md.read_text(encoding="utf-8")
                )
    return hashes


# ─────────────────────────────────────────────────────────────────────────────
# Audit-Log
# ─────────────────────────────────────────────────────────────────────────────

def write_audit_log(
    config: SddConfig,
    artifact_id: str,
    old_status: str,
    new_status: str,
    reason: str,
) -> None:
    path = config.root / AUDIT_LOG_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"{ts} {artifact_id} {old_status} → {new_status} [{reason}]\n"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line)


# ─────────────────────────────────────────────────────────────────────────────
# Status-Übergänge
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class StatusChange:
    artifact_id: str
    path: Path
    old_status: str
    new_status: str


def check_transitions(config: SddConfig) -> list[StatusChange]:
    """Vergleicht aktuellen Content-Hash mit gespeichertem.

    Gibt alle Artefakte zurück, deren Status aufgrund einer inhaltlichen
    Änderung zurückgesetzt werden muss.
    """
    hashes = load_hashes(config)
    changes: list[StatusChange] = []

    for base_dir in (config.specs_dir, config.contracts_dir):
        if not base_dir.exists():
            continue
        for md in sorted(base_dir.rglob("*.md")):
            doc = parse_safe(md)
            if not doc or not doc.frontmatter:
                continue
            artifact_id = doc.frontmatter.get("id")
            if not artifact_id:
                continue
            status = doc.frontmatter.get("status", "draft")
            if status not in _EDIT_TRANSITIONS:
                continue

            current_hash = compute_content_hash(md.read_text(encoding="utf-8"))
            stored_hash = hashes.get(artifact_id)

            if stored_hash is not None and current_hash != stored_hash:
                changes.append(StatusChange(
                    artifact_id=artifact_id,
                    path=md,
                    old_status=status,
                    new_status=_EDIT_TRANSITIONS[status],
                ))

    return changes


def apply_transitions(config: SddConfig, changes: list[StatusChange]) -> None:
    """Patcht Frontmatter-Status, schreibt Audit-Log und aktualisiert Hashes."""
    if not changes:
        return
    hashes = load_hashes(config)
    for change in changes:
        patch_status(change.path, change.new_status)
        write_audit_log(
            config, change.artifact_id,
            change.old_status, change.new_status,
            "content-change-detected",
        )
        hashes[change.artifact_id] = compute_content_hash(
            change.path.read_text(encoding="utf-8")
        )
    save_hashes(config, hashes)


# ─────────────────────────────────────────────────────────────────────────────
# Pending-Contracts
# ─────────────────────────────────────────────────────────────────────────────

def pending_contracts(config: SddConfig) -> list[Document]:
    """Contracts mit Status review ohne verknüpften Test."""
    result: list[Document] = []
    if not config.contracts_dir.exists():
        return result
    for md in sorted(config.contracts_dir.rglob("*.md")):
        doc = parse_safe(md)
        if not doc or not doc.frontmatter:
            continue
        if doc.frontmatter.get("status") != "review":
            continue
        if not (doc.frontmatter.get("tests") or []):
            result.append(doc)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# LLM Contract-Review
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ContractReviewResult:
    tst_id: str
    tst_path: Path
    llm_verdict: str  # "approved" | "needs_revision"
    notes: str


def review_contract(config: SddConfig, con_id: str) -> ContractReviewResult:
    """LLM-Review für einen Contract.

    1. Sendet Contract + Referenz-Spec an LLM (via SPEC-0008-Provider)
    2. Speichert TST-Datei mit Status draft und generated_by: llm
    3. Verknüpft TST-ID im Contract-Frontmatter
    4. Bei needs_revision: LLM-Notizen am Contract-Ende anhängen
    """
    from .ids import next_id
    from .llm.factory import get_completion_provider
    from .templates import load_template, render, slugify

    contract_doc = _find_doc_by_id(config.contracts_dir, con_id)
    if contract_doc is None:
        raise ValueError(f"Contract nicht gefunden: {con_id}")

    spec_id = contract_doc.frontmatter.get("spec", "")
    spec_text = ""
    if spec_id:
        spec_doc = _find_doc_by_id(config.specs_dir, spec_id)
        if spec_doc:
            spec_text = spec_doc.path.read_text(encoding="utf-8")

    contract_text = contract_doc.path.read_text(encoding="utf-8")
    prompt = _build_review_prompt(contract_text, spec_text)

    provider = get_completion_provider(config, "completion")
    import time as _time
    _t0 = _time.monotonic()
    result = provider.complete(prompt, max_tokens=2048)
    _duration_ms = int((_time.monotonic() - _t0) * 1000)

    if result.usage:
        from .estimation import persist_token_usage
        persist_token_usage(
            config,
            component="review-contract",
            model=result.usage.model or "",
            input_tokens=result.usage.input_tokens,
            output_tokens=result.usage.output_tokens,
            cache_read_tokens=result.usage.cache_read_tokens,
            cache_write_tokens=result.usage.cache_creation_tokens,
            duration_ms=_duration_ms,
            spec_id=spec_id or None,
        )

    verdict, notes, test_suggestion = _parse_review_output(result.text)

    tst_id = next_id(config, "test")
    slug = slugify(contract_doc.frontmatter.get("title", con_id))
    tst_path = config.tests_dir / "contract" / f"{tst_id}-llm-{slug}.md"
    tst_path.parent.mkdir(parents=True, exist_ok=True)

    tmpl, _ = load_template(config, "test")
    tst_text = render(tmpl, {
        "id": tst_id,
        "title": f"LLM-Review: {contract_doc.frontmatter.get('title', con_id)}",
        "spec": spec_id,
        "contract": con_id,
    })
    tst_text = re.sub(
        r"^status:\s*\S+.*?$", "status: draft", tst_text, count=1, flags=re.MULTILINE
    )
    tst_text = _inject_generated_by(tst_text)
    if test_suggestion:
        tst_text += f"\n## Generierter Testvorschlag\n\n{test_suggestion}\n"
    tst_path.write_text(tst_text, encoding="utf-8")

    if spec_id:
        try:
            from .regression_check import RegressionCheckChain
            from .gate import ExecutionGate
            chain = RegressionCheckChain(config.root)
            rc_result = chain.run(spec_id, provider=None)
            if not any(f.severity == "error" for f in rc_result.findings):
                gate = ExecutionGate(config.root)
                gate.mark_phase_complete(spec_id, "regression-ok")
        except Exception:
            pass

    _link_test_in_contract(contract_doc.path, tst_id)

    if verdict == "needs_revision" and notes:
        with contract_doc.path.open("a", encoding="utf-8") as fh:
            fh.write(f"\n## LLM Review Notes\n\n{notes}\n")

    return ContractReviewResult(
        tst_id=tst_id,
        tst_path=tst_path,
        llm_verdict=verdict,
        notes=notes,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Interne Hilfsfunktionen
# ─────────────────────────────────────────────────────────────────────────────

def _find_doc_by_id(base_dir: Path, artifact_id: str) -> Document | None:
    if not base_dir.exists():
        return None
    for md in base_dir.rglob("*.md"):
        doc = parse_safe(md)
        if doc and doc.frontmatter.get("id") == artifact_id:
            return doc
    return None


def _inject_generated_by(tst_text: str) -> str:
    """Fügt generated_by: llm nach der ersten status:-Zeile (Frontmatter) ein."""
    return re.sub(
        r"^(status:\s*\S[^\n]*)$",
        r"\1\ngenerated_by: llm",
        tst_text,
        count=1,
        flags=re.MULTILINE,
    )


def _link_test_in_contract(contract_path: Path, tst_id: str) -> None:
    """Ersetzt tests: [] im Contract durch tests: ["TST-XXXX"]."""
    text = contract_path.read_text(encoding="utf-8")
    if "tests: []" in text:
        contract_path.write_text(
            text.replace("tests: []", f'tests: ["{tst_id}"]', 1),
            encoding="utf-8",
        )


def _build_review_prompt(contract_text: str, spec_text: str) -> str:
    spec_section = f"\n\n## Referenz-Spec\n\n{spec_text}" if spec_text else ""
    return (
        "Du bist ein SDD-Contract-Reviewer. Analysiere den folgenden Contract und:\n\n"
        "1. Prüfe Vollständigkeit und Konsistenz des Contracts\n"
        "2. Generiere mindestens ein konkretes Test-Szenario "
        "(Gherkin-Szenario oder pytest-Gerüst)\n"
        "3. Bewerte: `approved` (Contract klar und vollständig) oder "
        "`needs_revision` mit Begründung\n\n"
        "Antworte exakt in diesem Format:\n\n"
        "VERDICT: approved|needs_revision\n"
        "NOTES: <Begründung bei needs_revision, sonst leer>\n"
        "TEST_SUGGESTION:\n"
        "<Test-Code oder Gherkin-Szenario>\n\n"
        f"## Contract\n\n{contract_text}{spec_section}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# SPEC-0019: TDD-Implementierungsphase – start_spec()
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class StartResult:
    spec_id: str
    spec_path: Path
    stubs_created: list[Path]
    stubs_skipped: list[Path]
    tst_ids: list[str]


def start_spec(config: SddConfig, spec_id: str) -> StartResult:
    """Setzt Spec-Status auf in-progress und generiert Test-Stubs (SPEC-0019).

    Vorbedingung: status == approved. Illegale Übergänge werfen ValueError.
    """
    spec_doc = _find_doc_by_id(config.specs_dir, spec_id)
    if spec_doc is None:
        raise ValueError(f"Spec nicht gefunden: {spec_id}")

    current_status = spec_doc.frontmatter.get("status", "")
    if current_status == "in-progress":
        raise ValueError(f"[INFO] {spec_id} ist bereits in-progress.")
    if current_status != "approved":
        raise ValueError(
            f"{spec_id} hat Status '{current_status}' – erst Execution Gate durchlaufen "
            f"(sdd spec approve {spec_id})."
        )

    now = datetime.now(timezone.utc)
    spec_doc.frontmatter["status"] = "in-progress"
    spec_doc.frontmatter["started_at"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    spec_doc.frontmatter["updated"] = now.strftime("%Y-%m-%d")
    spec_doc.write()

    write_audit_log(config, spec_id, "approved", "in-progress", "sdd-start")

    tst_ids: list[str] = spec_doc.frontmatter.get("tests") or []
    stubs_created: list[Path] = []
    stubs_skipped: list[Path] = []

    for tst_id in tst_ids:
        tst_doc = _find_tst_doc(config, tst_id)
        stub_path = _derive_stub_path(config, tst_id, tst_doc)
        if stub_path is None:
            continue
        if stub_path.exists():
            stubs_skipped.append(stub_path)
        else:
            stub_path.parent.mkdir(parents=True, exist_ok=True)
            stub_path.write_text(_render_stub(tst_id, tst_doc, spec_id), encoding="utf-8")
            stubs_created.append(stub_path)

    return StartResult(
        spec_id=spec_id,
        spec_path=spec_doc.path,
        stubs_created=stubs_created,
        stubs_skipped=stubs_skipped,
        tst_ids=list(tst_ids),
    )


def mark_evaluation_failed(config: SddConfig, spec_id: str, report_path: Path) -> None:
    """Setzt SPEC-Status auf evaluation-failed und schreibt Audit-Log."""
    spec_doc = _find_doc_by_id(config.specs_dir, spec_id)
    if spec_doc is None:
        raise ValueError(f"Spec nicht gefunden: {spec_id}")
    old_status = spec_doc.frontmatter.get("status", "unknown")
    now = datetime.now(timezone.utc)
    spec_doc.frontmatter["status"] = "evaluation-failed"
    spec_doc.frontmatter["updated"] = now.strftime("%Y-%m-%d")
    spec_doc.frontmatter["evaluation_failed_at"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    spec_doc.frontmatter["evaluation_report"] = str(report_path)
    spec_doc.write()
    write_audit_log(config, spec_id, old_status, "evaluation-failed", "sdd-evaluate")


def get_in_progress_specs(config: SddConfig) -> list[Document]:
    """Gibt alle Specs mit status: in-progress zurück (SPEC-0019 FR-08)."""
    result: list[Document] = []
    if not config.specs_dir.exists():
        return result
    for md in sorted(config.specs_dir.rglob("*.md")):
        doc = parse_safe(md)
        if doc and doc.frontmatter.get("status") == "in-progress":
            result.append(doc)
    return result


def _find_tst_doc(config: SddConfig, tst_id: str) -> "Document | None":
    tests_root = config.root / "tests"
    if not tests_root.exists():
        return None
    for md in tests_root.rglob("*.md"):
        doc = parse_safe(md)
        if doc and doc.frontmatter.get("id") == tst_id:
            return doc
    return None


def _derive_stub_path(config: SddConfig, tst_id: str, tst_doc: "Document | None") -> "Path | None":
    tests_root = config.root / "tests"
    if tst_doc is not None:
        artifact = tst_doc.frontmatter.get("artifact")
        if artifact:
            return config.root / artifact
        level = tst_doc.frontmatter.get("level", "unit")
    else:
        level = "unit"
    slug = tst_id.lower().replace("-", "_")
    return tests_root / level / f"test_{slug}.py"


def _render_stub(tst_id: str, tst_doc: "Document | None", spec_id: str) -> str:
    title = ""
    contract = ""
    level = "unit"
    if tst_doc is not None:
        title = tst_doc.frontmatter.get("title", "")
        contract = tst_doc.frontmatter.get("contract", "")
        level = tst_doc.frontmatter.get("level", "unit")

    header = [f"# {tst_id}" + (f" – {title}" if title else "")]
    header.append(f"# Spec: {spec_id}")
    if contract:
        header.append(f"# Contract: {contract}")
    header.append("# Generiert von 'sdd start' – TODO: implementieren (SPEC-0019)")

    class_name = "Test" + tst_id.replace("-", "")
    body = [
        "",
        "import pytest",
        "",
        "",
        f"class {class_name}:",
        f"    # Level: {level}",
        "    def test_placeholder(self) -> None:",
        "        # TODO: Konkreten Test implementieren",
        "        raise NotImplementedError",
    ]
    return "\n".join(header + body) + "\n"


def _parse_review_output(text: str) -> tuple[str, str, str]:
    """Parst LLM-Antwort: (verdict, notes, test_suggestion)."""
    verdict = "needs_revision"
    notes = ""
    test_suggestion = text

    m = re.search(r"VERDICT:\s*(approved|needs_revision)", text, re.IGNORECASE)
    if m:
        verdict = m.group(1).lower()

    m = re.search(r"NOTES:\s*(.+?)(?=\nTEST_SUGGESTION:|$)", text, re.DOTALL)
    if m:
        notes = m.group(1).strip()

    m = re.search(r"TEST_SUGGESTION:\s*\n(.*)", text, re.DOTALL)
    if m:
        test_suggestion = m.group(1).strip()

    return verdict, notes, test_suggestion
