"""Unit-Tests für generate_holdouts.write_hol_file (SPEC-0033)."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from sdd_cli.generate_holdouts import write_hol_file


@pytest.fixture()
def cfg(tmp_path: Path):
    from sdd_cli.config import SddConfig
    (tmp_path / ".sdd").mkdir()
    return SddConfig(root=tmp_path, raw={"ids": {"padding": 4}})


SCENARIO = {
    "title": "Happy Path Test",
    "input": "Der Nutzer ruft den Befehl auf.",
    "expected": "Exit-Code 0 und mindestens 2 HOL-Dateien angelegt.",
    "evaluation_hint": "- Exit-Code prüfen\n- HOL-Dateien zählen",
}


def test_creates_hol_file(cfg) -> None:
    path = write_hol_file("HOL-0001", "SPEC-0033", "CON-0157", SCENARIO, cfg)
    assert path.exists()


def test_frontmatter_has_required_fields(cfg) -> None:
    path = write_hol_file("HOL-0001", "SPEC-0033", "CON-0157", SCENARIO, cfg)
    text = path.read_text(encoding="utf-8")

    import re
    match = re.match(r"^---\s*\n(?P<yaml>.*?)\n---\s*\n", text, re.DOTALL)
    assert match, "Kein Frontmatter gefunden"
    fm = yaml.safe_load(match.group("yaml"))

    assert fm["id"] == "HOL-0001"
    assert fm["spec"] == "SPEC-0033"
    assert fm["status"] == "ready"
    assert "title" in fm


def test_body_has_required_sections(cfg) -> None:
    path = write_hol_file("HOL-0001", "SPEC-0033", "CON-0157", SCENARIO, cfg)
    body = path.read_text(encoding="utf-8")

    assert "## Input" in body
    assert "## Expected" in body
    assert "## Evaluation Hint" in body


def test_file_placed_in_holdout_dir(cfg) -> None:
    path = write_hol_file("HOL-0001", "SPEC-0033", "CON-0157", SCENARIO, cfg)
    assert path.parent == cfg.holdout_dir


def test_status_is_ready(cfg) -> None:
    path = write_hol_file("HOL-0001", "SPEC-0033", "CON-0157", SCENARIO, cfg)
    text = path.read_text(encoding="utf-8")
    assert "status: ready" in text
