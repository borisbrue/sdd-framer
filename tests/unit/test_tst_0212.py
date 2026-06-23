# TST-0212 – Provider-Auflösung: keyfreier Default + Fail-Loud
# Spec: SPEC-0050 · Contract: CON-0186
from pathlib import Path
from unittest.mock import patch

from sdd_cli.config import SddConfig
from sdd_cli.llm.factory import get_completion_provider
from sdd_cli.llm.providers.claude_cli import ClaudeCliCompletionProvider
from sdd_cli.llm.providers.anthropic import AnthropicCompletionProvider


def _cfg(raw: dict) -> SddConfig:
    return SddConfig(root=Path("/tmp"), raw=raw)


class TestTST0212:
    def test_completion_defaults_to_claude_cli(self) -> None:
        # FR-01 / INV-01: ohne llm-Konfiguration -> claude-cli (kein anthropic, kein Key)
        provider = get_completion_provider(_cfg({}), "completion")
        assert isinstance(provider, ClaudeCliCompletionProvider)

    def test_anthropic_optin_honored(self) -> None:
        # FR-05 / INV-02: explizit konfigurierter anthropic-Provider wird verwendet
        raw = {"llm": {"completion": {"provider": "anthropic", "api_key": "sk-test"}}}
        with patch.object(AnthropicCompletionProvider, "__init__", return_value=None):
            provider = get_completion_provider(_cfg(raw), "completion")
        assert isinstance(provider, AnthropicCompletionProvider)

    def test_no_silent_fallback_to_claude_cli(self) -> None:
        # FR-02 / INV-03: explizit anthropic bleibt anthropic - kein stiller Wechsel
        raw = {"llm": {"completion": {"provider": "anthropic"}}}
        with patch.object(AnthropicCompletionProvider, "__init__", return_value=None):
            provider = get_completion_provider(_cfg(raw), "completion")
        assert not isinstance(provider, ClaudeCliCompletionProvider)
        assert isinstance(provider, AnthropicCompletionProvider)

    def test_evaluator_stays_claude_cli(self) -> None:
        # INV-04: Holdout-Gate-Regression - evaluator auf claude-cli bleibt claude-cli
        raw = {"llm": {"evaluator": {"provider": "claude-cli"}}}
        provider = get_completion_provider(_cfg(raw), "evaluator")
        assert isinstance(provider, ClaudeCliCompletionProvider)
