# TST-0150 – local_agent Config-Schema (CON-0128)
# Spec: SPEC-0036 | Level: contract | Contract: CON-0128

import json
import os
from pathlib import Path

import jsonschema
import pytest

from sdd_cli.local_agent import LocalAgentConfig

_SCHEMA_PATH = Path(__file__).parents[2] / ".sdd/contracts/data/local-agent-config.schema.json"


@pytest.fixture(scope="module")
def schema() -> dict:
    return json.loads(_SCHEMA_PATH.read_text())


class TestTST0150:
    def test_valid_enabled_config(self, schema: dict) -> None:
        cfg = {
            "enabled": True,
            "proxy_url": "http://localhost:4000",
            "model": "llama3.1:8b",
            "context_window": 131072,
            "context_reserve_tokens": 8192,
            "max_parallel_local": 4,
            "max_parallel_cloud": 2,
            "api_key": "local-key",
            "health_check": True,
        }
        jsonschema.validate(cfg, schema)

    def test_disabled_no_proxy_required(self, schema: dict) -> None:
        # INV-01: enabled=false → proxy_url/model/context_window nicht erforderlich
        cfg = {"enabled": False}
        jsonschema.validate(cfg, schema)

    def test_missing_proxy_url_when_enabled_fails(self, schema: dict) -> None:
        cfg = {
            "enabled": True,
            "model": "llama3.1:8b",
            "context_window": 131072,
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(cfg, schema)

    def test_invalid_proxy_url_pattern(self, schema: dict) -> None:
        # INV-02: proxy_url muss http:// oder https:// sein
        cfg = {
            "enabled": True,
            "proxy_url": "ftp://localhost:4000",
            "model": "llama3.1:8b",
            "context_window": 131072,
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(cfg, schema)

    def test_context_window_must_be_positive(self, schema: dict) -> None:
        # INV-03: context_window > 0
        cfg = {
            "enabled": True,
            "proxy_url": "http://localhost:4000",
            "model": "llama3.1:8b",
            "context_window": 0,
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(cfg, schema)

    def test_env_var_resolution(self, monkeypatch) -> None:
        # INV-05: ${ENV_VAR} wird via os.environ aufgelöst
        monkeypatch.setenv("MY_PROXY_KEY", "resolved-key")
        cfg = {
            "enabled": True,
            "proxy_url": "http://localhost:4000",
            "model": "llama3.1:8b",
            "context_window": 131072,
            "api_key": "${MY_PROXY_KEY}",
        }
        result = LocalAgentConfig.from_dict(cfg)
        assert result.api_key == "resolved-key"

    def test_missing_section_fallback(self) -> None:
        # INV-01: fehlende Sektion → None zurück (Cloud-Only-Fallback)
        class FakeConfig:
            raw = {}  # no local_agent key

        result = LocalAgentConfig.from_sdd_config(FakeConfig())
        assert result is None

    def test_additional_properties_rejected(self, schema: dict) -> None:
        cfg = {
            "enabled": False,
            "unknown_field": "oops",
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(cfg, schema)
