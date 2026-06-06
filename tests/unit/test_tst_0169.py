"""TST-0169: sdd hub run erscheint nicht in sdd hub --help (CON-0146)."""
from __future__ import annotations

from click.testing import CliRunner

from sdd_cli.main import hub, hub_run


class TestTST0169:
    def test_hub_run_not_in_hub_help(self):
        """G-01: hub run nicht in sdd hub --help."""
        runner = CliRunner()
        result = runner.invoke(hub, ["--help"])
        assert "run" not in result.output

    def test_hub_run_help_works(self):
        """G-02: sdd hub run --help funktioniert (Exit 0)."""
        runner = CliRunner()
        result = runner.invoke(hub_run, ["--help"])
        assert result.exit_code == 0
        assert "--port" in result.output

    def test_hub_run_is_hidden(self):
        """INV-01: hub_run hat hidden=True im Click-Objekt."""
        run_cmd = hub.commands.get("run")
        assert run_cmd is not None
        assert run_cmd.hidden is True

    def test_hub_start_still_visible_in_help(self):
        """Regression: hub start bleibt sichtbar."""
        runner = CliRunner()
        result = runner.invoke(hub, ["--help"])
        assert "start" in result.output
