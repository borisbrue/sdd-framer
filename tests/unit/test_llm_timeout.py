"""Das Zeitlimit fuer LLM-Aufrufe muss einstellbar sein.

`regression_check` reicht keinen Timeout durch, und claude_cli setzte fest
120 Sekunden. Fuer reale Specs brauchte Stufe 2 mehrere Minuten und lieferte
dabei echte ERROR-Befunde — der Wert war systematisch zu knapp, nicht
gelegentlich.

Solange ein Skip die Gate-Phase noch markierte, fiel das nicht auf. Seit #71
bleibt das Gate dort stehen, und der einzige Ausweg waere `--allow-skipped-llm`
— also genau der bewusste Verzicht, den der Fix seltener machen sollte.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tool"))

from sdd_cli.config import SddConfig
from sdd_cli.llm.providers.claude_cli import ClaudeCliCompletionProvider


def _cfg(raw: dict | None = None) -> SddConfig:
    return SddConfig(root=Path("/tmp"), raw=raw or {})


def _erfasster_timeout(provider, **kwargs) -> int:
    """Ruft complete() und gibt den an subprocess.run gereichten Timeout zurueck."""
    erfasst: dict = {}

    def fake_run(cmd, **kw):
        erfasst.update(kw)
        raise subprocess.TimeoutExpired(cmd, kw.get("timeout", 0))

    with patch("sdd_cli.llm.providers.claude_cli._find_claude", return_value="/usr/bin/claude"), \
         patch("sdd_cli.llm.providers.claude_cli.subprocess.run", fake_run):
        try:
            provider.complete("prompt", **kwargs)
        except RuntimeError:
            pass
    return erfasst["timeout"]


class TestDefault:
    def test_default_ist_600(self):
        """120s reichten fuer reale Specs nicht."""
        assert _erfasster_timeout(ClaudeCliCompletionProvider()) == 600

    def test_config_property_liefert_600(self):
        assert _cfg().llm_timeout() == 600


class TestKonfigurierbar:
    def test_config_wert_wird_genutzt(self):
        assert _cfg({"llm": {"timeout_seconds": 900}}).llm_timeout() == 900

    def test_provider_uebernimmt_den_wert(self):
        assert _erfasster_timeout(ClaudeCliCompletionProvider(timeout=900)) == 900

    def test_argument_sticht_den_instanzwert(self):
        assert _erfasster_timeout(
            ClaudeCliCompletionProvider(timeout=900), timeout=30) == 30

    def test_ungueltiger_wert_faellt_zurueck(self):
        assert _cfg({"llm": {"timeout_seconds": "lang"}}).llm_timeout() == 600

    def test_null_wird_auf_eins_gehoben(self):
        assert _cfg({"llm": {"timeout_seconds": 0}}).llm_timeout() == 1


class TestFactoryReichtDurch:
    def test_erzeugter_provider_traegt_den_konfigurierten_wert(self):
        from sdd_cli.llm.factory import get_completion_provider

        provider = get_completion_provider(
            _cfg({"llm": {"timeout_seconds": 900,
                          "completion": {"provider": "claude-cli"}}}),
            "completion")
        assert _erfasster_timeout(provider) == 900

    def test_ohne_konfiguration_600(self):
        from sdd_cli.llm.factory import get_completion_provider

        provider = get_completion_provider(_cfg(), "completion")
        assert _erfasster_timeout(provider) == 600


class TestFehlermeldungNenntDenWert:
    def test_timeout_meldung_zeigt_die_sekunden(self):
        provider = ClaudeCliCompletionProvider(timeout=900)

        def fake_run(cmd, **kw):
            raise subprocess.TimeoutExpired(cmd, kw.get("timeout", 0))

        with patch("sdd_cli.llm.providers.claude_cli._find_claude",
                   return_value="/usr/bin/claude"), \
             patch("sdd_cli.llm.providers.claude_cli.subprocess.run", fake_run):
            try:
                provider.complete("p")
            except RuntimeError as exc:
                assert "900s" in str(exc)
            else:
                raise AssertionError("RuntimeError erwartet")
