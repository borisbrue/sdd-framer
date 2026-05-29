# TST-0127 – JobManager Unit-Tests
# Spec: SPEC-0028 | Contract: CON-0109
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tool"))

from sdd_cli.pipeline_jobs import JobManager
from sdd_cli.config import SddConfig


def _cfg(tmp_path: Path) -> SddConfig:
    sdd_dir = tmp_path / ".sdd"
    sdd_dir.mkdir(parents=True, exist_ok=True)
    return SddConfig(root=tmp_path, raw={})


class TestTST0127:

    def test_tc01_start_creates_job_file(self, tmp_path):
        """start() legt job.json mit status=running an."""
        jobs = JobManager(_cfg(tmp_path))
        job = jobs.start("SPEC-0028", "review")
        p = tmp_path / ".sdd" / "pipeline" / "SPEC-0028-job.json"
        assert p.exists()
        assert job.status == "running"
        assert job.spec_id == "SPEC-0028"
        assert job.command == "review"

    def test_tc02_get_reads_back_started_job(self, tmp_path):
        """get() liest zurück was start() geschrieben hat."""
        jobs = JobManager(_cfg(tmp_path))
        jobs.start("SPEC-0028", "review")
        job = jobs.get("SPEC-0028")
        assert job is not None
        assert job.spec_id == "SPEC-0028"
        assert job.status == "running"

    def test_tc03_append_accumulates_output(self, tmp_path):
        """append() häuft output-Zeilen auf."""
        jobs = JobManager(_cfg(tmp_path))
        jobs.start("SPEC-0028", "review")
        jobs.append("SPEC-0028", "Zeile 1")
        jobs.append("SPEC-0028", "Zeile 2")
        job = jobs.get("SPEC-0028")
        assert job is not None
        assert "Zeile 1" in job.output
        assert "Zeile 2" in job.output

    def test_tc04_finish_ok_sets_done(self, tmp_path):
        """finish(ok=True) setzt status=done und finished_at."""
        jobs = JobManager(_cfg(tmp_path))
        jobs.start("SPEC-0028", "review")
        jobs.finish("SPEC-0028", ok=True, result={"score": 1.0})
        job = jobs.get("SPEC-0028")
        assert job is not None
        assert job.status == "done"
        assert job.finished_at is not None
        assert job.result == {"score": 1.0}

    def test_tc05_finish_fail_sets_failed(self, tmp_path):
        """finish(ok=False) setzt status=failed."""
        jobs = JobManager(_cfg(tmp_path))
        jobs.start("SPEC-0028", "review")
        jobs.finish("SPEC-0028", ok=False)
        job = jobs.get("SPEC-0028")
        assert job is not None
        assert job.status == "failed"

    def test_tc06_get_unknown_spec_returns_none(self, tmp_path):
        """get() für unbekannte Spec gibt None zurück."""
        jobs = JobManager(_cfg(tmp_path))
        assert jobs.get("SPEC-9999") is None
