"""TST-0183 – CLI-Verhalten von sdd holdout generate (CON-0157, SPEC-0033)."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner

from sdd_cli.main import cli


@pytest.fixture()
def sdd_project(tmp_path: Path):
    sdd_dir = tmp_path / ".sdd"
    for d in [
        sdd_dir / "specs",
        sdd_dir / "contracts" / "behavior",
        sdd_dir / "holdout",
    ]:
        d.mkdir(parents=True)

    (sdd_dir / "config.yaml").write_text(
        yaml.dump({
            "ids": {"padding": 4},
            "llm": {"completion": {"provider": "anthropic", "model": "claude-haiku-4-5-20251001"}},
        }),
        encoding="utf-8",
    )
    (sdd_dir / "specs" / "SPEC-0033-test.md").write_text(
        "---\nid: SPEC-0033\ntitle: Test Spec\nstatus: approved\n"
        "contracts:\n  - CON-0157\n---\n# Body\n",
        encoding="utf-8",
    )
    (sdd_dir / "contracts" / "behavior" / "CON-0157-test.md").write_text(
        "---\nid: CON-0157\ntitle: Test Contract\nstatus: approved\n---\n"
        "## Szenarien\nGiven something\nWhen action\nThen result\n",
        encoding="utf-8",
    )
    return tmp_path


def _fake_generate(contract_content, contract_id, spec_content, provider, num_scenarios=3):
    return [
        {
            "title": f"Szenario {i+1}",
            "input": f"Input {i+1}",
            "expected": f"Expected {i+1}",
            "evaluation_hint": f"Hint {i+1}",
        }
        for i in range(2)
    ]


class TestTST0183:
    def test_happy_path_exit_code_zero(self, sdd_project: Path, monkeypatch) -> None:
        monkeypatch.chdir(sdd_project)
        runner = CliRunner()
        with patch("sdd_cli.generate_holdouts.generate_holdout_scenarios", side_effect=_fake_generate):
            result = runner.invoke(cli, ["holdout", "generate", "SPEC-0033"], catch_exceptions=False)
        assert result.exit_code == 0, result.output

    def test_happy_path_output_contains_hol_ids(self, sdd_project: Path, monkeypatch) -> None:
        monkeypatch.chdir(sdd_project)
        runner = CliRunner()
        with patch("sdd_cli.generate_holdouts.generate_holdout_scenarios", side_effect=_fake_generate):
            result = runner.invoke(cli, ["holdout", "generate", "SPEC-0033"])
        assert "HOL-" in result.output
        assert "angelegt" in result.output

    def test_draft_spec_exits_with_code_one(self, sdd_project: Path, monkeypatch) -> None:
        (sdd_project / ".sdd" / "specs" / "SPEC-0033-test.md").write_text(
            "---\nid: SPEC-0033\ntitle: Test\nstatus: draft\ncontracts:\n  - CON-0157\n---\n",
            encoding="utf-8",
        )
        monkeypatch.chdir(sdd_project)
        runner = CliRunner()
        result = runner.invoke(cli, ["holdout", "generate", "SPEC-0033"])
        assert result.exit_code == 1
        assert "approved oder in-progress" in result.output

    def test_no_contracts_exits_with_code_one(self, sdd_project: Path, monkeypatch) -> None:
        (sdd_project / ".sdd" / "specs" / "SPEC-0033-test.md").write_text(
            "---\nid: SPEC-0033\ntitle: Test\nstatus: approved\ncontracts: []\n---\n",
            encoding="utf-8",
        )
        monkeypatch.chdir(sdd_project)
        runner = CliRunner()
        result = runner.invoke(cli, ["holdout", "generate", "SPEC-0033"])
        assert result.exit_code == 1
        assert "Keine Contracts gefunden" in result.output

    def test_unknown_spec_exits_with_code_one(self, sdd_project: Path, monkeypatch) -> None:
        monkeypatch.chdir(sdd_project)
        runner = CliRunner()
        result = runner.invoke(cli, ["holdout", "generate", "SPEC-9999"])
        assert result.exit_code == 1
        assert "SPEC-9999 nicht gefunden" in result.output
