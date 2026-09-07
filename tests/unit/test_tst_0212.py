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

    def test_blueprint_config_is_keyless(self) -> None:
        # FR-06: das Blueprint darf den keyfreien Builtin nicht wieder ueberschreiben.
        # Ohne diesen Test bleibt FR-01 erfuellt, waehrend jedes neue Projekt
        # trotzdem einen ANTHROPIC_API_KEY verlangt.
        import yaml

        blueprint = (
            Path(__file__).resolve().parents[2]
            / "tool" / "sdd_cli" / "blueprint" / "config.yaml"
        )
        llm = yaml.safe_load(blueprint.read_text(encoding="utf-8")).get("llm") or {}
        key_provider = {
            name: block.get("provider")
            for name, block in llm.items()
            if isinstance(block, dict) and block.get("provider") == "anthropic"
        }
        assert not key_provider, (
            f"Blueprint setzt Key-Provider fuer {sorted(key_provider)} — "
            "ein neues Projekt waere ohne ANTHROPIC_API_KEY nicht arbeitsfaehig."
        )

    def test_blueprint_completion_is_claude_cli(self) -> None:
        # FR-06: der wichtigste Einzelfall, weil completion die meisten Aufrufer hat.
        import yaml

        blueprint = (
            Path(__file__).resolve().parents[2]
            / "tool" / "sdd_cli" / "blueprint" / "config.yaml"
        )
        llm = yaml.safe_load(blueprint.read_text(encoding="utf-8"))["llm"]
        assert llm["completion"]["provider"] == "claude-cli"
