"""Unit-Tests für patch_status (TST-0026) und _call_code_gen_agent CLI-Agent (TST-0027).

Spec: SPEC-0007 · Contracts: CON-0020, CON-0021
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tool"))

from sdd_cli.frontmatter import parse, patch_status          # noqa: E402
from sdd_cli.orchestrator import _call_code_gen_agent        # noqa: E402

CLAUDE_BIN = "/usr/bin/claude"


# ─── TST-0026: patch_status ───────────────────────────────────────────────────

def _make_md(tmp_path: Path, status: str = "approved") -> Path:
    md = tmp_path / "SPEC-T.md"
    md.write_text(
        f"---\nid: SPEC-T\ntitle: Test\nstatus: {status}\nowner: Boris\n---\n\nBody text.\n",
        encoding="utf-8",
    )
    return md


def test_tc01_patch_status_changes_field(tmp_path):
    """patch_status setzt status-Feld auf neuen Wert (TST-0026 TC-01)."""
    md = _make_md(tmp_path, "approved")
    patch_status(md, "implemented")
    doc = parse(md)
    assert doc.frontmatter["status"] == "implemented"


def test_tc02_patch_status_preserves_other_fields(tmp_path):
    """Restliches Frontmatter bleibt unverändert (TST-0026 TC-02)."""
    md = _make_md(tmp_path, "approved")
    patch_status(md, "implemented")
    doc = parse(md)
    assert doc.frontmatter["id"] == "SPEC-T"
    assert doc.frontmatter["title"] == "Test"
    assert doc.frontmatter["owner"] == "Boris"


def test_tc03_patch_status_preserves_body(tmp_path):
    """Body bleibt nach patch_status unverändert (TST-0026 TC-03)."""
    md = _make_md(tmp_path, "approved")
    patch_status(md, "implemented")
    doc = parse(md)
    assert "Body text." in doc.body


def test_tc04_patch_status_no_duplicate_field(tmp_path):
    """Kein doppeltes status-Feld nach patch_status (TST-0026 TC-04)."""
    md = _make_md(tmp_path, "approved")
    patch_status(md, "implemented")
    raw = md.read_text(encoding="utf-8")
    assert raw.count("status:") == 1


# ─── TST-0027: _call_code_gen_agent via Provider-Abstraktion ─────────────────
# Updated for SPEC-0008: _call_code_gen_agent now delegates to get_code_gen_provider().
# Subprocess details are tested in test_llm_providers.py (ClaudeCliCodeGenProvider).

def _mock_config(tmp_path: Path):
    cfg = MagicMock()
    cfg.root = tmp_path
    return cfg


def test_tc01_code_gen_agent_returns_files_and_explanation(tmp_path):
    """Erfolgreicher Agent-Lauf → (files, explanation) Tuple (TST-0027 TC-01)."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "foo.py").write_text("# hello", encoding="utf-8")

    mock_provider = MagicMock()
    mock_provider.generate.return_value = (
        [{"path": "src/foo.py", "content": "# hello"}],
        "Created src/foo.py with the implementation.",
    )
    cfg = _mock_config(tmp_path)

    with patch("sdd_cli.llm.get_code_gen_provider", return_value=mock_provider):
        files, explanation = _call_code_gen_agent(cfg, "SPEC-T", "spec", "", [], "")

    assert any(f["path"] == "src/foo.py" for f in files)
    assert "Created" in explanation or "implementation" in explanation.lower()


def test_tc02_code_gen_agent_claude_not_found(tmp_path):
    """Provider raises RuntimeError 'nicht gefunden' → propagates (TST-0027 TC-02)."""
    cfg = _mock_config(tmp_path)
    mock_provider = MagicMock()
    mock_provider.generate.side_effect = RuntimeError("claude CLI nicht gefunden")

    with patch("sdd_cli.llm.get_code_gen_provider", return_value=mock_provider):
        with pytest.raises(RuntimeError, match="nicht gefunden"):
            _call_code_gen_agent(cfg, "SPEC-T", "spec", "", [], "")


def test_tc03_code_gen_agent_nonzero_exit(tmp_path):
    """Provider raises RuntimeError 'exit 1' → propagates (TST-0027 TC-03)."""
    cfg = _mock_config(tmp_path)
    mock_provider = MagicMock()
    mock_provider.generate.side_effect = RuntimeError("claude CLI Fehler (exit 1)")

    with patch("sdd_cli.llm.get_code_gen_provider", return_value=mock_provider):
        with pytest.raises(RuntimeError, match="exit 1"):
            _call_code_gen_agent(cfg, "SPEC-T", "spec", "", [], "")


def test_tc04_code_gen_agent_explanation_from_last_line(tmp_path):
    """Explanation wird vom Provider zurückgegeben (TST-0027 TC-04)."""
    mock_provider = MagicMock()
    mock_provider.generate.return_value = ([], "Final summary of work done.")
    cfg = _mock_config(tmp_path)

    with patch("sdd_cli.llm.get_code_gen_provider", return_value=mock_provider):
        _, explanation = _call_code_gen_agent(cfg, "SPEC-T", "spec", "", [], "")

    assert explanation == "Final summary of work done."
