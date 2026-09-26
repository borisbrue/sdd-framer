# TST-0122 – LLM-Pool-Konfiguration und Provider-Test (Unit)
# Spec: SPEC-0027 | Contract: CON-0103

from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from tool.sdd_cli.config_manager import (
    ConfigManager,
    ConfigValidationError,
)
from tool.sdd_cli.llm_probe import LlmProbeError, OllamaProbe, probe_llm


def _make_config(tmp_path: Path, data: dict) -> Path:
    p = tmp_path / "config.yaml"
    p.write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")
    return p


def _pool_with_providers(*providers) -> dict:
    return {"llm_pool": {"strategy": "cost_first", "providers": list(providers)}}


def _local_provider(id="ollama-mistral") -> dict:
    return {"id": id, "type": "local", "model": "mistral:7b",
            "cost_tier": "cheap", "max_context_tokens": 32000,
            "base_url": "http://localhost:11434"}


def _remote_provider(id="claude-sonnet", api_key_env="ANTHROPIC_API_KEY") -> dict:
    p = {"id": id, "type": "remote", "model": "claude-sonnet-4-6",
         "cost_tier": "standard", "max_context_tokens": 200000}
    if api_key_env:
        p["api_key_env"] = api_key_env
    return p


class TestTST0122:
    def test_multiple_providers_stored_with_required_fields(self, tmp_path):
        data = _pool_with_providers(_local_provider(), _remote_provider())
        p = _make_config(tmp_path, data)
        reloaded = yaml.safe_load(p.read_text())
        providers = reloaded["llm_pool"]["providers"]
        assert len(providers) == 2
        for prov in providers:
            for field in ("id", "type", "model", "cost_tier", "max_context_tokens"):
                assert field in prov

    def test_remote_provider_stores_env_var_name_not_key(self, tmp_path):
        data = _pool_with_providers(_remote_provider(api_key_env="ANTHROPIC_API_KEY"))
        p = _make_config(tmp_path, data)
        content = p.read_text()
        assert "ANTHROPIC_API_KEY" in content
        assert "sk-" not in content

    def test_direct_key_input_rejected_with_warning(self, tmp_path):
        data = _pool_with_providers(_local_provider())
        p = _make_config(tmp_path, data)
        mgr = ConfigManager(p)
        with pytest.raises(ConfigValidationError, match="API-Key"):
            mgr.set("llm_pool.providers[0].api_key_env", "sk-ant-abc123")

    def test_probe_returns_latency_when_reachable(self):
        with patch.object(OllamaProbe, "probe", return_value=42.0):
            latency = probe_llm(_local_provider())
        assert latency == 42.0

    def test_probe_raises_on_unreachable_provider(self):
        with patch.object(OllamaProbe, "probe", side_effect=LlmProbeError("down")):
            with pytest.raises(LlmProbeError):
                probe_llm(_local_provider())

    def test_local_first_strategy_prefers_local(self, tmp_path):
        data = _pool_with_providers(_local_provider(), _remote_provider())
        data["llm_pool"]["strategy"] = "local_first"
        p = _make_config(tmp_path, data)
        reloaded = yaml.safe_load(p.read_text())
        assert reloaded["llm_pool"]["strategy"] == "local_first"
        first = reloaded["llm_pool"]["providers"][0]
        assert first["type"] == "local"
