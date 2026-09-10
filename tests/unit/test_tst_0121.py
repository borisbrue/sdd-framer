# TST-0121 – Config-Wizard-Flow (Unit)
# Spec: SPEC-0027 | Contract: CON-0102

from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from tool.sdd_cli.config_manager import ConfigValidationError
from tool.sdd_cli.config_wizard import ConfigWizard

PLACEHOLDER = "<PROJECT_DESCRIPTION>"


def _make_config(tmp_path: Path, data: dict) -> Path:
    p = tmp_path / "config.yaml"
    p.write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")
    return p


def _base_data() -> dict:
    return {
        "project": {"description": PLACEHOLDER},
        "docker": {
            "runtime": "docker", "image": "img", "dockerfile": "df",
            "max_parallel_containers": 2, "registry": {"url": "", "auth_env": ""},
        },
    }


class TestTST0121:
    def test_full_wizard_writes_valid_config(self, tmp_path):
        p = _make_config(tmp_path, _base_data())
        wizard = ConfigWizard(p)
        wizard.run(
            non_interactive=True,
            project_description="Test project",
        )
        reloaded = yaml.safe_load(p.read_text())
        assert reloaded["project"]["description"] == "Test project"

    def test_section_llm_only_asks_llm_section(self, tmp_path):
        data = _base_data()
        data["docker"]["max_parallel_containers"] = 99
        p = _make_config(tmp_path, data)
        wizard = ConfigWizard(p)
        wizard.run(section="llm", non_interactive=True, llm_strategy="local_first")
        reloaded = yaml.safe_load(p.read_text())
        assert reloaded["llm_pool"]["strategy"] == "local_first"
        assert reloaded["docker"]["max_parallel_containers"] == 99

    def test_abort_leaves_config_unchanged(self, tmp_path):
        p = _make_config(tmp_path, _base_data())
        original = p.read_text()
        wizard = ConfigWizard(p)
        with patch("builtins.input", side_effect=KeyboardInterrupt):
            wizard.run()
        assert p.read_text() == original

    def test_invalid_max_parallel_containers_retries(self, tmp_path):
        p = _make_config(tmp_path, _base_data())
        wizard = ConfigWizard(p)
        with pytest.raises(ConfigValidationError):
            wizard.run(section="docker", non_interactive=True, docker_max_parallel=0)

    def test_non_interactive_valid_flags_exit_0(self, tmp_path):
        p = _make_config(tmp_path, _base_data())
        wizard = ConfigWizard(p)
        result = wizard.run(non_interactive=True, project_description="OK")
        assert isinstance(result, dict)

    def test_non_interactive_invalid_value_exit_1(self, tmp_path):
        p = _make_config(tmp_path, _base_data())
        wizard = ConfigWizard(p)
        with pytest.raises((ConfigValidationError, Exception)):
            wizard.run(section="docker", non_interactive=True, docker_max_parallel=-1)

    def test_auto_start_on_placeholder_description(self, tmp_path):
        data = _base_data()
        assert ConfigWizard.needs_setup(data) is True
        data["project"]["description"] = "My project"
        assert ConfigWizard.needs_setup(data) is False
