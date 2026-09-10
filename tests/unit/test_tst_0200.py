"""TST-0200 – task_routing Konfigurationsschema – Defaults, Validation, SPEC-0008 (Unit)
Spec: SPEC-0045 · Contract: CON-0174
"""
import pytest

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestTaskRoutingConfigSchema:
    def test_defaults_when_block_missing(self):
        """INV-02: Fehlt task_routing-Block → alle Defaults korrekt."""
        from tool.sdd_cli.task_routing.config import load_task_routing_config

        config = load_task_routing_config({})
        assert config.enabled is False
        assert config.complexity_threshold == 30
        assert config.max_retries == 3
        assert config.max_concurrent == 3

    def test_explicit_values_are_applied(self):
        """Explizite Werte überschreiben Defaults."""
        from tool.sdd_cli.task_routing.config import load_task_routing_config

        raw = {"task_routing": {
            "enabled": True,
            "complexity_threshold": 50,
            "max_retries": 5,
            "max_concurrent": 2,
        }}
        config = load_task_routing_config(raw)
        assert config.enabled is True
        assert config.complexity_threshold == 50
        assert config.max_retries == 5
        assert config.max_concurrent == 2

    def test_enabled_without_local_llm_acts_as_disabled(self):
        """INV-01: enabled=true aber llm.local_llm fehlt → local_llm_configured=False."""
        from tool.sdd_cli.task_routing.config import load_task_routing_config

        raw = {"task_routing": {"enabled": True}}
        config = load_task_routing_config(raw)
        assert config.local_llm_configured is False

    def test_local_llm_configured_when_present(self):
        """llm.local_llm vorhanden → local_llm_configured=True."""
        from tool.sdd_cli.task_routing.config import load_task_routing_config

        raw = {
            "task_routing": {"enabled": True},
            "llm": {
                "local_llm": {
                    "provider": "openai-compat",
                    "base_url": "http://localhost:11434/v1",
                    "model": "qwen2.5-coder:14b",
                }
            },
        }
        config = load_task_routing_config(raw)
        assert config.local_llm_configured is True

    def test_complexity_threshold_below_zero_raises(self):
        """INV-03: threshold < 0 → ValueError."""
        from tool.sdd_cli.task_routing.config import load_task_routing_config

        with pytest.raises(ValueError, match="complexity_threshold"):
            load_task_routing_config({"task_routing": {"complexity_threshold": -1}})

    def test_complexity_threshold_above_100_raises(self):
        """INV-03: threshold > 100 → ValueError."""
        from tool.sdd_cli.task_routing.config import load_task_routing_config

        with pytest.raises(ValueError, match="complexity_threshold"):
            load_task_routing_config({"task_routing": {"complexity_threshold": 101}})

    def test_complexity_threshold_boundaries_valid(self):
        """Grenzwerte 0 und 100 sind valide."""
        from tool.sdd_cli.task_routing.config import load_task_routing_config

        for value in (0, 100):
            config = load_task_routing_config({"task_routing": {"complexity_threshold": value}})
            assert config.complexity_threshold == value

    def test_unsupported_provider_raises(self):
        """INV-04: llm.local_llm.provider != openai-compat → ValueError in v0.1.0."""
        from tool.sdd_cli.task_routing.config import load_task_routing_config

        raw = {
            "llm": {
                "local_llm": {
                    "provider": "anthropic",  # nicht erlaubt für local_llm
                    "model": "claude-haiku-4-5-20251001",
                }
            }
        }
        with pytest.raises(ValueError, match="openai-compat"):
            load_task_routing_config(raw)

    def test_local_llm_inherits_model_from_completion_default(self):
        """INV-05: llm.local_llm ohne model erbt von llm.completion.model (SPEC-0008)."""
        from tool.sdd_cli.task_routing.config import load_task_routing_config

        raw = {
            "llm": {
                "completion": {"provider": "anthropic", "model": "claude-haiku-4-5-20251001"},
                "local_llm": {
                    "provider": "openai-compat",
                    "base_url": "http://localhost:11434/v1",
                    # kein model-Feld → erbt von llm.completion.model
                },
            }
        }
        config = load_task_routing_config(raw)
        assert config.local_llm_model == "claude-haiku-4-5-20251001"

    def test_local_llm_missing_base_url_raises(self):
        """openai-compat ohne base_url → ValueError (SPEC-0008 Pflichtfeld)."""
        from tool.sdd_cli.task_routing.config import load_task_routing_config

        raw = {
            "task_routing": {"enabled": True},
            "llm": {
                "local_llm": {
                    "provider": "openai-compat",
                    "model": "qwen2.5-coder:14b",
                    # base_url fehlt
                }
            },
        }
        with pytest.raises(ValueError, match="base_url"):
            load_task_routing_config(raw)
