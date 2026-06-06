"""TST-0168: sdd hub start gibt Warnung aus wenn Port belegt ist (CON-0145)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from sdd_cli.main import hub_start


class TestTST0168:
    def test_warning_when_port_occupied(self):
        """G-01/INV-01/INV-02: Warnung erscheint vor Start, enthält Port-Nummer."""
        runner = CliRunner()
        with patch("sdd_cli.hub.app.create_app", return_value=MagicMock()), \
             patch("uvicorn.run"), \
             patch("sdd_cli.main._hub_port_occupied", return_value=True):
            result = runner.invoke(hub_start, ["--port", "4711", "--no-browser"])
        assert "WARN" in result.output
        assert "4711" in result.output

    def test_no_warning_when_port_free(self):
        """G-03: Keine Warnung wenn Port frei."""
        runner = CliRunner()
        with patch("sdd_cli.hub.app.create_app", return_value=MagicMock()), \
             patch("uvicorn.run"), \
             patch("sdd_cli.main._hub_port_occupied", return_value=False):
            result = runner.invoke(hub_start, ["--port", "4711", "--no-browser"])
        assert "WARN" not in result.output

    def test_warning_contains_custom_port(self):
        """INV-02: Warnung enthält den konkreten Port-Wert."""
        runner = CliRunner()
        with patch("sdd_cli.hub.app.create_app", return_value=MagicMock()), \
             patch("uvicorn.run"), \
             patch("sdd_cli.main._hub_port_occupied", return_value=True):
            result = runner.invoke(hub_start, ["--port", "9876", "--no-browser"])
        assert "9876" in result.output
