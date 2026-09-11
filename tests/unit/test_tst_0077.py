# TST-0077 – Acceptance: Vollständiger Docker-Spec-Flow (CON-0065/0066/0067)
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from sdd_cli.config import SddConfig
from sdd_cli.dev_container import (
    ContainerRuntime,
    DevContainerManager,
    save_test_result,
)


@pytest.fixture
def cfg(tmp_path):
    (tmp_path / ".sdd").mkdir()
    (tmp_path / ".sdd" / "config.yaml").write_text("docker:\n  image: sdd-dev:latest\n")
    return SddConfig(root=tmp_path, raw={"docker": {"image": "sdd-dev:latest"}})


def _mock_runtime(status: str | None = None) -> MagicMock:
    rt = MagicMock(spec=ContainerRuntime)
    rt.inspect_status.return_value = status
    return rt


def test_full_flow_start_pr_close(cfg):
    """Smoke-Test: start → Tests (Ergebnis simuliert) → pr → close.

    Der Test läuft im Container direkt über die Runtime (`podman exec …`); die
    Finalisierung schließt den Container nach grünen Tests, der Branch bleibt
    (CON-0065 G-05/G-06, v0.4.0).
    """
    spec_id = "SPEC-0021"

    rt = _mock_runtime(status=None)
    with (
        patch("sdd_cli.dev_container._branch_exists", return_value=False),
        patch("sdd_cli.dev_container._git"),
    ):
        DevContainerManager(cfg, runtime=rt).start(spec_id)

    save_test_result(cfg, spec_id, passed=4, total=4)

    mock_strategy = MagicMock()
    rt2 = _mock_runtime()
    with (
        patch("sdd_cli.dev_container._run", return_value=MagicMock(returncode=0, stdout="")),
        patch("sdd_cli.dev_container._git", return_value=MagicMock(returncode=0, stdout="")),
    ):
        DevContainerManager(cfg, pr_strategy=mock_strategy, runtime=rt2).pr(spec_id)

    mock_strategy.create.assert_called_once_with(spec_id, cfg)

    rt3 = _mock_runtime()
    with patch("sdd_cli.dev_container._git") as mock_git:
        DevContainerManager(cfg, runtime=rt3).close(spec_id)

    rt3.stop.assert_called_once_with("sdd-dev-spec-0021")
    rt3.rm.assert_called_once_with("sdd-dev-spec-0021")
    mock_git.assert_not_called()  # der Branch bleibt
