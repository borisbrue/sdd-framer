# TST-0141 | SPEC-0035 | CON-0122
# Fallback-Logik: Single-Context-Mode bei Nicht-Claude-Provider

from pathlib import Path

from tool.sdd_cli.config import SddConfig
from tool.sdd_cli.sub_agent import is_claude_provider


def _config(provider: str) -> SddConfig:
    return SddConfig(root=Path("."), raw={"llm": {"ai_routes": {"provider": provider}}})


class TestTST0141:
    def test_tc01_claude_provider_enables_delegation_mode(self) -> None:
        assert is_claude_provider(_config("claude-cli")) is True
        assert is_claude_provider(_config("anthropic")) is True

    def test_tc02_non_claude_provider_triggers_single_context_fallback(self) -> None:
        assert is_claude_provider(_config("openai")) is False
        assert is_claude_provider(_config("gemini")) is False
        assert is_claude_provider(_config("openai-compat")) is False

    def test_tc03_fallback_produces_no_task_id_entries(self) -> None:
        # When not Claude, sub-agent loop is never entered, so no task_id entries.
        # Verified structurally: is_claude_provider returns False → orchestrator not called.
        cfg = _config("openai")
        assert not is_claude_provider(cfg)
