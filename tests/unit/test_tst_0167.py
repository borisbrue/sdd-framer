"""TST-0167: sdd hub start startet hub/app.py im Vordergrund auf Port 4711 (CON-0144)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from sdd_cli.main import hub_start


class TestTST0167:
    def test_uses_create_app_not_start_hub(self):
        """G-04: hub/app.py create_app wird aufgerufen, start_hub() nicht."""
        runner = CliRunner()
        with patch("sdd_cli.hub.app.create_app", return_value=MagicMock()) as mock_ca, \
             patch("uvicorn.run"), \
             patch("sdd_cli.main._hub_port_occupied", return_value=False):
            runner.invoke(hub_start, ["--no-browser"])
        mock_ca.assert_called_once()

    def test_default_port_is_4711(self):
        """G-03: Standardport ist 4711."""
        runner = CliRunner()
        with patch("sdd_cli.hub.app.create_app", return_value=MagicMock()), \
             patch("uvicorn.run") as mock_uv, \
             patch("sdd_cli.main._hub_port_occupied", return_value=False):
            runner.invoke(hub_start, ["--no-browser"])
        assert mock_uv.call_args[1]["port"] == 4711

    def test_custom_port_overrides_default(self):
        """G-03: --port überschreibt Default."""
        runner = CliRunner()
        with patch("sdd_cli.hub.app.create_app", return_value=MagicMock()), \
             patch("uvicorn.run") as mock_uv, \
             patch("sdd_cli.main._hub_port_occupied", return_value=False):
            runner.invoke(hub_start, ["--port", "5555", "--no-browser"])
        assert mock_uv.call_args[1]["port"] == 5555
