"""`sdd new github-workflow` ist ersatzlos entfallen (SPEC-0044 FR-06, v0.2.0).

Der Stub behauptete "in sdd init integriert" — das ist nie geschehen; init.py
referenziert github-actions an keiner Stelle. FR-06 verlangte dafuer eine
interaktive Rueckfrage, was mit dem autonomen Default (SPEC-0051) und dem
keyfreien Betrieb (SPEC-0050, der Workflow braucht einen ANTHROPIC_API_KEY als
Secret) kollidiert. Die Anforderung ist deshalb zurueckgenommen statt mit einem
Sonderfall gerettet.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tool"))

_ROOT = Path(__file__).resolve().parents[2]


class TestStubTellsTheTruth:
    def test_stub_no_longer_claims_integration(self):
        from sdd_cli.main import cli

        hilfe = cli.commands["new"].commands["github-workflow"].help or ""
        assert "sdd init" not in hilfe, (
            "Der Hinweis behauptet weiter eine Integration, die es nicht gibt"
        )

    def test_stub_points_at_the_template(self):
        from click.testing import CliRunner

        from sdd_cli.main import cli

        result = CliRunner().invoke(cli, ["new", "github-workflow"])
        assert result.exit_code == 1
        assert ".sdd/templates/github-actions/" in result.output

    def test_init_really_does_not_create_it(self, tmp_path):
        """Belegt, dass die Ruecknahme den Ist-Zustand beschreibt."""
        from sdd_cli.init import init_project

        init_project(tmp_path, title="Probe")
        assert not (tmp_path / ".github" / "workflows").exists()

    def test_template_is_shipped_and_reachable(self, tmp_path):
        from sdd_cli.init import init_project

        init_project(tmp_path, title="Probe")
        vorlage = (tmp_path / ".sdd" / "templates" / "github-actions"
                   / "sdd-orchestrate.yml")
        assert vorlage.exists(), "Die Vorlage muss nach sdd init auffindbar sein"


class TestSpecReflectsTheDecision:
    def _spec(self) -> str:
        return (_ROOT / ".sdd" / "specs"
                / "SPEC-0044-sdd-cleanup-cli-skill-consolidation.md").read_text(
            encoding="utf-8")

    def test_version_was_bumped(self):
        assert "version: 0.2.0" in self._spec()

    def test_rollback_is_documented_with_a_reason(self):
        text = self._spec()
        assert "Zurückgenommen am 2026-09-08" in text
        assert "ANTHROPIC_API_KEY" in text and "autonom" in text

    def test_inventory_row_matches(self):
        assert "ersatzlos entfallen; Vorlage bleibt unter" in self._spec()
