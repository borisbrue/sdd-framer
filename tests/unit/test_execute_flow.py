"""Unit-Tests für patch_status (TST-0026); TST-0027 (_call_code_gen_agent) entfällt mit SPEC-0062.

Spec: SPEC-0007 · Contracts: CON-0020, CON-0021
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tool"))

from sdd_cli.frontmatter import parse, patch_status

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
