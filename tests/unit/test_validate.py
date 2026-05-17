"""Unit-Tests für validate.py – Projektvalidierung (SPEC-0006)."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from sdd_cli.config import SddConfig
from sdd_cli.validate import (
    Issue,
    Report,
    validate,
    _check_agents_md,
    _check_lifecycle_rules,
    AGENTS_MD_REQUIRED_SECTIONS,
)


# ─── Schemas & Fixtures ───────────────────────────────────────────────────────

REAL_SCHEMAS = Path(__file__).parents[2] / ".sdd" / "schemas"


def _cfg(tmp_path: Path, raw: dict | None = None) -> SddConfig:
    sdd = tmp_path / ".sdd"
    for sub in ["specs", "contracts", "tests"]:
        (sdd / sub).mkdir(parents=True)
    schemas_dst = sdd / "schemas"
    if REAL_SCHEMAS.exists():
        shutil.copytree(REAL_SCHEMAS, schemas_dst)
    else:
        schemas_dst.mkdir(parents=True)
    return SddConfig(root=tmp_path, raw=raw or {})


def _write_spec(path: Path, **fm_overrides) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fm = {
        "id": "SPEC-0001", "title": "Feature A", "status": "draft",
        "owner": "boris", "created": "2026-01-01", "updated": "2026-01-01",
        "contracts": ["CON-0001"], "tests": ["TST-0001"],
    }
    fm.update(fm_overrides)
    yaml_lines = "\n".join(f"{k}: {json.dumps(v)}" for k, v in fm.items())
    path.write_text(f"---\n{yaml_lines}\n---\nbody\n", encoding="utf-8")


def _write_contract(path: Path, **fm_overrides) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fm = {
        "id": "CON-0001", "title": "API Contract", "type": "api",
        "format": "openapi", "spec": "SPEC-0001", "version": "1.0.0",
        "status": "draft", "tests": ["TST-0001"],
    }
    fm.update(fm_overrides)
    yaml_lines = "\n".join(f"{k}: {json.dumps(v)}" for k, v in fm.items())
    path.write_text(f"---\n{yaml_lines}\n---\nbody\n", encoding="utf-8")


def _write_test(path: Path, **fm_overrides) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fm = {
        "id": "TST-0001", "title": "Test", "level": "contract",
        "spec": "SPEC-0001", "contract": "CON-0001", "status": "draft",
    }
    fm.update(fm_overrides)
    yaml_lines = "\n".join(f"{k}: {json.dumps(v)}" for k, v in fm.items())
    path.write_text(f"---\n{yaml_lines}\n---\nbody\n", encoding="utf-8")


# ─── Issue ────────────────────────────────────────────────────────────────────

class TestIssue:
    def test_format_error(self, tmp_path):
        issue = Issue("error", tmp_path / ".sdd" / "specs" / "SPEC-0001.md", "Missing field")
        text = issue.format(tmp_path)
        assert "✗" in text
        assert "Missing field" in text
        assert ".sdd" in text

    def test_format_warning(self, tmp_path):
        issue = Issue("warning", tmp_path / "file.md", "Minor issue")
        text = issue.format(tmp_path)
        assert "⚠" in text

    def test_to_dict(self, tmp_path):
        issue = Issue("error", tmp_path / "file.md", "Msg", instruction="Fix it")
        d = issue.to_dict(tmp_path)
        assert d["severity"] == "error"
        assert d["message"] == "Msg"
        assert d["instruction"] == "Fix it"

    def test_format_path_outside_root(self, tmp_path):
        issue = Issue("error", Path("/other/path/file.md"), "Msg")
        text = issue.format(tmp_path)
        assert "Msg" in text


# ─── Report ───────────────────────────────────────────────────────────────────

class TestReport:
    def test_add_and_retrieve_errors(self, tmp_path):
        r = Report()
        r.add("error", tmp_path / "f.md", "bad")
        assert len(r.errors) == 1
        assert len(r.warnings) == 0
        assert not r.ok

    def test_add_warning(self, tmp_path):
        r = Report()
        r.add("warning", tmp_path / "f.md", "minor")
        assert len(r.warnings) == 1
        assert len(r.errors) == 0
        assert r.ok

    def test_ok_true_when_no_errors(self):
        r = Report()
        assert r.ok

    def test_mixed_issues(self, tmp_path):
        r = Report()
        r.add("error", tmp_path / "a.md", "e1")
        r.add("warning", tmp_path / "b.md", "w1")
        assert len(r.errors) == 1
        assert len(r.warnings) == 1
        assert not r.ok


# ─── validate ─────────────────────────────────────────────────────────────────

class TestValidate:
    def test_empty_project_no_errors(self, tmp_path):
        cfg = _cfg(tmp_path, raw={
            "validation": {
                "require_contract_per_spec": False,
                "require_test_per_contract": False,
                "fail_on_orphans": False,
                "check_agents_md": False,
            }
        })
        report = validate(cfg)
        assert report.ok

    def test_valid_full_chain_passes(self, tmp_path):
        cfg = _cfg(tmp_path, raw={
            "validation": {"check_agents_md": False}
        })
        _write_spec(tmp_path / ".sdd" / "specs" / "SPEC-0001.md")
        _write_contract(tmp_path / ".sdd" / "contracts" / "CON-0001.md")
        _write_test(tmp_path / ".sdd" / "tests" / "TST-0001.md")
        report = validate(cfg)
        assert report.ok, [i.message for i in report.errors]

    def test_spec_missing_contract_gives_error(self, tmp_path):
        cfg = _cfg(tmp_path, raw={"validation": {"check_agents_md": False}})
        _write_spec(tmp_path / ".sdd" / "specs" / "SPEC-0001.md",
                    contracts=["CON-9999"], tests=["TST-0001"])
        _write_test(tmp_path / ".sdd" / "tests" / "TST-0001.md")
        report = validate(cfg)
        assert any("CON-9999" in i.message for i in report.errors)

    def test_spec_missing_test_reference_gives_error(self, tmp_path):
        cfg = _cfg(tmp_path, raw={"validation": {"check_agents_md": False}})
        _write_spec(tmp_path / ".sdd" / "specs" / "SPEC-0001.md",
                    contracts=["CON-0001"], tests=["TST-9999"])
        _write_contract(tmp_path / ".sdd" / "contracts" / "CON-0001.md")
        report = validate(cfg)
        assert any("TST-9999" in i.message for i in report.errors)

    def test_contract_missing_spec_reference_gives_error(self, tmp_path):
        cfg = _cfg(tmp_path, raw={
            "validation": {
                "require_contract_per_spec": False,
                "fail_on_orphans": False,
                "check_agents_md": False,
            }
        })
        _write_contract(tmp_path / ".sdd" / "contracts" / "CON-0001.md",
                        spec="SPEC-9999")
        report = validate(cfg)
        assert any("SPEC-9999" in i.message for i in report.errors)

    def test_orphan_contract_gives_error(self, tmp_path):
        cfg = _cfg(tmp_path, raw={"validation": {
            "require_contract_per_spec": False,
            "check_agents_md": False,
        }})
        # Contract without spec: field
        path = tmp_path / ".sdd" / "contracts" / "CON-0001.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "---\nid: CON-0001\ntitle: T\ntype: api\nformat: openapi\n"
            "version: 1.0.0\nstatus: draft\n---\nbody\n",
            encoding="utf-8",
        )
        report = validate(cfg)
        assert any("orphan" in i.message.lower() for i in report.errors)

    def test_require_contract_per_spec_triggers_error(self, tmp_path):
        cfg = _cfg(tmp_path, raw={"validation": {
            "require_contract_per_spec": True,
            "require_test_per_contract": False,
            "fail_on_orphans": False,
            "check_agents_md": False,
        }})
        _write_spec(tmp_path / ".sdd" / "specs" / "SPEC-0001.md",
                    contracts=[], tests=[])
        report = validate(cfg)
        assert any("require_contract_per_spec" in i.message for i in report.errors)

    def test_require_test_per_contract_triggers_error(self, tmp_path):
        cfg = _cfg(tmp_path, raw={"validation": {
            "require_contract_per_spec": False,
            "require_test_per_contract": True,
            "fail_on_orphans": False,
            "check_agents_md": False,
        }})
        _write_contract(tmp_path / ".sdd" / "contracts" / "CON-0001.md",
                        tests=[])
        report = validate(cfg)
        assert any("require_test_per_contract" in i.message for i in report.errors)

    def test_frontmatter_schema_violation_gives_error(self, tmp_path):
        cfg = _cfg(tmp_path, raw={"validation": {"check_agents_md": False}})
        bad = tmp_path / ".sdd" / "specs" / "BAD.md"
        bad.parent.mkdir(parents=True, exist_ok=True)
        # Missing required fields
        bad.write_text("---\nid: SPEC-0001\n---\nbody\n", encoding="utf-8")
        report = validate(cfg)
        assert any("Frontmatter ungültig" in i.message for i in report.errors)

    def test_unknown_spec_status_gives_warning(self, tmp_path):
        cfg = _cfg(tmp_path, raw={"validation": {"check_agents_md": False}})
        _write_spec(tmp_path / ".sdd" / "specs" / "SPEC-0001.md",
                    status="unknown_status")
        _write_contract(tmp_path / ".sdd" / "contracts" / "CON-0001.md")
        _write_test(tmp_path / ".sdd" / "tests" / "TST-0001.md")
        report = validate(cfg)
        assert any("unknown_status" in i.message for i in report.warnings)

    def test_spec_depends_on_missing_spec(self, tmp_path):
        cfg = _cfg(tmp_path, raw={"validation": {"check_agents_md": False}})
        _write_spec(tmp_path / ".sdd" / "specs" / "SPEC-0001.md",
                    contracts=["CON-0001"], tests=["TST-0001"],
                    depends_on=["SPEC-9999"])
        _write_contract(tmp_path / ".sdd" / "contracts" / "CON-0001.md")
        _write_test(tmp_path / ".sdd" / "tests" / "TST-0001.md")
        report = validate(cfg)
        assert any("SPEC-9999" in i.message for i in report.errors)

    def test_artifact_missing_gives_warning(self, tmp_path):
        cfg = _cfg(tmp_path, raw={"validation": {
            "fail_on_orphans": False, "check_agents_md": False
        }})
        _write_contract(tmp_path / ".sdd" / "contracts" / "CON-0001.md",
                        artifact=".sdd/contracts/api/missing.yaml")
        report = validate(cfg)
        assert any("Artifact-Datei fehlt" in i.message for i in report.warnings)


# ─── _check_agents_md ─────────────────────────────────────────────────────────

class TestCheckAgentsMd:
    def test_missing_agents_md_gives_warning(self, tmp_path):
        cfg = SddConfig(root=tmp_path, raw={})
        report = Report()
        _check_agents_md(cfg, report)
        assert len(report.warnings) == 1
        assert "AGENTS.md fehlt" in report.warnings[0].message

    def test_complete_agents_md_no_warnings(self, tmp_path):
        agents = tmp_path / "AGENTS.md"
        sections = "\n".join(
            f"{s}\nEchter Inhalt für diese Sektion.\n" for s in AGENTS_MD_REQUIRED_SECTIONS
        )
        agents.write_text(sections, encoding="utf-8")
        cfg = SddConfig(root=tmp_path, raw={})
        report = Report()
        _check_agents_md(cfg, report)
        assert report.ok, [w.message for w in report.warnings]

    def test_missing_section_gives_warning(self, tmp_path):
        agents = tmp_path / "AGENTS.md"
        # Only add first section, skip the rest
        agents.write_text(
            f"{AGENTS_MD_REQUIRED_SECTIONS[0]}\nContent here.\n",
            encoding="utf-8",
        )
        cfg = SddConfig(root=tmp_path, raw={})
        report = Report()
        _check_agents_md(cfg, report)
        missing = [w for w in report.warnings if "fehlt" in w.message]
        assert len(missing) >= len(AGENTS_MD_REQUIRED_SECTIONS) - 1

    def test_placeholder_only_section_gives_warning(self, tmp_path):
        agents = tmp_path / "AGENTS.md"
        section = AGENTS_MD_REQUIRED_SECTIONS[0]
        agents.write_text(
            f"{section}\n<!-- placeholder -->\n",
            encoding="utf-8",
        )
        cfg = SddConfig(root=tmp_path, raw={})
        report = Report()
        _check_agents_md(cfg, report)
        assert any("Platzhalter" in w.message for w in report.warnings)


# ─── _check_lifecycle_rules ───────────────────────────────────────────────────

class TestCheckLifecycleRules:
    def _make_doc(self, path: Path, fm: dict) -> object:
        from sdd_cli.frontmatter import parse_safe
        path.parent.mkdir(parents=True, exist_ok=True)
        yaml_lines = "\n".join(f"{k}: {json.dumps(v)}" for k, v in fm.items())
        path.write_text(f"---\n{yaml_lines}\n---\nbody\n", encoding="utf-8")
        return parse_safe(path)

    def test_fr10_review_contract_without_test_gives_error(self, tmp_path):
        contract_path = tmp_path / "CON-0001.md"
        c = self._make_doc(contract_path, {
            "id": "CON-0001", "status": "review", "spec": "SPEC-0001", "tests": []
        })
        report = Report()
        _check_lifecycle_rules(report, [c], [], {})
        assert any("FR-10" in i.message for i in report.errors)

    def test_fr10_draft_contract_without_test_no_error(self, tmp_path):
        contract_path = tmp_path / "CON-0001.md"
        c = self._make_doc(contract_path, {
            "id": "CON-0001", "status": "draft", "spec": "SPEC-0001", "tests": []
        })
        report = Report()
        _check_lifecycle_rules(report, [c], [], {})
        assert report.ok

    def test_fr10_review_with_existing_test_no_error(self, tmp_path):
        contract_path = tmp_path / "CON-0001.md"
        c = self._make_doc(contract_path, {
            "id": "CON-0001", "status": "review", "spec": "SPEC-0001", "tests": ["TST-0001"]
        })
        report = Report()
        _check_lifecycle_rules(report, [c], [], {"TST-0001": object()})
        assert report.ok

    def test_fr11_approved_spec_with_review_contract_gives_warning(self, tmp_path):
        spec_path = tmp_path / "SPEC-0001.md"
        contract_path = tmp_path / "CON-0001.md"
        s = self._make_doc(spec_path, {
            "id": "SPEC-0001", "status": "approved",
            "contracts": ["CON-0001"], "title": "T"
        })
        c = self._make_doc(contract_path, {
            "id": "CON-0001", "status": "review", "spec": "SPEC-0001"
        })
        report = Report()
        _check_lifecycle_rules(report, [c], [s], {})
        assert any("FR-11" in w.message for w in report.warnings)

    def test_fr11_approved_spec_with_approved_contract_no_warning(self, tmp_path):
        spec_path = tmp_path / "SPEC-0001.md"
        contract_path = tmp_path / "CON-0001.md"
        s = self._make_doc(spec_path, {
            "id": "SPEC-0001", "status": "approved",
            "contracts": ["CON-0001"], "title": "T"
        })
        c = self._make_doc(contract_path, {
            "id": "CON-0001", "status": "approved", "spec": "SPEC-0001"
        })
        report = Report()
        _check_lifecycle_rules(report, [c], [s], {})
        assert len(report.warnings) == 0
