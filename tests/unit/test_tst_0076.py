# TST-0076 – PR-Dokument Schema-Validierung (CON-0067)
from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sdd_cli.config import SddConfig
from sdd_cli.dev_container import LocalGitStrategy, save_test_result


@pytest.fixture
def cfg(tmp_path):
    (tmp_path / ".sdd").mkdir()
    (tmp_path / ".sdd" / "config.yaml").write_text("")
    return SddConfig(root=tmp_path, raw={})


def _create_pr_doc(cfg, spec_id="SPEC-0021"):
    save_test_result(cfg, spec_id, passed=3, total=3)
    with (
        patch("sdd_cli.dev_container._run", return_value=MagicMock(returncode=0, stdout="")),
        patch("sdd_cli.dev_container._git", return_value=MagicMock(returncode=0, stdout="3 files changed")),
    ):
        strategy = LocalGitStrategy()
        strategy.create(spec_id, cfg)
    return cfg.root / ".sdd" / "prs" / f"PR-{spec_id}.md"


def _parse_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"^---\n(.*?)\n---", text, re.DOTALL)
    assert match, "Kein YAML-Frontmatter gefunden"
    import yaml
    return yaml.safe_load(match.group(1)) or {}


# ── TC-01: Vollständiges valides PR-Dokument ──────────────────────────────────

def test_tc01_valid_pr_document_has_required_fields(cfg):
    pr_path = _create_pr_doc(cfg)
    assert pr_path.exists()
    fm = _parse_frontmatter(pr_path)

    for field in ("spec_id", "branch", "created", "test_result", "merge_command"):
        assert field in fm, f"Pflichtfeld '{field}' fehlt"


# ── TC-02: ohne übergebenen Branch leitet die Strategie dev/ ab (INV-01) ──────

def test_tc02_spec_id_branch_consistent(cfg):
    pr_path = _create_pr_doc(cfg)
    fm = _parse_frontmatter(pr_path)
    assert fm["branch"] == f"dev/{fm['spec_id']}", "spec_id und branch inkonsistent"


# ── TC-03: merge_command enthält Branch-Namen (INV-03) ───────────────────────

def test_tc03_merge_command_contains_branch(cfg):
    pr_path = _create_pr_doc(cfg)
    fm = _parse_frontmatter(pr_path)
    assert fm["branch"] in fm["merge_command"], "merge_command enthält nicht den Branch-Namen"


# ── TC-04: .sdd/prs/ wird automatisch erstellt (INV-04) ─────────────────────

def test_tc04_prs_dir_created_automatically(cfg):
    prs_dir = cfg.root / ".sdd" / "prs"
    assert not prs_dir.exists()
    _create_pr_doc(cfg)
    assert prs_dir.exists()


# ── TC-05: test_result: passed nur bei tests_passed == tests_total (INV-02) ──

def test_tc05_test_result_passed_requires_all_passing(cfg):
    pr_path = _create_pr_doc(cfg)
    fm = _parse_frontmatter(pr_path)
    if fm["test_result"] == "passed":
        assert fm.get("tests_passed", 0) == fm.get("tests_total", -1)
        assert fm.get("tests_total", 0) > 0


# ── TC-06: ein übergebener Branch landet im Dokument (INV-01, v0.3.0) ────────
#
# Die Finalisierung übergibt ihren eigenen Branch (feat/SPEC-XXXX). Bis #123
# verlangte das Schema dev/SPEC-XXXX, und kein Test prüfte den übergebenen Fall,
# also genau den, der heute tatsächlich vorkommt.

def test_tc06_uebergebener_branch_landet_im_dokument(cfg):
    save_test_result(cfg, "SPEC-0021", passed=3, total=3)
    with patch("sdd_cli.dev_container._git",
               return_value=MagicMock(returncode=0, stdout="3 files changed")) as mock_git:
        LocalGitStrategy().create("SPEC-0021", cfg, branch="feat/SPEC-0021")

    fm = _parse_frontmatter(cfg.root / ".sdd" / "prs" / "PR-SPEC-0021.md")
    assert fm["branch"] == "feat/SPEC-0021"
    assert "feat/SPEC-0021" in fm["merge_command"]
    mock_git.assert_called_once_with(
        ["diff", "main..feat/SPEC-0021", "--stat"], capture=True, check=False)
