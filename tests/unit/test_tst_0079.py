# TST-0079 – ContainerRuntime: DockerRuntime und PodmanRuntime CLI delegation
# Contract: CON-0069 (dev-stack-lifecycle)
# Spec: SPEC-0022
from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, call, patch

import pytest

from sdd_cli.dev_container import DockerRuntime, PodmanRuntime, get_runtime, validate_docker_config
from sdd_cli.config import SddConfig


def _mock_run(returncode: int = 0, stdout: str = "") -> MagicMock:
    m = MagicMock(spec=subprocess.CompletedProcess)
    m.returncode = returncode
    m.stdout = stdout
    return m


class TestTST0079:
    # TC-01: DockerRuntime.build delegiert korrekte CLI-Argumente
    def test_docker_runtime_build(self) -> None:
        rt = DockerRuntime()
        with patch("subprocess.run", return_value=_mock_run()) as mock:
            rt.build("sdd-dev:latest", ".sdd/Dockerfile")
        mock.assert_called_once_with(
            ["docker", "build", "-t", "sdd-dev:latest", "-f", ".sdd/Dockerfile", "."],
            capture_output=False,
            text=True,
            check=True,
        )

    # TC-02: PodmanRuntime.build delegiert korrekte CLI-Argumente
    def test_podman_runtime_build(self) -> None:
        rt = PodmanRuntime()
        with patch("subprocess.run", return_value=_mock_run()) as mock:
            rt.build("sdd-dev:latest", ".sdd/Dockerfile")
        mock.assert_called_once_with(
            ["podman", "build", "-t", "sdd-dev:latest", "-f", ".sdd/Dockerfile", "."],
            capture_output=False,
            text=True,
            check=True,
        )

    # TC-03: DockerRuntime.push delegiert korrekte CLI-Argumente
    def test_docker_runtime_push(self) -> None:
        rt = DockerRuntime()
        with patch("subprocess.run", return_value=_mock_run()) as mock:
            rt.push("registry.example.com/sdd/sdd-dev:latest")
        mock.assert_called_once_with(
            ["docker", "push", "registry.example.com/sdd/sdd-dev:latest"],
            capture_output=False,
            text=True,
            check=True,
        )

    # TC-04: DockerRuntime.compose_up delegiert korrekte CLI-Argumente
    def test_docker_runtime_compose_up(self) -> None:
        rt = DockerRuntime()
        with patch("subprocess.run", return_value=_mock_run()) as mock:
            rt.compose_up(".sdd/docker-compose.yml")
        mock.assert_called_once_with(
            ["docker", "compose", "-f", ".sdd/docker-compose.yml", "up", "-d"],
            capture_output=False,
            text=True,
            check=True,
        )

    # TC-05: PodmanRuntime.run_container enthält --userns=keep-id
    def test_podman_run_container_userns(self) -> None:
        rt = PodmanRuntime()
        with patch("subprocess.run", return_value=_mock_run()) as mock:
            rt.run_container(
                "sdd-dev-spec-0022",
                "sdd-dev:latest",
                volume="/proj:/workspace",
                env={"SPEC_ID": "SPEC-0022"},
            )
        args = mock.call_args[0][0]
        assert "--userns=keep-id" in args
        assert "podman" == args[0]

    # TC-06: DockerRuntime.run_container enthält kein --userns=keep-id
    def test_docker_run_container_no_userns(self) -> None:
        rt = DockerRuntime()
        with patch("subprocess.run", return_value=_mock_run()) as mock:
            rt.run_container(
                "sdd-dev-spec-0022",
                "sdd-dev:latest",
                volume="/proj:/workspace",
                env={},
            )
        args = mock.call_args[0][0]
        assert "--userns=keep-id" not in args

    # TC-07: get_runtime liefert DockerRuntime für docker
    def test_get_runtime_docker(self) -> None:
        cfg = MagicMock(spec=SddConfig)
        cfg.raw = {"docker": {"runtime": "docker"}}
        rt = get_runtime(cfg)
        assert isinstance(rt, DockerRuntime)

    # TC-08: get_runtime liefert PodmanRuntime für podman
    def test_get_runtime_podman(self) -> None:
        cfg = MagicMock(spec=SddConfig)
        cfg.raw = {"docker": {"runtime": "podman"}}
        rt = get_runtime(cfg)
        assert isinstance(rt, PodmanRuntime)

    # TC-09: ungültige Runtime → Fehlermeldung + sys.exit
    def test_get_runtime_invalid(self) -> None:
        cfg = MagicMock(spec=SddConfig)
        cfg.raw = {"docker": {"runtime": "nerdctl"}}
        with pytest.raises(SystemExit):
            get_runtime(cfg)

    # TC-10: validate_docker_config akzeptiert minimale Config
    def test_validate_minimal_config(self) -> None:
        validate_docker_config({})  # muss ohne Exception durchlaufen

    # TC-11: validate_docker_config lehnt ungültige Runtime ab
    def test_validate_invalid_runtime(self) -> None:
        with pytest.raises(ValueError, match="nerdctl"):
            validate_docker_config({"runtime": "nerdctl"})

    # TC-12: validate_docker_config lehnt max_lines=0 ab
    def test_validate_max_lines_zero(self) -> None:
        with pytest.raises(ValueError, match="max_lines"):
            validate_docker_config({"log_stream": {"max_lines": 0}})

    # TC-13: validate_docker_config lehnt max_lines>10000 ab
    def test_validate_max_lines_too_large(self) -> None:
        with pytest.raises(ValueError, match="max_lines"):
            validate_docker_config({"log_stream": {"max_lines": 10001}})
