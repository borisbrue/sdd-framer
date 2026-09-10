# TST-0125 – SDD Config Schema (Unit)
# Spec: SPEC-0027 | Contract: CON-0106

from tool.sdd_cli.config_manager import _validate_business_rules, validate_schema


def _valid_config() -> dict:
    return {
        "llm_pool": {
            "strategy": "local_first",
            "providers": [
                {
                    "id": "ollama-mistral",
                    "type": "local",
                    "model": "mistral:7b",
                    "cost_tier": "cheap",
                    "max_context_tokens": 32000,
                    "base_url": "http://localhost:11434",
                },
                {
                    "id": "claude-sonnet",
                    "type": "remote",
                    "model": "claude-sonnet-4-6",
                    "cost_tier": "standard",
                    "max_context_tokens": 200000,
                    "api_key_env": "ANTHROPIC_API_KEY",
                },
            ],
        },
        "docker": {
            "runtime": "docker",
            "image": "sdd-dev:latest",
            "dockerfile": ".sdd/Dockerfile",
            "max_parallel_containers": 2,
            "resources": {"cpu_limit": "1.0", "memory_limit": "1g"},
            "cleanup": {"on_success": True, "on_failure": False},
            "registry": {"url": "", "auth_env": ""},
            "skip_if_unavailable": False,
        },
    }


class TestTST0125:
    def test_valid_config_passes_schema(self):
        errors = validate_schema(_valid_config())
        assert errors == []

    def test_plaintext_api_key_fails_pattern(self):
        data = _valid_config()
        data["llm_pool"]["providers"][1]["api_key_env"] = "sk-ant-abc123"
        errors = _validate_business_rules(data)
        assert any("api_key_env" in e for e in errors)

    def test_remote_without_api_key_env_fails(self):
        data = _valid_config()
        del data["llm_pool"]["providers"][1]["api_key_env"]
        errors = _validate_business_rules(data)
        assert any("api_key_env" in e for e in errors)

    def test_max_parallel_containers_zero_fails(self):
        data = _valid_config()
        data["docker"]["max_parallel_containers"] = 0
        errors = _validate_business_rules(data)
        assert any("max_parallel_containers" in e for e in errors)

    def test_invalid_memory_limit_format_fails(self):
        data = _valid_config()
        data["docker"]["resources"]["memory_limit"] = "1gb"
        errors = validate_schema(data)
        assert any("memory_limit" in e or "1gb" in e for e in errors)

    def test_invalid_strategy_enum_fails(self):
        data = _valid_config()
        data["llm_pool"]["strategy"] = "random"
        errors = _validate_business_rules(data)
        assert any("strategy" in e for e in errors)

    def test_duplicate_provider_ids_detected(self):
        data = _valid_config()
        dup = dict(data["llm_pool"]["providers"][0])
        data["llm_pool"]["providers"].append(dup)
        errors = _validate_business_rules(data)
        assert any("Doppelte" in e or "doppelt" in e.lower() for e in errors)

    def test_registry_url_without_auth_env_fails(self):
        data = _valid_config()
        data["docker"]["registry"] = {"url": "registry.example.com", "auth_env": ""}
        errors = _validate_business_rules(data)
        assert any("auth_env" in e for e in errors)
