# TST-0081 – docker: Config-Schema Validierung
# Contract: CON-0072 (docker-config-schema)
# Spec: SPEC-0022
from __future__ import annotations

import pytest

from sdd_cli.dev_container import validate_docker_config


class TestTST0081:
    # CON-0072 INV-01: Ungültige Runtime → ValueError
    def test_invalid_runtime_raises(self) -> None:
        with pytest.raises(ValueError, match="nerdctl"):
            validate_docker_config({"runtime": "nerdctl"})

    # CON-0072 INV-01: Weitere ungültige Runtime
    def test_containerd_runtime_raises(self) -> None:
        with pytest.raises(ValueError, match="containerd"):
            validate_docker_config({"runtime": "containerd"})

    # CON-0072 INV-02: Minimale Config (leer) ist valide
    def test_minimal_config_valid(self) -> None:
        validate_docker_config({})

    # CON-0072 INV-02: docker valide
    def test_runtime_docker_valid(self) -> None:
        validate_docker_config({"runtime": "docker"})

    # CON-0072 INV-02: podman valide
    def test_runtime_podman_valid(self) -> None:
        validate_docker_config({"runtime": "podman"})

    # CON-0072 INV-03: max_lines=0 ungültig
    def test_max_lines_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="max_lines"):
            validate_docker_config({"log_stream": {"max_lines": 0}})

    # CON-0072 INV-03: max_lines=10001 ungültig
    def test_max_lines_too_large_raises(self) -> None:
        with pytest.raises(ValueError, match="max_lines"):
            validate_docker_config({"log_stream": {"max_lines": 10001}})

    # CON-0072 INV-03: max_lines=1 (Grenzwert) valide
    def test_max_lines_min_boundary_valid(self) -> None:
        validate_docker_config({"log_stream": {"max_lines": 1}})

    # CON-0072 INV-03: max_lines=10000 (Grenzwert) valide
    def test_max_lines_max_boundary_valid(self) -> None:
        validate_docker_config({"log_stream": {"max_lines": 10000}})

    # Vollständige valide Config
    def test_full_config_valid(self) -> None:
        validate_docker_config({
            "runtime": "podman",
            "image": "my-dev:1.0",
            "dockerfile": ".sdd/Dockerfile",
            "registry": {
                "url": "registry.example.com/sdd",
                "auth_env": "REGISTRY_TOKEN",
            },
            "compose_file": ".sdd/docker-compose.yml",
            "log_stream": {
                "enabled": True,
                "max_lines": 500,
            },
        })
