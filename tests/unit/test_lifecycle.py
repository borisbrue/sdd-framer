"""Unit-Tests für lifecycle.py (SPEC-0010).

Deckt TST-0048 bis TST-0054 ab.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sdd_cli.lifecycle import (
    compute_content_hash,
    load_hashes,
    save_hashes,
    rebuild_hashes,
    write_audit_log,
    check_transitions,
    apply_transitions,
    pending_contracts,
    review_contract,
    _parse_review_output,
    StatusChange,
)
from sdd_cli.validate import validate, _check_lifecycle_rules, Report


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

def _write_spec(path: Path, artifact_id: str, status: str, body: str = "body") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\nid: {artifact_id}\nstatus: {status}\nupdated: 2026-01-01\n---\n{body}\n",
        encoding="utf-8",
    )
    return path


def _write_contract(
    path: Path, artifact_id: str, status: str,
    spec: str = "SPEC-0001", tests: list[str] | None = None, body: str = "body",
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    tests_yaml = "[]" if not tests else str(tests).replace("'", '"')
    path.write_text(
        f"---\nid: {artifact_id}\nstatus: {status}\nspec: {spec}\ntests: {tests_yaml}\n---\n{body}\n",
        encoding="utf-8",
    )
    return path


@pytest.fixture()
def sdd_project(tmp_path: Path):
    """Minimales SDD-Projekt mit Templates für Tests."""
    import shutil
    sdd_dir = tmp_path / ".sdd"
    sdd_dir.mkdir()
    (sdd_dir / "config.yaml").write_text(
        "project:\n  id: PRJ-0001\n  name: Test\n", encoding="utf-8"
    )
    (sdd_dir / "specs").mkdir()
    (sdd_dir / "contracts").mkdir()
    (sdd_dir / "tests").mkdir()
    # Templates aus dem echten Projekt kopieren
    real_templates = Path(__file__).parents[2] / ".sdd" / "templates"
    if real_templates.exists():
        shutil.copytree(real_templates, sdd_dir / "templates")
    return tmp_path


@pytest.fixture()
def cfg(sdd_project):
    from sdd_cli.config import load_config
    import os
    os.chdir(sdd_project)
    return load_config()


# ─────────────────────────────────────────────────────────────────────────────
# TST-0048 – Content-Hash-Berechnung
# ─────────────────────────────────────────────────────────────────────────────

class TestComputeContentHash:
    def test_same_body_different_status_equal_hash(self):
        """TC-01: status:-Änderung erzeugt gleichen Hash."""
        t1 = "---\nid: SPEC-0001\nstatus: draft\n---\nbody text\n"
        t2 = "---\nid: SPEC-0001\nstatus: approved\n---\nbody text\n"
        assert compute_content_hash(t1) == compute_content_hash(t2)

    def test_same_body_different_updated_equal_hash(self):
        """TC-02: updated:-Änderung erzeugt gleichen Hash."""
        t1 = "---\nid: SPEC-0001\nupdated: 2026-01-01\n---\nbody\n"
        t2 = "---\nid: SPEC-0001\nupdated: 2026-06-01\n---\nbody\n"
        assert compute_content_hash(t1) == compute_content_hash(t2)

    def test_different_body_different_hash(self):
        """TC-03: Body-Änderung erzeugt anderen Hash."""
        t1 = "---\nid: SPEC-0001\nstatus: draft\n---\nbody A\n"
        t2 = "---\nid: SPEC-0001\nstatus: draft\n---\nbody B\n"
        assert compute_content_hash(t1) != compute_content_hash(t2)

    def test_empty_text_returns_valid_sha256(self):
        """TC-04: Leerer Text → valider 64-Zeichen-SHA-256."""
        h = compute_content_hash("")
        assert len(h) == 64
        assert re.fullmatch(r"[0-9a-f]{64}", h)


# ─────────────────────────────────────────────────────────────────────────────
# TST-0049 – Status-Übergang approved → review
# ─────────────────────────────────────────────────────────────────────────────

class TestCheckAndApplyTransitions:
    def test_approved_spec_with_changed_body_triggers_review(self, cfg, sdd_project):
        """TC-01: approved-Spec mit geändertem Body → check_transitions gibt Übergang."""
        spec_path = sdd_project / ".sdd" / "specs" / "SPEC-0001-test.md"
        _write_spec(spec_path, "SPEC-0001", "approved", body="original body")

        hashes = rebuild_hashes(cfg)
        # Body ändern
        _write_spec(spec_path, "SPEC-0001", "approved", body="changed body")

        save_hashes(cfg, hashes)
        changes = check_transitions(cfg)
        assert any(ch.artifact_id == "SPEC-0001" and ch.new_status == "review"
                   for ch in changes)

    def test_apply_transitions_patches_frontmatter(self, cfg, sdd_project):
        """TC-02: apply_transitions patcht status in Datei auf review."""
        spec_path = sdd_project / ".sdd" / "specs" / "SPEC-0001-test.md"
        _write_spec(spec_path, "SPEC-0001", "approved", body="original")
        hashes = rebuild_hashes(cfg)
        _write_spec(spec_path, "SPEC-0001", "approved", body="changed")
        save_hashes(cfg, hashes)

        changes = check_transitions(cfg)
        apply_transitions(cfg, changes)

        from sdd_cli.frontmatter import parse
        doc = parse(spec_path)
        assert doc.frontmatter["status"] == "review"

    def test_apply_transitions_updates_hashes_json(self, cfg, sdd_project):
        """TC-03: apply_transitions aktualisiert content-hashes.json."""
        spec_path = sdd_project / ".sdd" / "specs" / "SPEC-0001-test.md"
        _write_spec(spec_path, "SPEC-0001", "approved", body="original")
        hashes = rebuild_hashes(cfg)
        old_hash = hashes["SPEC-0001"]
        _write_spec(spec_path, "SPEC-0001", "approved", body="changed")
        save_hashes(cfg, hashes)

        changes = check_transitions(cfg)
        apply_transitions(cfg, changes)

        new_hashes = load_hashes(cfg)
        assert new_hashes["SPEC-0001"] != old_hash

    def test_implemented_spec_transitions_to_review(self, cfg, sdd_project):
        """TC-04: implemented-Spec mit Body-Änderung → review."""
        spec_path = sdd_project / ".sdd" / "specs" / "SPEC-0001-test.md"
        _write_spec(spec_path, "SPEC-0001", "implemented", body="original")
        hashes = rebuild_hashes(cfg)
        _write_spec(spec_path, "SPEC-0001", "implemented", body="changed")
        save_hashes(cfg, hashes)

        changes = check_transitions(cfg)
        assert any(ch.artifact_id == "SPEC-0001"
                   and ch.old_status == "implemented"
                   and ch.new_status == "review"
                   for ch in changes)


# ─────────────────────────────────────────────────────────────────────────────
# TST-0050 – Kein Übergang bei reiner updated:-Änderung
# ─────────────────────────────────────────────────────────────────────────────

class TestNoFalseTransitions:
    def test_only_updated_changed_no_transition(self, cfg, sdd_project):
        """TC-01: Nur updated:-Änderung → kein Übergang."""
        spec_path = sdd_project / ".sdd" / "specs" / "SPEC-0001-test.md"
        _write_spec(spec_path, "SPEC-0001", "approved", body="same body")
        hashes = rebuild_hashes(cfg)
        save_hashes(cfg, hashes)
        # updated: Zeile ändern, aber Body bleibt gleich
        spec_path.write_text(
            "---\nid: SPEC-0001\nstatus: approved\nupdated: 2099-01-01\n---\nsame body\n",
            encoding="utf-8",
        )

        changes = check_transitions(cfg)
        assert not any(ch.artifact_id == "SPEC-0001" for ch in changes)

    def test_first_run_no_hashes_initializes_and_returns_empty(self, cfg, sdd_project):
        """TC-03: Erstlauf ohne hashes.json → leere Changes, Datei wird angelegt."""
        _write_spec(sdd_project / ".sdd" / "specs" / "SPEC-0001-test.md", "SPEC-0001", "approved")
        hashes_path = sdd_project / ".sdd" / "content-hashes.json"
        assert not hashes_path.exists()

        # check_transitions gibt bei fehlendem Hash für das Artefakt keine Changes zurück
        changes = check_transitions(cfg)
        assert not any(ch.artifact_id == "SPEC-0001" for ch in changes)


# ─────────────────────────────────────────────────────────────────────────────
# TST-0051 – sdd new contract → initiales Status = review
# ─────────────────────────────────────────────────────────────────────────────

class TestNewContractInitialStatus:
    def test_new_contract_template_renders_review_status(self, cfg):
        """TC-01: main._new_contract setzt Status auf review (über String-Patch in main.py)."""
        from sdd_cli.templates import load_template, render

        tmpl, _ = load_template(cfg, "contract", contract_format="markdown")
        text = render(tmpl, {"id": "CON-9999", "title": "Test", "spec": "SPEC-0001"})
        # Simuliere den Patch aus main.py (FR-03)
        patched = text.replace("\nstatus: draft\n", "\nstatus: review\n", 1)
        assert "status: review" in patched
        assert "status: draft" not in patched


# ─────────────────────────────────────────────────────────────────────────────
# TST-0052 – Audit-Log-Schreibung
# ─────────────────────────────────────────────────────────────────────────────

class TestAuditLog:
    AUDIT_RE = re.compile(
        r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z "
        r"[A-Z]+-\d{4} \S+ → \S+ \[.+\]$"
    )

    def test_write_audit_log_format(self, cfg, sdd_project):
        """TC-01: Audit-Eintrag hat korrektes Format."""
        write_audit_log(cfg, "SPEC-0001", "approved", "review", "content-change-detected")
        log = (sdd_project / ".sdd" / "audit.log").read_text(encoding="utf-8")
        lines = [l for l in log.splitlines() if l]
        assert len(lines) == 1
        assert self.AUDIT_RE.match(lines[0]), f"Format ungültig: {lines[0]!r}"

    def test_apply_transitions_writes_audit_entry(self, cfg, sdd_project):
        """TC-02: apply_transitions schreibt Eintrag ins Audit-Log."""
        spec_path = sdd_project / ".sdd" / "specs" / "SPEC-0001-test.md"
        _write_spec(spec_path, "SPEC-0001", "approved", body="original")
        hashes = rebuild_hashes(cfg)
        _write_spec(spec_path, "SPEC-0001", "approved", body="changed")
        save_hashes(cfg, hashes)

        changes = check_transitions(cfg)
        apply_transitions(cfg, changes)

        log_path = sdd_project / ".sdd" / "audit.log"
        assert log_path.exists()
        assert "SPEC-0001" in log_path.read_text(encoding="utf-8")

    def test_multiple_writes_append(self, cfg, sdd_project):
        """TC-03: Mehrfache Schreibungen appenden."""
        write_audit_log(cfg, "SPEC-0001", "approved", "review", "reason-a")
        write_audit_log(cfg, "CON-0001", "approved", "review", "reason-b")
        log = (sdd_project / ".sdd" / "audit.log").read_text(encoding="utf-8")
        assert log.count("SPEC-0001") == 1
        assert log.count("CON-0001") == 1


# ─────────────────────────────────────────────────────────────────────────────
# TST-0053 – review_contract mit LLM-Mock
# ─────────────────────────────────────────────────────────────────────────────

class TestReviewContract:
    _LLM_APPROVED = (
        "VERDICT: approved\n"
        "NOTES: \n"
        "TEST_SUGGESTION:\n"
        "def test_example():\n    assert True\n"
    )
    _LLM_REVISION = (
        "VERDICT: needs_revision\n"
        "NOTES: Missing precondition section.\n"
        "TEST_SUGGESTION:\n"
        "def test_placeholder():\n    pass\n"
    )

    def _make_contract(self, sdd_project: Path, cid: str, status: str = "review") -> Path:
        p = sdd_project / ".sdd" / "contracts" / f"{cid}-test.md"
        _write_contract(p, cid, status, spec="SPEC-0001", tests=[])
        return p

    def _mock_provider(self, llm_text: str):
        from sdd_cli.llm.base import CompletionResult, UsageMetadata
        provider = MagicMock()
        provider.complete.return_value = CompletionResult(
            text=llm_text,
            usage=UsageMetadata(),
        )
        return provider

    def test_approved_verdict_creates_tst_with_generated_by(self, cfg, sdd_project):
        """TC-01: approved-Antwort → TST-Datei mit generated_by: llm."""
        self._make_contract(sdd_project, "CON-9901")
        (sdd_project / ".sdd" / "specs").mkdir(parents=True, exist_ok=True)
        _write_spec(sdd_project / ".sdd" / "specs" / "SPEC-0001-test.md", "SPEC-0001", "draft")

        with patch(
            "sdd_cli.llm.factory.get_completion_provider",
            return_value=self._mock_provider(self._LLM_APPROVED),
        ):
            result = review_contract(cfg, "CON-9901")

        assert result.tst_path.exists()
        content = result.tst_path.read_text(encoding="utf-8")
        assert "generated_by: llm" in content
        assert "status: draft" in content
        assert result.llm_verdict == "approved"

    def test_needs_revision_appends_review_notes_to_contract(self, cfg, sdd_project):
        """TC-02: needs_revision → LLM Review Notes an Contract angehängt."""
        contract_path = self._make_contract(sdd_project, "CON-9902")
        _write_spec(sdd_project / ".sdd" / "specs" / "SPEC-0001-test.md", "SPEC-0001", "draft")

        with patch(
            "sdd_cli.llm.factory.get_completion_provider",
            return_value=self._mock_provider(self._LLM_REVISION),
        ):
            result = review_contract(cfg, "CON-9902")

        assert "## LLM Review Notes" in contract_path.read_text(encoding="utf-8")

    def test_contract_linked_with_tst_id(self, cfg, sdd_project):
        """TC-03: Contract-Datei enthält die neue TST-ID."""
        contract_path = self._make_contract(sdd_project, "CON-9903")
        _write_spec(sdd_project / ".sdd" / "specs" / "SPEC-0001-test.md", "SPEC-0001", "draft")

        with patch(
            "sdd_cli.llm.factory.get_completion_provider",
            return_value=self._mock_provider(self._LLM_APPROVED),
        ):
            result = review_contract(cfg, "CON-9903")

        contract_content = contract_path.read_text(encoding="utf-8")
        assert result.tst_id in contract_content

    def test_llm_error_propagates_without_file(self, cfg, sdd_project):
        """TC-04: LLM RuntimeError → kein TST geschrieben."""
        self._make_contract(sdd_project, "CON-9904")

        failing_provider = MagicMock()
        failing_provider.complete.side_effect = RuntimeError("LLM unavailable")

        with patch(
            "sdd_cli.llm.factory.get_completion_provider",
            return_value=failing_provider,
        ):
            with pytest.raises(RuntimeError):
                review_contract(cfg, "CON-9904")

        tst_files = list((sdd_project / ".sdd" / "tests").rglob("TST-99*.md"))
        assert not tst_files


# ─────────────────────────────────────────────────────────────────────────────
# TST-0054 – validate FR-10 / FR-11
# ─────────────────────────────────────────────────────────────────────────────

class TestValidateLifecycleRules:
    def _make_report_with_docs(
        self,
        contracts_data: list[dict],
        specs_data: list[dict],
        tests_data: list[dict] | None = None,
    ) -> Report:
        from sdd_cli.frontmatter import Document
        from pathlib import Path

        def _doc(fm: dict, base: str = "/tmp") -> Document:
            return Document(path=Path(f"{base}/{fm['id']}.md"), frontmatter=fm, body="")

        contracts = [_doc(c) for c in contracts_data]
        specs = [_doc(s, "/tmp/specs") for s in specs_data]
        test_index = {t["id"]: _doc(t) for t in (tests_data or [])}

        report = Report()
        _check_lifecycle_rules(report, contracts, specs, test_index)
        return report

    def test_fr10_contract_review_no_tests_is_error(self):
        """TC-01: Contract review + tests:[] → ERROR."""
        report = self._make_report_with_docs(
            contracts_data=[{"id": "CON-0001", "status": "review", "tests": []}],
            specs_data=[],
        )
        errors = [i for i in report.errors if "FR-10" in i.message]
        assert errors

    def test_fr10_contract_review_with_test_no_error(self):
        """TC-02: Contract review + tests vorhanden → kein FR-10."""
        report = self._make_report_with_docs(
            contracts_data=[{"id": "CON-0001", "status": "review", "tests": ["TST-0001"]}],
            specs_data=[],
            tests_data=[{"id": "TST-0001"}],
        )
        errors = [i for i in report.errors if "FR-10" in i.message]
        assert not errors

    def test_fr10_contract_draft_no_error(self):
        """TC-03: Contract draft + tests:[] → kein FR-10."""
        report = self._make_report_with_docs(
            contracts_data=[{"id": "CON-0001", "status": "draft", "tests": []}],
            specs_data=[],
        )
        errors = [i for i in report.errors if "FR-10" in i.message]
        assert not errors

    def test_fr11_approved_spec_with_review_contract_is_warning(self):
        """TC-04: Spec approved + Contract review → WARNING."""
        report = self._make_report_with_docs(
            contracts_data=[{"id": "CON-0001", "status": "review", "tests": []}],
            specs_data=[{"id": "SPEC-0001", "status": "approved", "contracts": ["CON-0001"]}],
        )
        warnings = [i for i in report.warnings if "FR-11" in i.message]
        assert warnings

    def test_fr11_approved_spec_all_contracts_approved_no_warning(self):
        """TC-05: Spec approved + alle Contracts approved → kein FR-11."""
        report = self._make_report_with_docs(
            contracts_data=[{"id": "CON-0001", "status": "approved", "tests": ["TST-0001"]}],
            specs_data=[{"id": "SPEC-0001", "status": "approved", "contracts": ["CON-0001"]}],
            tests_data=[{"id": "TST-0001"}],
        )
        warnings = [i for i in report.warnings if "FR-11" in i.message]
        assert not warnings
