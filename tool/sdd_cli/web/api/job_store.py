"""In-Memory Job-Store für asynchrone Analyse-Jobs (SPEC-0016, CON-0051)."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

JOB_TTL_HOURS = 24
JOB_TIMEOUT_SECONDS = 120
MAX_CONCURRENT_JOBS_PER_DOC = 5


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


@dataclass
class AnalysisJob:
    job_id: str
    doc_id: str
    status: str        # "queued" | "running" | "complete" | "failed"
    result_id: str | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    def _touch(self) -> None:
        self.updated_at = _now()

    def mark_running(self) -> None:
        self.status = "running"
        self._touch()

    def mark_complete(self, result_id: str) -> None:
        self.status = "complete"
        self.result_id = result_id
        self._touch()

    def mark_failed(self, error: str) -> None:
        self.status = "failed"
        self.error = error
        self._touch()

    def is_expired(self) -> bool:
        return _now() - self.updated_at > timedelta(hours=JOB_TTL_HOURS)

    def is_timed_out(self) -> bool:
        return (
            self.status == "running"
            and _now() - self.updated_at > timedelta(seconds=JOB_TIMEOUT_SECONDS)
        )


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, AnalysisJob] = {}

    def create(self, doc_id: str) -> AnalysisJob:
        job = AnalysisJob(job_id=str(uuid.uuid4()), doc_id=doc_id, status="queued")
        self._jobs[job.job_id] = job
        return job

    def get(self, job_id: str) -> AnalysisJob | None:
        job = self._jobs.get(job_id)
        if job is None:
            return None
        if job.is_expired():
            del self._jobs[job_id]
            return None
        return job

    def update_running(self, job_id: str) -> None:
        if job := self._jobs.get(job_id):
            job.mark_running()

    def update_complete(self, job_id: str, result_id: str) -> None:
        if job := self._jobs.get(job_id):
            job.mark_complete(result_id)

    def update_failed(self, job_id: str, error: str) -> None:
        if job := self._jobs.get(job_id):
            job.mark_failed(error)

    def active_count(self, doc_id: str) -> int:
        return sum(
            1 for j in self._jobs.values()
            if j.doc_id == doc_id and j.status in {"queued", "running"}
        )

    def cleanup_expired(self) -> int:
        expired = [jid for jid, j in self._jobs.items() if j.is_expired()]
        for jid in expired:
            del self._jobs[jid]
        return len(expired)

    def apply_timeouts(self) -> int:
        timed_out = [j for j in self._jobs.values() if j.is_timed_out()]
        for job in timed_out:
            job.mark_failed("Timeout")
        return len(timed_out)


# Singleton — geteilt über alle Requests des Prozesses
_store = JobStore()


def get_job_store() -> JobStore:
    return _store
