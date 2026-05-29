"""Unit-Tests für JobManager (FR-11 SPEC-0028)."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tool"))

from sdd_cli.pipeline_jobs import JobManager, JobStatus


def _make_cfg(tmp_path: Path):
    cfg = MagicMock()
    cfg.sdd_dir = tmp_path / ".sdd"
    return cfg


# ── TC-01: start schreibt job.json ───────────────────────────────────────────

def test_tc01_start_creates_job_file(tmp_path):
    """start() legt .sdd/pipeline/{spec_id}-job.json an (TC-01)."""
    cfg = _make_cfg(tmp_path)
    jm = JobManager(cfg)
    job = jm.start("SPEC-0028", "review")

    job_file = tmp_path / ".sdd" / "pipeline" / "SPEC-0028-job.json"
    assert job_file.exists()
    assert job.status == "running"
    assert job.command == "review"


# ── TC-02: get liest zurück was start schrieb ────────────────────────────────

def test_tc02_get_returns_started_job(tmp_path):
    """get() gibt JobStatus zurück der mit start() angelegt wurde (TC-02)."""
    cfg = _make_cfg(tmp_path)
    jm = JobManager(cfg)
    jm.start("SPEC-0028", "review")

    loaded = jm.get("SPEC-0028")
    assert loaded is not None
    assert loaded.spec_id == "SPEC-0028"
    assert loaded.status == "running"


# ── TC-03: append fügt Zeilen hinzu ─────────────────────────────────────────

def test_tc03_append_accumulates_output(tmp_path):
    """append() fügt Zeilen zum output-Feld hinzu (TC-03)."""
    cfg = _make_cfg(tmp_path)
    jm = JobManager(cfg)
    jm.start("SPEC-0028", "review")
    jm.append("SPEC-0028", "line one")
    jm.append("SPEC-0028", "line two")

    job = jm.get("SPEC-0028")
    assert "line one" in job.output
    assert "line two" in job.output


# ── TC-04: finish(ok=True) setzt status auf done ─────────────────────────────

def test_tc04_finish_ok_sets_done(tmp_path):
    """finish(ok=True) setzt status='done' und finished_at (TC-04)."""
    cfg = _make_cfg(tmp_path)
    jm = JobManager(cfg)
    jm.start("SPEC-0028", "review")
    jm.finish("SPEC-0028", ok=True, result={"summary": "ok"})

    job = jm.get("SPEC-0028")
    assert job.status == "done"
    assert job.finished_at is not None
    assert job.result == {"summary": "ok"}


# ── TC-05: finish(ok=False) setzt status auf failed ──────────────────────────

def test_tc05_finish_error_sets_failed(tmp_path):
    """finish(ok=False) setzt status='failed' (TC-05)."""
    cfg = _make_cfg(tmp_path)
    jm = JobManager(cfg)
    jm.start("SPEC-0028", "review")
    jm.finish("SPEC-0028", ok=False)

    job = jm.get("SPEC-0028")
    assert job.status == "failed"


# ── TC-06: get gibt None zurück wenn kein Job existiert ──────────────────────

def test_tc06_get_returns_none_for_unknown_spec(tmp_path):
    """get() gibt None zurück wenn kein Job für spec_id existiert (TC-06)."""
    cfg = _make_cfg(tmp_path)
    jm = JobManager(cfg)
    assert jm.get("SPEC-9999") is None
