# TST-0123 – Config-Commands set/get/show/validate (Unit)
# Spec: SPEC-0027 | Contract: CON-0104

from pathlib import Path

import pytest
import yaml

from tool.sdd_cli.config_manager import ConfigManager, ConfigValidationError


def _make_config(tmp_path: Path, data: dict) -> Path:
    p = tmp_path / "config.yaml"
    p.write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")
    return p


def _base_data() -> dict:
    return {
        "docker": {
            "runtime": "docker",
            "image": "sdd-dev:latest",
            "dockerfile": ".sdd/Dockerfile",
            "max_parallel_containers": 2,
            "registry": {"url": "", "auth_env": ""},
        }
    }


class TestTST0123:
    def test_set_scalar_value_via_dot_notation(self, tmp_path):
        p = _make_config(tmp_path, _base_data())
        mgr = ConfigManager(p)
        mgr.set("docker.max_parallel_containers", 4)
        reloaded = yaml.safe_load(p.read_text())
        assert reloaded["docker"]["max_parallel_containers"] == 4

    def test_set_array_element_via_index_notation(self, tmp_path):
        data = _base_data()
        data["llm_pool"] = {
            "strategy": "cost_first",
            "providers": [{"id": "p1", "type": "remote", "model": "m", "cost_tier": "cheap", "max_context_tokens": 1000, "api_key_env": "OLD_KEY"}],
        }
        p = _make_config(tmp_path, data)
        mgr = ConfigManager(p)
        mgr.set("llm_pool.providers[0].api_key_env", "ANTHROPIC_API_KEY")
        reloaded = yaml.safe_load(p.read_text())
        assert reloaded["llm_pool"]["providers"][0]["api_key_env"] == "ANTHROPIC_API_KEY"

    def test_get_existing_key_returns_value(self, tmp_path):
        p = _make_config(tmp_path, _base_data())
        mgr = ConfigManager(p)
        assert mgr.get("docker.max_parallel_containers") == 2

    def test_get_nonexistent_key_returns_none_exit_1(self, tmp_path):
        p = _make_config(tmp_path, _base_data())
        mgr = ConfigManager(p)
        assert mgr.get("llm_pool.providers[5].model") is None

    def test_show_returns_all_sections(self, tmp_path):
        p = _make_config(tmp_path, _base_data())
        mgr = ConfigManager(p)
        output = mgr.show()
        assert "docker" in output

    def test_show_section_returns_only_section(self, tmp_path):
        data = _base_data()
        data["llm_pool"] = {"strategy": "cost_first", "providers": []}
        p = _make_config(tmp_path, data)
        mgr = ConfigManager(p)
        output = mgr.show(section="llm_pool")
        assert "llm_pool" in output
        assert "docker" not in output

    def test_validate_invalid_config_returns_error_list(self, tmp_path):
        data = _base_data()
        data["docker"]["max_parallel_containers"] = -1
        p = _make_config(tmp_path, data)
        mgr = ConfigManager(p)
        errors = mgr.validate()
        assert len(errors) >= 1
        assert any("max_parallel_containers" in e for e in errors)

    def test_set_invalid_value_leaves_yaml_unchanged(self, tmp_path):
        p = _make_config(tmp_path, _base_data())
        original = p.read_text()
        mgr = ConfigManager(p)
        with pytest.raises((ConfigValidationError, Exception)):
            mgr.set("docker.max_parallel_containers", -1)
        assert p.read_text() == original
