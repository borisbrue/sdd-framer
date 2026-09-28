"""Walking Skeleton: ein FR-markierter Test, damit sdd stack verify die Test-Sonde prüfen kann."""
import pytest
from fastapi.testclient import TestClient

from {{package_name}} import __version__
from {{package_name}}.__main__ import app


@pytest.mark.fr("FR-01")
def test_health_meldet_ok():
    antwort = TestClient(app).get("/health")
    assert antwort.status_code == 200
    assert antwort.json() == {"status": "ok", "version": __version__}
