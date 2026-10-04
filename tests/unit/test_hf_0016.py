"""HF-0016: Review-Hinweise vollständig ausgeben (#139), ein Notes-Block statt Historie (#140).

Im Projekt knxhub hatten Contracts nach drei Review-Runden bis zu vier „LLM Review Notes“-
Blöcke; das nächste Review las sie mit und wertete eine veraltete Notiz als Blocker. Die CLI
schnitt die Hinweise nach 200 Zeichen ab und zeigte sie bei `--spec` gar nicht.
"""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from sdd_cli.config import load_config
from sdd_cli.lifecycle import review_contract
from sdd_cli.llm.base import CompletionResult, UsageMetadata
from sdd_cli.main import cli

LANG = (
    "Der Contract ist inhaltlich dicht, hat aber neun Punkte, die vor approved geklärt "
    "gehören — drei davon sind harte Widersprüche, an denen TST-0001 sofort scheitern würde.\n\n"
    "## Blocker\n\n- B1: Statuscode 404 fehlt\n- B2: ENDE-DER-HINWEISE"
)


def _antwort(verdict: str, notes: str) -> str:
    return f"VERDICT: {verdict}\nNOTES: {notes}\nTEST_SUGGESTION:\ndef test_x():\n    pass\n"


def _provider(*antworten: str) -> MagicMock:
    provider = MagicMock()
    provider.complete.side_effect = [
        CompletionResult(text=a, usage=UsageMetadata()) for a in antworten
    ]
    return provider


@pytest.fixture
def projekt(tmp_path: Path) -> Path:
    sdd = tmp_path / ".sdd"
    (sdd / "specs").mkdir(parents=True)
    (sdd / "contracts").mkdir()
    (sdd / "config.yaml").write_text("project:\n  id: PRJ-0001\n  name: T\n", encoding="utf-8")
    (sdd / "specs" / "SPEC-0001-t.md").write_text(
        "---\nid: SPEC-0001\nstatus: draft\ncontracts: [CON-0001]\n---\nSpec\n", encoding="utf-8")
    (sdd / "contracts" / "CON-0001-t.md").write_text(
        "---\nid: CON-0001\nstatus: review\nspec: SPEC-0001\ntests: []\n---\n"
        "# Contract\n\nNormativer Text.\n", encoding="utf-8")
    old = Path.cwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(old)


def _contract(projekt: Path) -> str:
    return (projekt / ".sdd" / "contracts" / "CON-0001-t.md").read_text(encoding="utf-8")


class TestEinNotesBlock:
    def test_zweite_runde_ersetzt_den_block(self, projekt):
        provider = _provider(_antwort("needs_revision", "ALT: Punkt eins"),
                             _antwort("needs_revision", "NEU: Punkt zwei"))
        with patch("sdd_cli.llm.factory.get_completion_provider", return_value=provider):
            review_contract(load_config(projekt), "CON-0001")
            review_contract(load_config(projekt), "CON-0001")

        text = _contract(projekt)
        assert text.count("## LLM Review Notes") == 1
        assert "NEU: Punkt zwei" in text and "ALT: Punkt eins" not in text
        assert "Normativer Text." in text

    def test_alte_notizen_nicht_im_prompt(self, projekt):
        provider = _provider(_antwort("needs_revision", "ALT: Punkt eins"),
                             _antwort("needs_revision", "NEU"))
        with patch("sdd_cli.llm.factory.get_completion_provider", return_value=provider):
            review_contract(load_config(projekt), "CON-0001")
            review_contract(load_config(projekt), "CON-0001")

        zweiter_prompt = provider.complete.call_args_list[1].args[0]
        assert "Normativer Text." in zweiter_prompt
        assert "ALT: Punkt eins" not in zweiter_prompt

    def test_approved_entfernt_veraltete_notizen(self, projekt):
        provider = _provider(_antwort("needs_revision", "ALT: Punkt eins"),
                             _antwort("approved", ""))
        with patch("sdd_cli.llm.factory.get_completion_provider", return_value=provider):
            review_contract(load_config(projekt), "CON-0001")
            review_contract(load_config(projekt), "CON-0001")

        text = _contract(projekt)
        assert "LLM Review Notes" not in text and "ALT: Punkt eins" not in text
        assert "status: approved" in text and "Normativer Text." in text


class TestCliHinweise:
    def test_einzelreview_gibt_hinweise_vollstaendig_aus(self, projekt):
        provider = _provider(_antwort("needs_revision", LANG))
        with patch("sdd_cli.llm.factory.get_completion_provider", return_value=provider):
            result = CliRunner().invoke(cli, ["review", "contract", "CON-0001"])

        assert "ENDE-DER-HINWEISE" in result.output

    def test_spec_lauf_gibt_hinweise_aus(self, projekt):
        provider = _provider(_antwort("needs_revision", LANG))
        with patch("sdd_cli.llm.factory.get_completion_provider", return_value=provider):
            result = CliRunner().invoke(cli, ["review", "contract", "--spec", "SPEC-0001"])

        assert "needs_revision" in result.output
        assert "ENDE-DER-HINWEISE" in result.output
