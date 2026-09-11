# TST-0077 – Acceptance: Docker-Spec-Flow (CON-0065)
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from sdd_cli.config import SddConfig
from sdd_cli.dev_container import (
    ContainerRuntime,
    DevContainerManager,
    _load_last_test_result,
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


def test_full_flow_start_tests_close(cfg):
    """Smoke-Test: start → Testergebnis festhalten → close.

    Die Tests laufen im Container direkt über die Runtime (`podman exec …`). Den
    PR legt die Finalisierung an, das prüfen test_finalize_push.py und
    test_finalize_container.py. Der frühere Schritt `pr()` bediente das mit
    SPEC-0044 entfernte `sdd dev pr` und ist mit CON-0066 (deprecated, #123)
    entfallen.
    """
    spec_id = "SPEC-0021"

    rt = _mock_runtime(status=None)
    with (
        patch("sdd_cli.dev_container._branch_exists", return_value=False),
        patch("sdd_cli.dev_container._git"),
    ):
        DevContainerManager(cfg, runtime=rt).start(spec_id)
    rt.run_container.assert_called_once()

    save_test_result(cfg, spec_id, passed=4, total=4)
    assert _load_last_test_result(cfg, spec_id) == ("passed", 4, 4)

    rt2 = _mock_runtime()
    with patch("sdd_cli.dev_container._git") as mock_git:
        DevContainerManager(cfg, runtime=rt2).close(spec_id)

    rt2.stop.assert_called_once_with("sdd-dev-spec-0021")
    rt2.rm.assert_called_once_with("sdd-dev-spec-0021")
    mock_git.assert_not_called()  # der Branch bleibt
