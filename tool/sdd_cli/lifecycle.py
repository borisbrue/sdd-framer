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
from dataclasses import dataclass, field
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
    llm_verdict: str  # "approved" | "needs_revision"
    notes: str


def review_contract(config: SddConfig, con_id: str) -> ContractReviewResult:
    """LLM-Review für einen Contract (CON-0170 / SPEC-0044 FR-07).

    Prüft Vollständigkeit, SOLID-Konformität und Klarheit.
    Setzt status auf approved bei positivem Ergebnis.
    Legt KEINE TST-Datei an — Verantwortlichkeit liegt bei sdd test generate.
    """
    from .llm.factory import get_completion_provider

    contract_doc = _find_doc_by_id(config.contracts_dir, con_id)
    if contract_doc is None:
        raise ValueError(f"Contract nicht gefunden: {con_id}")

    spec_id = contract_doc.frontmatter.get("spec", "")
    spec_text = ""
    if spec_id:
        spec_doc = _find_doc_by_id(config.specs_dir, spec_id)
        if spec_doc:
            spec_text = spec_doc.path.read_text(encoding="utf-8")

    # Alte Review-Notizen gehoeren nicht in den Prompt: das naechste Review las
    # sie als Teil des Contracts und wertete veraltete Punkte als Blocker (#140).
    contract_text = _ohne_review_notes(contract_doc.path.read_text(encoding="utf-8"))
    artifact_rel = contract_doc.frontmatter.get("artifact", "")
    artifact_text = ""
    if artifact_rel and "<" not in artifact_rel:
        artifact_path = config.root / artifact_rel
        if artifact_path.exists():
            artifact_text = artifact_path.read_text(encoding="utf-8")
    prompt = _build_review_prompt(contract_text, spec_text, artifact_text)

    from .llm.usage import usage_context

    provider = get_completion_provider(config, "completion")
    # Die Factory erfasst den Aufruf (SPEC-0060 FR-06); hier nur der Kontext.
    with usage_context(spec_id=spec_id or None, operation="review-contract"):
        result = provider.complete(prompt, max_tokens=6144)

    verdict, notes, _ = _parse_review_output(result.text)

    if spec_id:
        try:
            from .gate import ExecutionGate
            from .regression_check import RegressionCheckChain
            chain = RegressionCheckChain(config.root)
            rc_result = chain.run(spec_id, provider=None)
            if not any(f.severity == "error" for f in rc_result.findings):
                gate = ExecutionGate(config.root)
                gate.mark_phase_complete(spec_id, "regression-ok")
        except Exception:
            pass

    # Ein Block statt einer wachsenden Historie: jede Runde haengte bisher einen
    # weiteren "## LLM Review Notes"-Abschnitt an (#140). FR-07 bleibt erfuellt.
    if verdict == "needs_revision" and notes:
        _schreibe_review_notes(contract_doc.path, notes)
    elif verdict == "approved":
        _schreibe_review_notes(contract_doc.path, None)
        # SPEC-0044 FR-07 und CON-0170 G-01 verlangen beides: die TST-Anlage
        # entfernen UND den Status setzen. Gebaut war nur die entfernende
        # Haelfte — der Docstring sagte die zweite zu, der Code loeste sie nie
        # ein. Ein Contract kam nie aus `review` heraus, und `sdd test generate`
        # arbeitet auf approved Contracts: die Kette brach genau dort (#104).
        from .frontmatter import patch_status
        patch_status(contract_doc.path, "approved")

    return ContractReviewResult(
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


_REVIEW_NOTES = re.compile(r"^## LLM Review Notes[ \t]*$", re.MULTILINE)


def _ohne_review_notes(text: str) -> str:
    """Contract-Text ohne den Review-Block (ab der ersten Ueberschrift bis Dateiende).

    Der Block steht laut FR-07 am Ende; die Notizen selbst enthalten oft eigene
    ##-Ueberschriften, deshalb endet er nicht an der naechsten Ueberschrift.
    """
    m = _REVIEW_NOTES.search(text)
    return text if m is None else text[: m.start()].rstrip("\n") + "\n"


def _schreibe_review_notes(contract_path: Path, notes: str | None) -> None:
    """Ersetzt den Review-Block; notes=None entfernt ihn."""
    original = contract_path.read_text(encoding="utf-8")
    text = _ohne_review_notes(original)
    if notes:
        text += f"\n## LLM Review Notes\n\n{notes}\n"
    if text != original:
        contract_path.write_text(text, encoding="utf-8")


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


def _build_review_prompt(
    contract_text: str,
    spec_text: str,
    artifact_text: str = "",
) -> str:
    spec_section = f"\n\n## Referenz-Spec\n\n{spec_text}" if spec_text else ""
    artifact_section = f"\n\n## Artifact\n\n{artifact_text}" if artifact_text else ""
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
        f"## Contract\n\n{contract_text}{artifact_section}{spec_section}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# SPEC-0019: TDD-Implementierungsphase – start_spec()
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class StubOutcome:
    """Ergebnis der LLM-Generierung fuer genau einen Test-Stub."""
    path: Path
    tst_id: str
    generated: bool
    reason: str = ""   # gefuellt, wenn generated False ist


@dataclass
class StartResult:
    spec_id: str
    spec_path: Path
    stubs_created: list[Path]
    stubs_skipped: list[Path]
    tst_ids: list[str]
    # False, wenn die Spec schon in-progress war. Der Aufrufer soll trotzdem
    # weitermachen: der Container fehlt womoeglich, und genau dafuer ruft man
    # `sdd start` erneut auf.
    status_changed: bool = True
    # Ohne diese Aufschluesselung war nicht erkennbar, welche Datei tatsaechlich
    # generiert wurde und welche als Platzhalter mit `raise NotImplementedError`
    # liegenblieb — beide standen unter "Test-Stubs angelegt".
    stub_outcomes: list[StubOutcome] = field(default_factory=list)
    # Test-Dateien, fuer die kein Stub angelegt wurde, weil Platzhalter und
    # Generierung nur pytest koennen (#141: `import pytest` in .rs-Dateien).
    stubs_unsupported: list[Path] = field(default_factory=list)

    @property
    def stubs_generated(self) -> list[Path]:
        return [o.path for o in self.stub_outcomes if o.generated]

    @property
    def stubs_placeholder(self) -> list[StubOutcome]:
        return [o for o in self.stub_outcomes if not o.generated]


def start_spec(config: SddConfig, spec_id: str) -> StartResult:
    """Setzt Spec-Status auf in-progress und generiert Test-Stubs (SPEC-0019).

    Vorbedingung: status == approved. Illegale Übergänge werfen ValueError.
    """
    spec_doc = _find_doc_by_id(config.specs_dir, spec_id)
    if spec_doc is None:
        raise ValueError(f"Spec nicht gefunden: {spec_id}")

    current_status = spec_doc.frontmatter.get("status", "")
    # in-progress ist kein Fehler: `sdd finalize` entfernt den Container, bevor
    # es scheitern kann, und verwies danach auf `sdd start` — das aber
    # kommentarlos zurueckkehrte, weil der Status schon stand. Der einzige
    # Ausweg war, den Container von Hand nachzubauen.
    bereits_gestartet = current_status == "in-progress"
    if not bereits_gestartet and current_status != "approved":
        raise ValueError(
            f"{spec_id} hat Status '{current_status}' – erst Execution Gate durchlaufen "
            f"(sdd spec approve {spec_id})."
        )

    if not bereits_gestartet:
        now = datetime.now(timezone.utc)
        spec_doc.frontmatter["status"] = "in-progress"
        spec_doc.frontmatter["started_at"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        spec_doc.frontmatter["updated"] = now.strftime("%Y-%m-%d")
        spec_doc.write()

        write_audit_log(config, spec_id, "approved", "in-progress", "sdd-start")

    tst_ids: list[str] = spec_doc.frontmatter.get("tests") or []
    stubs_created: list[Path] = []
    stubs_skipped: list[Path] = []
    stub_outcomes: list[StubOutcome] = []
    stubs_unsupported: list[Path] = []

    for tst_id in tst_ids:
        tst_doc = _find_tst_doc(config, tst_id)
        stub_path = _derive_stub_path(config, tst_id, tst_doc)
        if stub_path is None:
            continue
        if stub_path.suffix != ".py":
            # Weder Datei noch Verzeichnis anlegen: ein pytest-Modul in einer
            # .rs-Datei bricht `cargo test` ab (#141).
            stubs_unsupported.append(stub_path)
        elif stub_path.exists():
            stubs_skipped.append(stub_path)
        else:
            stub_path.parent.mkdir(parents=True, exist_ok=True)
            stub_path.write_text(_render_stub(tst_id, tst_doc, spec_id), encoding="utf-8")
            stubs_created.append(stub_path)
            ok, reason = _implement_test_stub(
                config, tst_id, tst_doc, stub_path, spec_body=spec_doc.body or ""
            )
            stub_outcomes.append(StubOutcome(
                path=stub_path, tst_id=tst_id, generated=ok, reason=reason))

    return StartResult(
        spec_id=spec_id,
        spec_path=spec_doc.path,
        stubs_created=stubs_created,
        stubs_skipped=stubs_skipped,
        tst_ids=list(tst_ids),
        stub_outcomes=stub_outcomes,
        status_changed=not bereits_gestartet,
        stubs_unsupported=stubs_unsupported,
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


def _find_tst_doc(config: SddConfig, tst_id: str) -> Document | None:
    for base in config.all_test_dirs:
        for md in base.rglob("*.md"):
            doc = parse_safe(md)
            if doc and doc.frontmatter.get("id") == tst_id:
                return doc
    return None


def _derive_stub_path(config: SddConfig, tst_id: str, tst_doc: Document | None) -> Path | None:
    if tst_doc is not None:
        artifact = tst_doc.frontmatter.get("artifact", "")
        # Skip template placeholders like "tests/<level>/<name>.test.<ext>"
        if artifact and "<" not in artifact:
            return config.root / artifact
        level = tst_doc.frontmatter.get("level", "unit")
    else:
        level = "unit"
    slug = tst_id.lower().replace("-", "_")
    return config.project_tests_dir / level / f"test_{slug}.py"


def _read_contract_for_tst(config: SddConfig, contract_id: str) -> tuple[str, str, str, str]:
    """Returns (title, format, artifact_content, artifact_rel) for a contract ID."""
    if not contract_id:
        return "", "", "", ""
    doc = _find_doc_by_id(config.contracts_dir, contract_id)
    if doc is None:
        return "", "", "", ""
    title = doc.frontmatter.get("title", "")
    fmt = doc.frontmatter.get("format", "")
    artifact_rel = doc.frontmatter.get("artifact", "")
    content = ""
    if artifact_rel:
        p = config.root / artifact_rel
        if p.exists():
            content = p.read_text(encoding="utf-8")
    return title, fmt, content, artifact_rel


def _build_implement_test_prompt(
    tst_id: str,
    title: str,
    level: str,
    contract_id: str,
    con_title: str,
    con_fmt: str,
    tst_body: str,
    artifact_content: str,
    artifact_rel: str,
    spec_body: str,
    class_name: str,
    stub_path: Path,
) -> str:
    artifact_section = ""
    if artifact_content:
        artifact_section = (
            f"\n**Contract-Artefakt** (`{artifact_rel}`):\n"
            f"{artifact_content[:3000]}\n"
        )
    spec_section = f"\n**Spec-Kontext:**\n{spec_body[:600]}\n" if spec_body else ""
    return (
        f"Schreibe ein ausführbares pytest-Modul für folgenden SDD-Test.\n\n"
        f"**Test-ID:** {tst_id}\n"
        f"**Titel:** {title}\n"
        f"**Level:** {level}\n"
        f"**Contract:** {contract_id} – {con_title} (Format: {con_fmt})\n"
        f"**Ausgabe-Datei:** {stub_path.name}\n\n"
        f"**Testbeschreibung:**\n{tst_body}\n"
        f"{artifact_section}{spec_section}\n"
        "**Anforderungen:**\n"
        "- Nur valider Python-Code, KEINE Markdown-Fences, keine Prosa\n"
        "- Verfügbare Imports: pathlib, pytest, yaml, jsonschema (alle installiert)\n"
        f"- Testklasse: `{class_name}` mit Methoden die `test_` beginnen\n"
        "- KEIN pytest.skip(), KEIN raise NotImplementedError — alle Tests sollen laufen\n"
        "- Kein Netzwerkzugriff: Mocks, In-Memory-Objekte oder statische Dateivalidierung\n"
        f"- Contract-Artefakt liegt unter: `{artifact_rel}` (Pfad relativ zu Repo-Root)\n"
        "- Pfad zu Repo-Root aus Testdatei: `Path(__file__).resolve().parents[2]`\n"
    )


def _implement_test_stub(
    config: SddConfig,
    tst_id: str,
    tst_doc: Document | None,
    stub_path: Path,
    spec_body: str = "",
) -> tuple[bool, str]:
    """Generiert pytest-Code via LLM. Gibt (erfolg, grund) zurueck.

    `grund` ist bei Misserfolg gefuellt und wandert bis in die CLI-Ausgabe.
    Vorher gab die Funktion nur bool zurueck, und der Aufrufer verwarf ihn —
    ein fehlgeschlagener Lauf war von einem erfolgreichen nicht zu unterscheiden.
    """
    if tst_doc is None:
        return False, f"Kein Test-Dokument zu {tst_id} gefunden"
    try:
        from .llm.factory import get_completion_provider
    except ImportError as exc:
        return False, f"LLM-Provider nicht ladbar: {exc}"

    title = tst_doc.frontmatter.get("title", "")
    level = tst_doc.frontmatter.get("level", "unit")
    contract_id = tst_doc.frontmatter.get("contract", "")
    tst_body = (tst_doc.body or "").strip()
    class_name = "Test" + tst_id.replace("-", "")

    con_title, con_fmt, artifact_content, artifact_rel = _read_contract_for_tst(
        config, contract_id
    )
    prompt = _build_implement_test_prompt(
        tst_id=tst_id, title=title, level=level,
        contract_id=contract_id, con_title=con_title, con_fmt=con_fmt,
        tst_body=tst_body, artifact_content=artifact_content,
        artifact_rel=artifact_rel, spec_body=spec_body,
        class_name=class_name, stub_path=stub_path,
    )
    system_prompt = (
        "You are an expert Python test engineer for Spec-Driven Development. "
        "Output ONLY valid Python code — no markdown fences, no prose, no explanations."
    )
    # Der Wert stand hart im Code. Mit dem claude-cli-Provider ist er bei
    # umfangreichen Test-Dokumenten knapp — genau dort schlug die Generierung
    # im gemeldeten Fall fehl.
    timeout = int((config.raw.get("llm") or {}).get("test_generation_timeout", 300))
    try:
        provider = get_completion_provider(config, "completion")
        result = provider.complete(prompt, max_tokens=4096,
                                   system_prompt=system_prompt, timeout=timeout)
        code = result.text.strip()
        if code.startswith("```"):
            lines = code.splitlines()
            end = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
            code = "\n".join(lines[1:end])
        if "import pytest" in code and "def test_" in code:
            stub_path.write_text(code, encoding="utf-8")
            return True, ""
        # Antwort kam an, taugt aber nicht. Vorher kommentarlos False.
        return False, (
            f"LLM-Antwort enthaelt keinen pytest-Code "
            f"({len(code)} Zeichen, erwartet 'import pytest' und 'def test_')"
        )
    except Exception as exc:
        # Vorher `except Exception: pass` — das verbarg genau die Information,
        # die man zur Diagnose braucht (Timeout, Providerfehler, Netzwerk).
        return False, f"{type(exc).__name__}: {exc}"


def _render_stub(tst_id: str, tst_doc: Document | None, spec_id: str) -> str:
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
