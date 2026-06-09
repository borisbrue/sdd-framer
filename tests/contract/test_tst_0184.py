"""TST-0184 – HOL-Datei-Struktur und Idempotenz-Garantie (CON-0158, SPEC-0033)."""
from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner

from sdd_cli.main import cli
from sdd_cli.generate_holdouts import write_hol_file


@pytest.fixture()
def cfg(tmp_path: Path):
    from sdd_cli.config import SddConfig
    (tmp_path / ".sdd").mkdir()
    return SddConfig(root=tmp_path, raw={"ids": {"padding": 4}})


@pytest.fixture()
def sdd_project(tmp_path: Path):
    sdd_dir = tmp_path / ".sdd"
    for d in [sdd_dir / "specs", sdd_dir / "contracts" / "behavior", sdd_dir / "holdout"]:
        d.mkdir(parents=True)
    (sdd_dir / "config.yaml").write_text(
        yaml.dump({"ids": {"padding": 4}, "llm": {"completion": {"provider": "anthropic", "model": "claude-haiku-4-5-20251001"}}}),
        encoding="utf-8",
    )
    (sdd_dir / "specs" / "SPEC-0033-test.md").write_text(
        "---\nid: SPEC-0033\ntitle: Test\nstatus: approved\ncontracts:\n  - CON-0157\n---\n# Body\n",
        encoding="utf-8",
    )
    (sdd_dir / "contracts" / "behavior" / "CON-0157-test.md").write_text(
        "---\nid: CON-0157\ntitle: Test\nstatus: approved\n---\n# Scenarios\n",
        encoding="utf-8",
    )
    return tmp_path


SCENARIO = {
    "title": "Happy Path",
    "priority": "critical",
    "type": "cli",
    "description": "Der Nutzer ruft den Befehl auf.",
    "setup": None,
    "test": {
        "action": {"command": "sdd", "args": ["generate-holdouts", "SPEC-0033"]},
        "assert": {"exit_code": 0, "stdout_contains": ["HOL-"]},
    },
    "teardown": None,
    "evaluation_hint": "- Exit-Code prüfen\n- HOL-Dateien zählen",
}


class TestTST0184:
    def test_hol_file_has_required_frontmatter_fields(self, cfg) -> None:
        path = write_hol_file("HOL-0001", "SPEC-0033", "CON-0157", SCENARIO, cfg)
        text = path.read_text(encoding="utf-8")

        match = re.match(r"^---\s*\n(?P<yaml>.*?)\n---\s*\n", text, re.DOTALL)
        assert match, "Kein Frontmatter gefunden"
        fm = yaml.safe_load(match.group("yaml"))

        assert "id" in fm
        assert "spec" in fm
        assert "status" in fm
        assert "title" in fm

    def test_status_is_wip(self, cfg) -> None:
        path = write_hol_file("HOL-0001", "SPEC-0033", "CON-0157", SCENARIO, cfg)
        fm_text = re.match(r"^---\s*\n(?P<yaml>.*?)\n---", path.read_text(encoding="utf-8"), re.DOTALL).group("yaml")
        fm = yaml.safe_load(fm_text)
        assert fm["status"] == "wip"

    def test_spec_field_matches_spec_id(self, cfg) -> None:
        path = write_hol_file("HOL-0001", "SPEC-0033", "CON-0157", SCENARIO, cfg)
        fm_text = re.match(r"^---\s*\n(?P<yaml>.*?)\n---", path.read_text(encoding="utf-8"), re.DOTALL).group("yaml")
        fm = yaml.safe_load(fm_text)
        assert fm["spec"] == "SPEC-0033"

    def test_body_contains_required_sections(self, cfg) -> None:
        path = write_hol_file("HOL-0001", "SPEC-0033", "CON-0157", SCENARIO, cfg)
        body = path.read_text(encoding="utf-8")
        assert "## Test" in body
        assert "## Evaluation Hint" in body

    def test_idempotenz_second_run_skips_existing(self, sdd_project: Path, monkeypatch) -> None:
        def _fake_generate(contract_content, contract_id, spec_content, provider, num_scenarios=3):
            return [{"title": f"S{i}", "priority": "normal", "type": "cli",
                     "description": "x", "setup": None,
                     "test": {"action": {"command": "echo"}, "assert": {"exit_code": 0}},
                     "teardown": None, "evaluation_hint": "z"} for i in range(2)]

        monkeypatch.chdir(sdd_project)
        runner = CliRunner()

        with patch("sdd_cli.generate_holdouts.generate_holdout_scenarios", side_effect=_fake_generate):
            result1 = runner.invoke(cli, ["generate-holdouts", "SPEC-0033"])
        assert result1.exit_code == 0

        hol_files_after_first = list((sdd_project / ".sdd" / "holdout").rglob("*.md"))
        count_after_first = len(hol_files_after_first)
        assert count_after_first >= 2

        with patch("sdd_cli.generate_holdouts.generate_holdout_scenarios", side_effect=_fake_generate):
            result2 = runner.invoke(cli, ["generate-holdouts", "SPEC-0033"])
        assert result2.exit_code == 0
        assert "übersprungen" in result2.output

        hol_files_after_second = list((sdd_project / ".sdd" / "holdout").rglob("*.md"))
        assert len(hol_files_after_second) == count_after_first
