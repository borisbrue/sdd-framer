"""Unit-Tests für job_store.py – In-Memory Job-Verwaltung (SPEC-0016, CON-0051)."""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "tool" / "sdd_cli" / "web" / "api"))

from job_store import JOB_TIMEOUT_SECONDS, JOB_TTL_HOURS, AnalysisJob, JobStore

# ─── AnalysisJob ──────────────────────────────────────────────────────────────

class TestAnalysisJob:
    def _make(self, **kw) -> AnalysisJob:
        return AnalysisJob(job_id="abc", doc_id="SPEC-0001", status="queued", **kw)

    def test_initial_status_queued(self):
        j = self._make()
        assert j.status == "queued"

    def test_mark_running(self):
        j = self._make()
        j.mark_running()
        assert j.status == "running"
        assert j.result_id is None

    def test_mark_complete(self):
        j = self._make()
        j.mark_running()
        j.mark_complete("2026-05-16T12:00:00_abc12345")
        assert j.status == "complete"
        assert j.result_id == "2026-05-16T12:00:00_abc12345"
        assert j.error is None

    def test_mark_failed(self):
        j = self._make()
        j.mark_running()
        j.mark_failed("LLM error")
        assert j.status == "failed"
        assert j.error == "LLM error"
        assert j.result_id is None

    def test_is_expired_fresh(self):
        j = self._make()
        assert j.is_expired() is False

    def test_is_expired_old(self):
        j = self._make()
        old = datetime.now(tz=timezone.utc) - timedelta(hours=JOB_TTL_HOURS + 1)
        j.updated_at = old
        assert j.is_expired() is True

    def test_is_timed_out_queued(self):
        j = self._make()
        old = datetime.now(tz=timezone.utc) - timedelta(seconds=JOB_TIMEOUT_SECONDS + 1)
        j.updated_at = old
        assert j.is_timed_out() is False  # only "running" times out

    def test_is_timed_out_running(self):
        j = self._make()
        j.mark_running()
        old = datetime.now(tz=timezone.utc) - timedelta(seconds=JOB_TIMEOUT_SECONDS + 1)
        j.updated_at = old
        assert j.is_timed_out() is True

    def test_is_timed_out_not_yet(self):
        j = self._make()
        j.mark_running()
        assert j.is_timed_out() is False


# ─── JobStore ─────────────────────────────────────────────────────────────────

class TestJobStore:
    def test_create_returns_job(self):
        store = JobStore()
        job = store.create("SPEC-0001")
        assert job.job_id
        assert job.doc_id == "SPEC-0001"
        assert job.status == "queued"

    def test_get_existing(self):
        store = JobStore()
        job = store.create("SPEC-0001")
        retrieved = store.get(job.job_id)
        assert retrieved is not None
        assert retrieved.job_id == job.job_id

    def test_get_nonexistent_returns_none(self):
        store = JobStore()
        assert store.get("nonexistent") is None

    def test_get_expired_returns_none(self):
        store = JobStore()
        job = store.create("SPEC-0001")
        old = datetime.now(tz=timezone.utc) - timedelta(hours=JOB_TTL_HOURS + 1)
        store._jobs[job.job_id].updated_at = old
        assert store.get(job.job_id) is None

    def test_update_running(self):
        store = JobStore()
        job = store.create("SPEC-0001")
        store.update_running(job.job_id)
        assert store.get(job.job_id).status == "running"

    def test_update_complete(self):
        store = JobStore()
        job = store.create("SPEC-0001")
        store.update_running(job.job_id)
        store.update_complete(job.job_id, "result-123")
        j = store.get(job.job_id)
        assert j.status == "complete"
        assert j.result_id == "result-123"

    def test_update_failed(self):
        store = JobStore()
        job = store.create("SPEC-0001")
        store.update_running(job.job_id)
        store.update_failed(job.job_id, "oops")
        j = store.get(job.job_id)
        assert j.status == "failed"
        assert j.error == "oops"

    def test_update_nonexistent_is_noop(self):
        store = JobStore()
        store.update_running("nonexistent")  # must not raise

    def test_active_count_empty(self):
        store = JobStore()
        assert store.active_count("SPEC-0001") == 0

    def test_active_count_queued_and_running(self):
        store = JobStore()
        store.create("SPEC-0001")
        j2 = store.create("SPEC-0001")
        store.update_running(j2.job_id)
        assert store.active_count("SPEC-0001") == 2

    def test_active_count_excludes_complete_and_failed(self):
        store = JobStore()
        j1 = store.create("SPEC-0001")
        j2 = store.create("SPEC-0001")
        store.update_running(j1.job_id)
        store.update_complete(j1.job_id, "r1")
        store.update_running(j2.job_id)
        store.update_failed(j2.job_id, "err")
        assert store.active_count("SPEC-0001") == 0

    def test_active_count_per_doc_id(self):
        store = JobStore()
        store.create("SPEC-0001")
        store.create("SPEC-0002")
        assert store.active_count("SPEC-0001") == 1
        assert store.active_count("SPEC-0002") == 1

    def test_cleanup_expired_removes_old(self):
        store = JobStore()
        job = store.create("SPEC-0001")
        old = datetime.now(tz=timezone.utc) - timedelta(hours=JOB_TTL_HOURS + 1)
        store._jobs[job.job_id].updated_at = old
        removed = store.cleanup_expired()
        assert removed == 1
        assert store.get(job.job_id) is None

    def test_cleanup_expired_keeps_fresh(self):
        store = JobStore()
        store.create("SPEC-0001")
        removed = store.cleanup_expired()
        assert removed == 0

    def test_apply_timeouts_marks_failed(self):
        store = JobStore()
        job = store.create("SPEC-0001")
        store.update_running(job.job_id)
        old = datetime.now(tz=timezone.utc) - timedelta(seconds=JOB_TIMEOUT_SECONDS + 1)
        store._jobs[job.job_id].updated_at = old
        count = store.apply_timeouts()
        assert count == 1
        j = store.get(job.job_id)
        assert j.status == "failed"
        assert "Timeout" in j.error

    def test_apply_timeouts_ignores_queued(self):
        store = JobStore()
        job = store.create("SPEC-0001")
        old = datetime.now(tz=timezone.utc) - timedelta(seconds=JOB_TIMEOUT_SECONDS + 1)
        store._jobs[job.job_id].updated_at = old
        count = store.apply_timeouts()
        assert count == 0
        assert store.get(job.job_id).status == "queued"
