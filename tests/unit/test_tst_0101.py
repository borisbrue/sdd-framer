# TST-0101 – CON-0091: PWA Setup-Flow — GET /api/specs Validierungs-Endpoint
# Contract: CON-0091
# Spec: SPEC-0024
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from routes.specs import router


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    return app


def _mock_config_with_specs(tmp_path: Path) -> MagicMock:
    """Erstellt eine minimale SddConfig mit einer Spec-Datei."""
    sdd_dir = tmp_path / ".sdd"
    specs_dir = sdd_dir / "specs"
    specs_dir.mkdir(parents=True)
    (specs_dir / "SPEC-0024-test.md").write_text(
        "---\nid: SPEC-0024\ntitle: Test Spec\nstatus: draft\npriority: high\n---\n# Test\n",
        encoding="utf-8",
    )
    cfg = MagicMock()
    cfg.root = tmp_path
    cfg.specs_dir = specs_dir
    return cfg


class TestTST0101:
    # CON-0091: Setup-Flow-Validierung — GET /api/specs antwortet mit HTTP 200
    def test_get_specs_returns_200(self, tmp_path: Path) -> None:
        cfg = _mock_config_with_specs(tmp_path)
        with patch("routes.specs.get_config", return_value=cfg):
            client = TestClient(_make_app())
            response = client.get("/specs")
        assert response.status_code == 200

    # CON-0091: Response ist eine Liste (Array) — ApiClient.validate() erwartet Array
    def test_get_specs_returns_list(self, tmp_path: Path) -> None:
        cfg = _mock_config_with_specs(tmp_path)
        with patch("routes.specs.get_config", return_value=cfg):
            client = TestClient(_make_app())
            response = client.get("/specs")
        assert isinstance(response.json(), list)

    # CON-0091: Jedes Spec-Objekt enthält 'id', 'title', 'status' (für Dashboard)
    def test_spec_object_has_required_fields(self, tmp_path: Path) -> None:
        cfg = _mock_config_with_specs(tmp_path)
        with patch("routes.specs.get_config", return_value=cfg):
            client = TestClient(_make_app())
            specs = client.get("/specs").json()
        assert len(specs) >= 1
        spec = specs[0]
        assert "id" in spec
        assert "title" in spec
        assert "status" in spec

    # CON-0091: Spec-Objekt enthält 'priority' (für Dashboard-Darstellung)
    def test_spec_object_has_priority_field(self, tmp_path: Path) -> None:
        cfg = _mock_config_with_specs(tmp_path)
        with patch("routes.specs.get_config", return_value=cfg):
            client = TestClient(_make_app())
            specs = client.get("/specs").json()
        assert "priority" in specs[0]

    # CON-0091: Leere Spec-Liste ist ein gültiges leeres Array (nicht null)
    def test_empty_specs_returns_empty_list(self, tmp_path: Path) -> None:
        sdd_dir = tmp_path / ".sdd" / "specs"
        sdd_dir.mkdir(parents=True)
        cfg = MagicMock()
        cfg.root = tmp_path
        cfg.specs_dir = sdd_dir
        with patch("routes.specs.get_config", return_value=cfg):
            client = TestClient(_make_app())
            response = client.get("/specs")
        assert response.status_code == 200
        assert response.json() == []
