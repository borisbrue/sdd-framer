"""Unit-Tests für interaktive Pipeline-Endpunkte (SPEC-0028).

FR-01  review_spec
FR-02  propose_contracts
FR-05  generate_holdouts
FR-06  get_contract / put_contract
FR-07  get_holdout / put_holdout
FR-09  run_tests_in_container
FR-11  get_job
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tool"))
sys.path.insert(0, str(REPO_ROOT / "web" / "api"))

# Import route functions directly (no FastAPI TestClient needed)
import routes.interactive as _mod
from sdd_cli.pipeline_jobs import JobManager


# ── Fixtures ─────────────────────────────────────────────────────────────────

def _make_spec(tmp_path: Path, spec_id: str = "SPEC-0028", contracts: list | None = None) -> Path:
    specs_dir = tmp_path / ".sdd" / "specs"
    specs_dir.mkdir(parents=True, exist_ok=True)
    fm = {
        "id": spec_id,
        "title": "Test Spec",
        "status": "in-progress",
        "owner": "Boris",
        "created": "2026-05-19",
        "updated": "2026-05-19",
    }
    if contracts:
        fm["contracts"] = contracts
    path = specs_dir / f"{spec_id}-test.md"
    path.write_text(f"---\n{yaml.safe_dump(fm)}---\n# Spec body\n\nFR-01: do thing\n", encoding="utf-8")
    return path


def _make_contract(tmp_path: Path, con_id: str = "CON-0001") -> Path:
    con_dir = tmp_path / ".sdd" / "contracts" / "behavior"
    con_dir.mkdir(parents=True, exist_ok=True)
    fm = {
        "id": con_id,
        "title": "Test Contract",
        "type": "behavior",
        "format": "markdown",
        "spec": "SPEC-0028",
        "version": "0.1.0",
        "status": "draft",
        "project": "PRJ-0001",
    }
    path = con_dir / f"{con_id}-test.md"
    path.write_text(f"---\n{yaml.safe_dump(fm)}---\n# Contract body\n", encoding="utf-8")
    return path


def _make_holdout(tmp_path: Path, hol_id: str = "HOL-0001") -> Path:
    hol_dir = tmp_path / ".sdd" / "holdout"
    hol_dir.mkdir(parents=True, exist_ok=True)
    fm = {"id": hol_id, "spec": "SPEC-0028", "title": "Test Holdout", "status": "draft"}
    path = hol_dir / f"{hol_id}-test.md"
    path.write_text(f"---\n{yaml.safe_dump(fm)}---\n# Holdout body\n", encoding="utf-8")
    return path


def _cfg(tmp_path: Path):
    from sdd_cli.config import SddConfig
    cfg = MagicMock(spec=SddConfig)
    cfg.root = tmp_path
    cfg.sdd_dir = tmp_path / ".sdd"
    cfg.specs_dir = tmp_path / ".sdd" / "specs"
    cfg.contracts_dir = tmp_path / ".sdd" / "contracts"
    cfg.holdout_dir = tmp_path / ".sdd" / "holdout"
    return cfg


def _mock_provider(text: str):
    result = MagicMock()
    result.text = text
    provider = MagicMock()
    provider.complete.return_value = result
    return provider


# ── FR-01: review_spec ────────────────────────────────────────────────────────

def test_tc01_review_spec_ok(tmp_path):
    """review_spec liefert ok=True und speichert Review-Datei (TC-01)."""
    _make_spec(tmp_path)
    cfg = _cfg(tmp_path)
    review_answer = json.dumps({
        "summary": "Spec ist gut",
        "issues": [],
        "suggestions": ["Mehr Details"],
    })
    provider = _mock_provider(review_answer)

    with patch("routes.interactive.get_config", return_value=cfg), \
         patch("routes.interactive._get_provider", return_value=provider):
        result = _mod.review_spec("SPEC-0028")

    assert result["ok"] is True
    assert "Spec ist gut" in result["output"]
    review_file = tmp_path / ".sdd" / "reviews" / "SPEC-0028-review.md"
    assert review_file.exists()


def test_tc02_review_spec_spec_not_found(tmp_path):
    """review_spec gibt 404 wenn Spec nicht existiert (TC-02)."""
    cfg = _cfg(tmp_path)
    cfg.specs_dir.mkdir(parents=True, exist_ok=True)
    from fastapi import HTTPException
    with patch("routes.interactive.get_config", return_value=cfg):
        with pytest.raises(HTTPException) as exc:
            _mod.review_spec("SPEC-9999")
    assert exc.value.status_code == 404


def test_tc03_review_spec_llm_error_returns_not_ok(tmp_path):
    """review_spec gibt ok=False wenn LLM einen Fehler wirft (TC-03)."""
    _make_spec(tmp_path)
    cfg = _cfg(tmp_path)
    provider = MagicMock()
    provider.complete.side_effect = RuntimeError("LLM nicht verfügbar")

    with patch("routes.interactive.get_config", return_value=cfg), \
         patch("routes.interactive._get_provider", return_value=provider):
        result = _mod.review_spec("SPEC-0028")

    assert result["ok"] is False
    assert "LLM nicht verfügbar" in result["output"]


# ── FR-02: propose_contracts ──────────────────────────────────────────────────

def test_tc04_propose_contracts_creates_files(tmp_path):
    """propose_contracts schreibt Contract-Dateien in .sdd/contracts/ (TC-04)."""
    _make_spec(tmp_path)
    cfg = _cfg(tmp_path)
    proposals = json.dumps([
        {"title": "API Endpoint", "type": "api", "format": "openapi", "guarantee": "GET /items liefert 200"},
    ])
    provider = _mock_provider(proposals)

    with patch("routes.interactive.get_config", return_value=cfg), \
         patch("routes.interactive._get_provider", return_value=provider):
        result = _mod.propose_contracts("SPEC-0028")

    assert result["ok"] is True
    assert len(result["contracts"]) == 1
    con_id = result["contracts"][0]["id"]
    assert con_id.startswith("CON-")
    # File should exist
    contract_path = tmp_path / result["contracts"][0]["path"]
    assert contract_path.exists()


def test_tc05_propose_contracts_links_to_spec(tmp_path):
    """propose_contracts verknüpft Contract-ID im Spec-Frontmatter (TC-05)."""
    _make_spec(tmp_path)
    cfg = _cfg(tmp_path)
    proposals = json.dumps([
        {"title": "Behavior Contract", "type": "behavior", "format": "markdown", "guarantee": "Gibt Ergebnis zurück"},
    ])
    provider = _mock_provider(proposals)

    with patch("routes.interactive.get_config", return_value=cfg), \
         patch("routes.interactive._get_provider", return_value=provider):
        result = _mod.propose_contracts("SPEC-0028")

    # Spec frontmatter should now have the contract ID
    from sdd_cli.frontmatter import parse_safe
    spec_path = tmp_path / ".sdd" / "specs" / "SPEC-0028-test.md"
    doc = parse_safe(spec_path)
    assert result["contracts"][0]["id"] in doc.frontmatter.get("contracts", [])


# ── FR-05: generate_holdouts ──────────────────────────────────────────────────

def test_tc06_generate_holdouts_no_contracts_returns_not_ok(tmp_path):
    """generate_holdouts gibt ok=False wenn keine Contracts verknüpft (TC-06)."""
    _make_spec(tmp_path, contracts=[])
    cfg = _cfg(tmp_path)

    with patch("routes.interactive.get_config", return_value=cfg):
        result = _mod.generate_holdouts("SPEC-0028")

    assert result["ok"] is False
    assert "Contracts" in result["output"]


def test_tc07_generate_holdouts_uses_only_contracts(tmp_path):
    """generate_holdouts schreibt Holdout-Dateien auf Contract-Basis (TC-07)."""
    _make_contract(tmp_path, "CON-0001")
    _make_spec(tmp_path, contracts=["CON-0001"])
    cfg = _cfg(tmp_path)
    scenarios = json.dumps([
        {"title": "Szenario A", "input": "request", "expected": "response", "evaluation_hint": "prüfe status"},
    ])
    provider = _mock_provider(scenarios)

    with patch("routes.interactive.get_config", return_value=cfg), \
         patch("routes.interactive._get_provider", return_value=provider):
        result = _mod.generate_holdouts("SPEC-0028")

    assert result["ok"] is True
    assert len(result["holdouts"]) == 1
    hol_path = tmp_path / result["holdouts"][0]["path"]
    assert hol_path.exists()
    # Verify prompt did NOT include source code paths
    call_args = provider.complete.call_args[0][0]
    assert "tool/" not in call_args
    assert "web/api/routes" not in call_args


# ── FR-06: get_contract / put_contract ───────────────────────────────────────

def test_tc08_get_contract_returns_body(tmp_path):
    """get_contract gibt body und frontmatter zurück (TC-08)."""
    _make_contract(tmp_path, "CON-0001")
    cfg = _cfg(tmp_path)

    with patch("routes.interactive.get_config", return_value=cfg):
        result = _mod.get_contract("SPEC-0028", "CON-0001")

    assert result["id"] == "CON-0001"
    assert "body" in result
    assert "frontmatter" in result


def test_tc09_put_contract_overwrites_body(tmp_path):
    """put_contract schreibt neuen body (TC-09)."""
    _make_contract(tmp_path, "CON-0001")
    cfg = _cfg(tmp_path)
    payload = _mod.PutBody(body="# New body\n\nUpdated content.\n")

    with patch("routes.interactive.get_config", return_value=cfg):
        result = _mod.put_contract("SPEC-0028", "CON-0001", payload)

    assert result["ok"] is True
    with patch("routes.interactive.get_config", return_value=cfg):
        reloaded = _mod.get_contract("SPEC-0028", "CON-0001")
    assert "Updated content." in reloaded["body"]


# ── FR-07: get_holdout / put_holdout ─────────────────────────────────────────

def test_tc10_get_holdout_returns_body(tmp_path):
    """get_holdout gibt body und frontmatter zurück (TC-10)."""
    _make_holdout(tmp_path, "HOL-0001")
    cfg = _cfg(tmp_path)

    with patch("routes.interactive.get_config", return_value=cfg):
        result = _mod.get_holdout("SPEC-0028", "HOL-0001")

    assert result["id"] == "HOL-0001"
    assert "body" in result


def test_tc11_put_holdout_overwrites_body(tmp_path):
    """put_holdout schreibt neuen body (TC-11)."""
    _make_holdout(tmp_path, "HOL-0001")
    cfg = _cfg(tmp_path)
    payload = _mod.PutBody(body="# Updated Holdout\n")

    with patch("routes.interactive.get_config", return_value=cfg):
        result = _mod.put_holdout("SPEC-0028", "HOL-0001", payload)

    assert result["ok"] is True


# ── FR-09: run_tests_in_container ────────────────────────────────────────────

def test_tc12_run_tests_container_not_running(tmp_path):
    """run_tests_in_container gibt ok=False wenn Container nicht läuft (TC-12)."""
    cfg = _cfg(tmp_path)
    mock_runtime = MagicMock()
    mock_runtime.inspect_status.return_value = "stopped"

    with patch("routes.interactive.get_config", return_value=cfg), \
         patch("routes.interactive.get_runtime", return_value=mock_runtime), \
         patch("routes.interactive.container_name", return_value="sdd-dev-spec-0028"):
        result = _mod.run_tests_in_container("SPEC-0028")

    assert result["ok"] is False
    assert "läuft nicht" in result["output"]


def _mock_popen(lines: list[str], returncode: int):
    """Builds a Popen mock whose stdout iterates over lines."""
    mock_proc = MagicMock()
    mock_proc.stdout = iter(line + "\n" for line in lines)
    mock_proc.returncode = returncode
    mock_proc.wait.return_value = returncode
    return mock_proc


def test_tc13_run_tests_passes(tmp_path):
    """run_tests_in_container gibt ok=True bei rc=0 (TC-13)."""
    cfg = _cfg(tmp_path)
    mock_runtime = MagicMock()
    mock_runtime.inspect_status.return_value = "running"
    mock_runtime.cli.return_value = "podman"

    with patch("routes.interactive.get_config", return_value=cfg), \
         patch("routes.interactive.get_runtime", return_value=mock_runtime), \
         patch("routes.interactive.container_name", return_value="sdd-dev-spec-0028"), \
         patch("routes.interactive.subprocess.Popen", return_value=_mock_popen(["5 passed"], 0)):
        result = _mod.run_tests_in_container("SPEC-0028")

    assert result["ok"] is True
    assert "5 passed" in result["output"]


def test_tc14_run_tests_fails_on_nonzero_rc(tmp_path):
    """run_tests_in_container gibt ok=False bei rc!=0 (TC-14)."""
    cfg = _cfg(tmp_path)
    mock_runtime = MagicMock()
    mock_runtime.inspect_status.return_value = "running"
    mock_runtime.cli.return_value = "podman"

    with patch("routes.interactive.get_config", return_value=cfg), \
         patch("routes.interactive.get_runtime", return_value=mock_runtime), \
         patch("routes.interactive.container_name", return_value="sdd-dev-spec-0028"), \
         patch("routes.interactive.subprocess.Popen", return_value=_mock_popen(["FAILED: test_foo"], 1)):
        result = _mod.run_tests_in_container("SPEC-0028")

    assert result["ok"] is False
    assert "FAILED" in result["output"]


# ── FR-11: get_job ────────────────────────────────────────────────────────────

def test_tc15_get_job_idle_when_no_job(tmp_path):
    """get_job gibt status=idle zurück wenn kein Job existiert (TC-15)."""
    cfg = _cfg(tmp_path)

    with patch("routes.interactive.get_config", return_value=cfg):
        result = _mod.get_job("SPEC-0028")

    assert result["status"] == "idle"


def test_tc16_get_job_returns_running_job(tmp_path):
    """get_job gibt laufenden Job zurück (TC-16)."""
    cfg = _cfg(tmp_path)
    jm = JobManager(cfg)
    jm.start("SPEC-0028", "review")

    with patch("routes.interactive.get_config", return_value=cfg):
        result = _mod.get_job("SPEC-0028")

    assert result["status"] == "running"
    assert result["command"] == "review"
