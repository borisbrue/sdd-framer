# TST-0078 – Performance: Container-Start SLO (CON-0068)
from __future__ import annotations

import pytest


def test_slo_placeholder():
    """SLO-Test erfordert ein laufendes Docker-Image (sdd-dev:latest).

    In der Unit-Test-Suite wird nur sichergestellt, dass das Modul
    importierbar ist. Der echte Zeitmessungs-Test läuft im Dev-Container
    via 'sdd dev exec SPEC-0021 pytest tests/performance/'.
    """
    from sdd_cli.dev_container import DevContainerManager, container_name, branch_name
    assert container_name("SPEC-0021") == "sdd-dev-spec-0021"
    assert branch_name("SPEC-0021") == "dev/SPEC-0021"
