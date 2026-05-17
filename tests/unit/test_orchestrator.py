"""Unit-Tests für orchestrator.py – Pipeline-Datenstrukturen und Hilfsfunktionen."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sdd_cli.orchestrator import (
    PipelineAttempt,
    PipelineReport,
    persist_pipeline_report,
    _load_spec,
    _load_agents_md,
    _load_contracts,
    _build_code_gen_prompt,
    _write_files,
    _gh_available,
    _create_pr,
    _label_pr,
    BRANCH_PREFIX,
    LABEL_APPROVED,
    LABEL_FAILED,
)
from sdd_cli.config import SddConfig


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _cfg(tmp_path: Path) -> SddConfig:
    sdd = tmp_path / ".sdd"
    (sdd / "specs").mkdir(parents=True)
    (sdd / "contracts").mkdir(parents=True)
    return SddConfig(root=tmp_path, raw={})


def _write_spec(path: Path, spec_id: str, contracts: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    contracts_yaml = json.dumps(contracts or [])
    path.write_text(
        f"---\nid: {spec_id}\ntitle: Feature\nstatus: draft\n"
        f"contracts: {contracts_yaml}\n---\nbody content\n",
        encoding="utf-8",
    )


def _write_contract(path: Path, contract_id: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\nid: {contract_id}\ntype: api\nformat: openapi\n---\ncontract body\n",
        encoding="utf-8",
    )


# ─── PipelineAttempt ──────────────────────────────────────────────────────────

class TestPipelineAttempt:
    def test_fields_accessible(self):
        a = PipelineAttempt(
            attempt=1, branch="sdd/SPEC-0001-attempt-1",
            build_passed=True, eval_pass_rate=0.95,
            pr_url="https://github.com/org/repo/pull/1",
            error=None, explanation="Add login feature",
        )
        assert a.attempt == 1
        assert a.build_passed is True
        assert a.eval_pass_rate == 0.95

    def test_defaults_allow_none(self):
        a = PipelineAttempt(
            attempt=2, branch="sdd/SPEC-0001-attempt-2",
            build_passed=None, eval_pass_rate=None,
            pr_url=None, error=None, explanation="",
        )
        assert a.build_passed is None
        assert a.pr_url is None


# ─── PipelineReport ───────────────────────────────────────────────────────────

class TestPipelineReport:
    def test_to_dict_structure(self):
        report = PipelineReport(
            timestamp="2026-01-01T00:00:00Z",
            spec_id="SPEC-0001",
            final_status="labeled",
        )
        d = report.to_dict()
        assert d["spec_id"] == "SPEC-0001"
        assert d["final_status"] == "labeled"
        assert d["attempts"] == []
        assert "timestamp" in d

    def test_to_dict_with_attempts(self):
        report = PipelineReport(
            timestamp="2026-01-01T00:00:00Z",
            spec_id="SPEC-0001",
            final_status="merged",
        )
        report.attempts.append(PipelineAttempt(
            attempt=1, branch="sdd/SPEC-0001-attempt-1",
            build_passed=True, eval_pass_rate=0.95,
            pr_url="https://github.com/org/repo/pull/1",
            error=None, explanation="feature impl",
        ))
        d = report.to_dict()
        assert len(d["attempts"]) == 1
        assert d["attempts"][0]["attempt"] == 1

    def test_issue_url_in_dict(self):
        report = PipelineReport(
            timestamp="2026-01-01T00:00:00Z",
            spec_id="SPEC-0001",
            final_status="failed",
            issue_url="https://github.com/org/repo/issues/42",
        )
        d = report.to_dict()
        assert d["issue_url"] == "https://github.com/org/repo/issues/42"


# ─── _load_spec ───────────────────────────────────────────────────────────────

class TestLoadSpec:
    def test_loads_existing_spec(self, tmp_path):
        cfg = _cfg(tmp_path)
        _write_spec(tmp_path / ".sdd" / "specs" / "SPEC-0001.md", "SPEC-0001")
        content = _load_spec(cfg, "SPEC-0001")
        assert "SPEC-0001" in content
        assert "body content" in content

    def test_raises_for_missing_spec(self, tmp_path):
        cfg = _cfg(tmp_path)
        with pytest.raises(ValueError, match="Spec nicht gefunden"):
            _load_spec(cfg, "SPEC-9999")

    def test_finds_nested_spec(self, tmp_path):
        cfg = _cfg(tmp_path)
        nested = tmp_path / ".sdd" / "specs" / "subdir" / "SPEC-0001.md"
        _write_spec(nested, "SPEC-0001")
        content = _load_spec(cfg, "SPEC-0001")
        assert "SPEC-0001" in content


# ─── _load_agents_md ──────────────────────────────────────────────────────────

class TestLoadAgentsMd:
    def test_returns_content_when_exists(self, tmp_path):
        cfg = _cfg(tmp_path)
        agents = tmp_path / "AGENTS.md"
        agents.write_text("# Agents\nContent here.", encoding="utf-8")
        result = _load_agents_md(cfg)
        assert "Agents" in result

    def test_returns_empty_when_missing(self, tmp_path):
        cfg = _cfg(tmp_path)
        result = _load_agents_md(cfg)
        assert result == ""


# ─── _load_contracts ──────────────────────────────────────────────────────────

class TestLoadContracts:
    def test_loads_referenced_contracts(self, tmp_path):
        cfg = _cfg(tmp_path)
        _write_spec(tmp_path / ".sdd" / "specs" / "SPEC-0001.md", "SPEC-0001",
                    contracts=["CON-0001"])
        _write_contract(tmp_path / ".sdd" / "contracts" / "CON-0001.md", "CON-0001")
        contracts = _load_contracts(cfg, "SPEC-0001")
        assert len(contracts) == 1
        assert contracts[0][0] == "CON-0001"
        assert "contract body" in contracts[0][1]

    def test_returns_empty_for_spec_without_contracts(self, tmp_path):
        cfg = _cfg(tmp_path)
        _write_spec(tmp_path / ".sdd" / "specs" / "SPEC-0001.md", "SPEC-0001", contracts=[])
        contracts = _load_contracts(cfg, "SPEC-0001")
        assert contracts == []

    def test_returns_empty_for_missing_spec(self, tmp_path):
        cfg = _cfg(tmp_path)
        contracts = _load_contracts(cfg, "SPEC-9999")
        assert contracts == []

    def test_skips_missing_contract_file(self, tmp_path):
        cfg = _cfg(tmp_path)
        _write_spec(tmp_path / ".sdd" / "specs" / "SPEC-0001.md", "SPEC-0001",
                    contracts=["CON-9999"])
        contracts = _load_contracts(cfg, "SPEC-0001")
        assert contracts == []


# ─── _build_code_gen_prompt ───────────────────────────────────────────────────

class TestBuildCodeGenPrompt:
    def test_contains_spec_content(self):
        prompt = _build_code_gen_prompt("Spec content here", "", [], "")
        assert "Spec content here" in prompt

    def test_includes_agents_md_when_provided(self):
        prompt = _build_code_gen_prompt("spec", "## Agents Guide\nContent", [], "")
        assert "AGENTS.md" in prompt
        assert "Agents Guide" in prompt

    def test_omits_agents_md_section_when_empty(self):
        prompt = _build_code_gen_prompt("spec", "", [], "")
        assert "AGENTS.md" not in prompt

    def test_includes_contracts(self):
        contracts = [("CON-0001", "openapi: 3.0...")]
        prompt = _build_code_gen_prompt("spec", "", contracts, "")
        assert "CON-0001" in prompt
        assert "openapi: 3.0" in prompt

    def test_includes_error_context(self):
        prompt = _build_code_gen_prompt("spec", "", [], "Build failed: TypeError")
        assert "Build failed: TypeError" in prompt
        assert "Previous Attempt Failed" in prompt

    def test_empty_error_context_omitted(self):
        prompt = _build_code_gen_prompt("spec", "", [], "")
        assert "Previous Attempt Failed" not in prompt

    def test_json_format_in_prompt(self):
        prompt = _build_code_gen_prompt("spec", "", [], "")
        assert '"files"' in prompt


# ─── _write_files ─────────────────────────────────────────────────────────────

class TestWriteFiles:
    def test_writes_single_file(self, tmp_path):
        cfg = _cfg(tmp_path)
        _write_files(cfg, [{"path": "src/main.py", "content": "print('hello')"}])
        result = (tmp_path / "src" / "main.py").read_text()
        assert result == "print('hello')"

    def test_creates_parent_dirs(self, tmp_path):
        cfg = _cfg(tmp_path)
        _write_files(cfg, [{"path": "a/b/c/d.txt", "content": "deep"}])
        assert (tmp_path / "a" / "b" / "c" / "d.txt").exists()

    def test_writes_multiple_files(self, tmp_path):
        cfg = _cfg(tmp_path)
        _write_files(cfg, [
            {"path": "src/a.py", "content": "a"},
            {"path": "src/b.py", "content": "b"},
        ])
        assert (tmp_path / "src" / "a.py").read_text() == "a"
        assert (tmp_path / "src" / "b.py").read_text() == "b"

    def test_empty_list_is_noop(self, tmp_path):
        cfg = _cfg(tmp_path)
        _write_files(cfg, [])  # should not raise


# ─── _gh_available ────────────────────────────────────────────────────────────

class TestGhAvailable:
    def test_returns_false_when_gh_not_found(self):
        with patch("sdd_cli.orchestrator._run") as mock_run:
            mock_run.side_effect = FileNotFoundError("gh not found")
            assert _gh_available() is False

    def test_returns_false_when_gh_exits_nonzero(self):
        with patch("sdd_cli.orchestrator._run") as mock_run:
            mock_run.return_value = (1, "error")
            assert _gh_available() is False

    def test_returns_true_when_gh_exits_zero(self):
        with patch("sdd_cli.orchestrator._run") as mock_run:
            mock_run.return_value = (0, "gh version 2.x")
            assert _gh_available() is True


# ─── _create_pr ───────────────────────────────────────────────────────────────

class TestCreatePr:
    def test_returns_none_when_gh_unavailable(self, tmp_path):
        cfg = _cfg(tmp_path)
        with patch("sdd_cli.orchestrator._gh_available", return_value=False):
            result = _create_pr(cfg, "sdd/branch", "SPEC-0001", "feat")
            assert result is None

    def test_returns_none_when_gh_command_fails(self, tmp_path):
        cfg = _cfg(tmp_path)
        with patch("sdd_cli.orchestrator._gh_available", return_value=True):
            with patch("sdd_cli.orchestrator._run", return_value=(1, "error")):
                result = _create_pr(cfg, "sdd/branch", "SPEC-0001", "feat")
                assert result is None

    def test_returns_pr_url_from_output(self, tmp_path):
        cfg = _cfg(tmp_path)
        with patch("sdd_cli.orchestrator._gh_available", return_value=True):
            with patch("sdd_cli.orchestrator._run",
                       return_value=(0, "https://github.com/org/repo/pull/42")):
                result = _create_pr(cfg, "sdd/branch", "SPEC-0001", "feat")
                assert result == "https://github.com/org/repo/pull/42"


# ─── _label_pr ────────────────────────────────────────────────────────────────

class TestLabelPr:
    def test_skips_when_gh_unavailable(self, tmp_path):
        cfg = _cfg(tmp_path)
        with patch("sdd_cli.orchestrator._gh_available", return_value=False):
            with patch("sdd_cli.orchestrator._run") as mock_run:
                _label_pr(cfg, "https://github.com/org/repo/pull/1", LABEL_APPROVED)
                mock_run.assert_not_called()

    def test_skips_empty_pr_url(self, tmp_path):
        cfg = _cfg(tmp_path)
        with patch("sdd_cli.orchestrator._gh_available", return_value=True):
            with patch("sdd_cli.orchestrator._run") as mock_run:
                _label_pr(cfg, "", LABEL_APPROVED)
                mock_run.assert_not_called()


# ─── persist_pipeline_report ──────────────────────────────────────────────────

class TestPersistPipelineReport:
    def test_creates_json_file(self, tmp_path):
        cfg = _cfg(tmp_path)
        report = PipelineReport(
            timestamp="2026-01-01T00:00:00Z",
            spec_id="SPEC-0001",
            final_status="labeled",
        )
        path = persist_pipeline_report(cfg, report)
        assert path.exists()
        assert path.suffix == ".json"
        data = json.loads(path.read_text())
        assert data["spec_id"] == "SPEC-0001"

    def test_creates_pipeline_dir(self, tmp_path):
        cfg = _cfg(tmp_path)
        report = PipelineReport(
            timestamp="2026-01-01T00:00:00Z",
            spec_id="SPEC-0001",
            final_status="failed",
        )
        persist_pipeline_report(cfg, report)
        assert (tmp_path / ".sdd" / "pipeline").is_dir()

    def test_filename_contains_spec_id(self, tmp_path):
        cfg = _cfg(tmp_path)
        report = PipelineReport(
            timestamp="2026-01-01T00:00:00Z",
            spec_id="SPEC-0042",
            final_status="merged",
        )
        path = persist_pipeline_report(cfg, report)
        assert "SPEC-0042" in path.name


# ─── Constants ────────────────────────────────────────────────────────────────

class TestConstants:
    def test_branch_prefix(self):
        assert BRANCH_PREFIX == "sdd"

    def test_labels(self):
        assert "approved" in LABEL_APPROVED
        assert "failed" in LABEL_FAILED
