# TST-0104 – CON-0094: PWA Dashboard SLO — GET /api/specs p95 < 200ms
# Contract: CON-0094
# Spec: SPEC-0024
from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from routes.specs import router


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    return app


def _mock_config(tmp_path: Path, n_specs: int = 5) -> MagicMock:
    specs_dir = tmp_path / ".sdd" / "specs"
    specs_dir.mkdir(parents=True)
    for i in range(1, n_specs + 1):
        spec_id = f"SPEC-{i:04d}"
        (specs_dir / f"{spec_id}-test.md").write_text(
            f"---\nid: {spec_id}\ntitle: Test {i}\nstatus: draft\npriority: medium\n---\n",
            encoding="utf-8",
        )
    cfg = MagicMock()
    cfg.root = tmp_path
    cfg.specs_dir = specs_dir
    return cfg


class TestTST0104:
    # CON-0094: GET /api/specs p95 < 200ms (20 Messungen)
    def test_get_specs_p95_under_200ms(self, tmp_path: Path) -> None:
        samples = 20
        latencies: list[float] = []
        cfg = _mock_config(tmp_path, n_specs=5)

        with patch("routes.specs.get_config", return_value=cfg):
            client = TestClient(_make_app())
            for _ in range(samples):
                t0 = time.monotonic()
                client.get("/specs")
                latencies.append(time.monotonic() - t0)

        latencies.sort()
        p95_idx = int(len(latencies) * 0.95)
        p95 = latencies[min(p95_idx, len(latencies) - 1)]
        assert p95 < 0.2, f"GET /api/specs p95={p95:.3f}s überschreitet 200ms SLO"
