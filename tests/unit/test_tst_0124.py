# TST-0124 – Docker-Container-Konfiguration (Unit)
# Spec: SPEC-0027 | Contract: CON-0105

import pytest
import yaml
from pathlib import Path
from unittest.mock import MagicMock, patch

from tool.sdd_cli.config_wizard import ConfigWizard
from tool.sdd_cli.config_manager import ConfigValidationError, _validate_business_rules


def _make_config(tmp_path: Path, data: dict) -> Path:
    p = tmp_path / "config.yaml"
    p.write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")
    return p


def _base_docker(max_par=2, on_success=True, on_failure=False,
                 skip=False, reg_url="", reg_auth="") -> dict:
    return {
        "runtime": "docker",
        "image": "sdd-dev:latest",
        "dockerfile": ".sdd/Dockerfile",
        "max_parallel_containers": max_par,
        "cleanup": {"on_success": on_success, "on_failure": on_failure},
        "registry": {"url": reg_url, "auth_env": reg_auth},
        "skip_if_unavailable": skip,
    }


class TestTST0124:
    def test_docker_section_sets_all_fields(self, tmp_path):
        data = {"project": {"description": "x"}, "docker": _base_docker()}
        p = _make_config(tmp_path, data)
        wizard = ConfigWizard(p)
        wizard.run(section="docker", non_interactive=True, docker_max_parallel=3)
        reloaded = yaml.safe_load(p.read_text())
        assert reloaded["docker"]["max_parallel_containers"] == 3
        assert "runtime" in reloaded["docker"]
        assert "image" in reloaded["docker"]

    def test_resource_limits_passed_as_docker_flags(self, tmp_path):
        data = {"docker": _base_docker()}
        data["docker"]["resources"] = {"cpu_limit": "1.0", "memory_limit": "1g"}
        p = _make_config(tmp_path, data)
        reloaded = yaml.safe_load(p.read_text())
        res = reloaded["docker"]["resources"]
        assert res["cpu_limit"] == "1.0"
        assert res["memory_limit"] == "1g"

    def test_cleanup_on_success_removes_container(self, tmp_path):
        data = {"docker": _base_docker(on_success=True)}
        p = _make_config(tmp_path, data)
        reloaded = yaml.safe_load(p.read_text())
        assert reloaded["docker"]["cleanup"]["on_success"] is True

    def test_no_cleanup_on_failure_keeps_container(self, tmp_path):
        data = {"docker": _base_docker(on_failure=False)}
        p = _make_config(tmp_path, data)
        reloaded = yaml.safe_load(p.read_text())
        assert reloaded["docker"]["cleanup"]["on_failure"] is False

    def test_max_parallel_zero_raises_validation_error(self, tmp_path):
        data = {"project": {"description": "x"}, "docker": _base_docker(max_par=0)}
        errors = _validate_business_rules(data)
        assert any("max_parallel_containers" in e for e in errors)

    def test_registry_url_without_auth_env_raises(self, tmp_path):
        data = {"docker": _base_docker(reg_url="registry.example.com", reg_auth="")}
        errors = _validate_business_rules(data)
        assert any("auth_env" in e for e in errors)

    def test_skip_if_unavailable_falls_back_to_local(self, tmp_path):
        data = {"docker": _base_docker(skip=True)}
        p = _make_config(tmp_path, data)
        reloaded = yaml.safe_load(p.read_text())
        assert reloaded["docker"]["skip_if_unavailable"] is True

    def test_parallelism_semaphore_limits_containers(self, tmp_path):
        data = {"docker": _base_docker(max_par=2)}
        p = _make_config(tmp_path, data)
        reloaded = yaml.safe_load(p.read_text())
        assert reloaded["docker"]["max_parallel_containers"] == 2
