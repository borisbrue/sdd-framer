# TST-0216 – GET /api/patterns – Response-Shape
# Spec: SPEC-0049 · Contract: CON-0184
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tool" / "sdd_cli" / "web" / "api"))
sys.path.insert(0, str(REPO_ROOT / "tool"))
os.environ.setdefault("SDD_PROJECT_ROOT", str(REPO_ROOT))

import sdd_context

sdd_context.init(REPO_ROOT)

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)
_KEYS = {"pattern_name", "specs", "refactoring_guru_url", "code_locations"}


class TestTST0216:
    def test_returns_200_list(self) -> None:
        r = client.get("/api/patterns")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_item_shape(self) -> None:
        data = client.get("/api/patterns").json()
        for item in data:
            assert _KEYS <= set(item.keys())
            assert isinstance(item["specs"], list)
            assert isinstance(item["code_locations"], list)
            for s in item["specs"]:
                assert "spec_id" in s and "reason" in s
            for loc in item["code_locations"]:
                assert {"file", "line", "annotation"} <= set(loc.keys())

    def test_all_items_have_name(self) -> None:
        # nur akzeptierte Patterns → jedes Element hat einen nicht-leeren Namen (G-05)
        data = client.get("/api/patterns").json()
        assert all(item["pattern_name"] for item in data)
