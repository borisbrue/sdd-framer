"""Unit-Tests für analysis_repository.py – Datei-Persistenz (SPEC-0016, CON-0050)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "tool" / "sdd_cli" / "web" / "api"))

from analysis_repository import AnalysisRepository, PersistedAnalysis, _safe_dir_name

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_analysis(doc_id: str = "SPEC-0001", result_id: str = "2026-05-16T12:00:00_abc12345") -> PersistedAnalysis:
    return PersistedAnalysis(
        result_id=result_id,
        doc_id=doc_id,
        timestamp="2026-05-16T12:00:00Z",
        session_id="sess-xyz",
        dismissed_ids=[],
        questions=[{"id": "q-001", "section": "FR", "text": "Question?", "severity": "warning"}],
        issues=[{"section": "NFR", "text": "Issue.", "severity": "error"}],
        suggestions=[{"text": "Suggestion."}],
        usage={"input_tokens": 100, "output_tokens": 50},
    )


# ─── _safe_dir_name ───────────────────────────────────────────────────────────

class TestSafeDirName:
    def test_plain_id(self):
        assert _safe_dir_name("SPEC-0001") == "SPEC-0001"

    def test_replaces_slash(self):
        assert "/" not in _safe_dir_name("foo/bar")

    def test_replaces_colon(self):
        assert ":" not in _safe_dir_name("foo:bar")


# ─── PersistedAnalysis ────────────────────────────────────────────────────────

class TestPersistedAnalysis:
    def test_to_dict_has_all_keys(self):
        a = _make_analysis()
        d = a.to_dict()
        for key in ("result_id", "doc_id", "timestamp", "session_id",
                    "dismissed_ids", "questions", "issues", "suggestions", "usage"):
            assert key in d

    def test_summary(self):
        a = _make_analysis()
        s = a.summary()
        assert s["result_id"] == a.result_id
        assert s["question_count"] == 1
        assert s["issue_count"] == 1
        assert s["dismissed_count"] == 0


# ─── AnalysisRepository.save ──────────────────────────────────────────────────

class TestSave:
    def test_creates_file(self, tmp_path):
        repo = AnalysisRepository(tmp_path)
        a = _make_analysis()
        path = repo.save(a)
        assert path.exists()

    def test_file_is_valid_json(self, tmp_path):
        repo = AnalysisRepository(tmp_path)
        a = _make_analysis()
        path = repo.save(a)
        data = json.loads(path.read_text())
        assert data["result_id"] == a.result_id

    def test_creates_doc_subdir(self, tmp_path):
        repo = AnalysisRepository(tmp_path)
        a = _make_analysis(doc_id="SPEC-0099")
        repo.save(a)
        assert (tmp_path / "SPEC-0099").is_dir()

    def test_filename_is_result_id(self, tmp_path):
        repo = AnalysisRepository(tmp_path)
        a = _make_analysis(result_id="2026-05-16T12:00:00_deadbeef")
        path = repo.save(a)
        assert path.name == "2026-05-16T12:00:00_deadbeef.json"


# ─── AnalysisRepository.list ──────────────────────────────────────────────────

class TestList:
    def test_empty_returns_empty(self, tmp_path):
        repo = AnalysisRepository(tmp_path)
        assert repo.list("SPEC-0001") == []

    def test_no_dir_returns_empty(self, tmp_path):
        repo = AnalysisRepository(tmp_path)
        assert repo.list("SPEC-9999") == []

    def test_lists_saved_analyses(self, tmp_path):
        repo = AnalysisRepository(tmp_path)
        repo.save(_make_analysis(result_id="2026-05-16T12:00:00_aaa"))
        repo.save(_make_analysis(result_id="2026-05-16T12:01:00_bbb"))
        result = repo.list("SPEC-0001")
        assert len(result) == 2

    def test_newest_first(self, tmp_path):
        repo = AnalysisRepository(tmp_path)
        repo.save(_make_analysis(result_id="2026-05-16T11:00:00_old"))
        repo.save(_make_analysis(result_id="2026-05-16T12:00:00_new"))
        result = repo.list("SPEC-0001")
        assert result[0]["result_id"] == "2026-05-16T12:00:00_new"

    def test_summary_has_correct_counts(self, tmp_path):
        repo = AnalysisRepository(tmp_path)
        repo.save(_make_analysis())
        result = repo.list("SPEC-0001")
        assert result[0]["question_count"] == 1
        assert result[0]["issue_count"] == 1
        assert result[0]["dismissed_count"] == 0

    def test_respects_limit(self, tmp_path):
        repo = AnalysisRepository(tmp_path)
        for i in range(10):
            repo.save(_make_analysis(result_id=f"2026-05-16T12:0{i}:00_x{i:02d}"))
        result = repo.list("SPEC-0001", limit=3)
        assert len(result) == 3


# ─── AnalysisRepository.get ───────────────────────────────────────────────────

class TestGet:
    def test_get_existing(self, tmp_path):
        repo = AnalysisRepository(tmp_path)
        a = _make_analysis()
        repo.save(a)
        retrieved = repo.get("SPEC-0001", a.result_id)
        assert retrieved is not None
        assert retrieved.result_id == a.result_id

    def test_get_nonexistent_returns_none(self, tmp_path):
        repo = AnalysisRepository(tmp_path)
        assert repo.get("SPEC-0001", "nonexistent") is None

    def test_get_preserves_questions(self, tmp_path):
        repo = AnalysisRepository(tmp_path)
        a = _make_analysis()
        repo.save(a)
        retrieved = repo.get("SPEC-0001", a.result_id)
        assert len(retrieved.questions) == 1
        assert retrieved.questions[0]["id"] == "q-001"


# ─── AnalysisRepository.update_dismiss ───────────────────────────────────────

class TestUpdateDismiss:
    def test_dismiss_adds_id(self, tmp_path):
        repo = AnalysisRepository(tmp_path)
        a = _make_analysis()
        repo.save(a)
        updated = repo.update_dismiss("SPEC-0001", a.result_id, "q-001", True)
        assert "q-001" in updated

    def test_undismiss_removes_id(self, tmp_path):
        repo = AnalysisRepository(tmp_path)
        a = _make_analysis()
        a.dismissed_ids = ["q-001"]
        repo.save(a)
        updated = repo.update_dismiss("SPEC-0001", a.result_id, "q-001", False)
        assert "q-001" not in updated

    def test_idempotent_dismiss(self, tmp_path):
        repo = AnalysisRepository(tmp_path)
        a = _make_analysis()
        repo.save(a)
        repo.update_dismiss("SPEC-0001", a.result_id, "q-001", True)
        updated = repo.update_dismiss("SPEC-0001", a.result_id, "q-001", True)
        assert updated.count("q-001") == 1

    def test_nonexistent_returns_none(self, tmp_path):
        repo = AnalysisRepository(tmp_path)
        result = repo.update_dismiss("SPEC-0001", "nonexistent", "q-001", True)
        assert result is None

    def test_dismiss_persisted_to_disk(self, tmp_path):
        repo = AnalysisRepository(tmp_path)
        a = _make_analysis()
        repo.save(a)
        repo.update_dismiss("SPEC-0001", a.result_id, "q-001", True)
        # re-read from disk
        retrieved = repo.get("SPEC-0001", a.result_id)
        assert "q-001" in retrieved.dismissed_ids


# ─── AnalysisRepository.make_result_id ───────────────────────────────────────

class TestMakeResultId:
    def test_format(self):
        rid = AnalysisRepository.make_result_id("3f8a1c2d-abcd-1234-efef-000000000000")
        # format: YYYY-MM-DDTHH:MM:SS_{first 8 chars of job_id}
        parts = rid.split("_")
        assert len(parts) == 2
        assert len(parts[1]) == 8

    def test_different_job_ids_differ(self):
        r1 = AnalysisRepository.make_result_id("aaaaaaaa-0000-0000-0000-000000000000")
        r2 = AnalysisRepository.make_result_id("bbbbbbbb-0000-0000-0000-000000000000")
        assert r1 != r2
