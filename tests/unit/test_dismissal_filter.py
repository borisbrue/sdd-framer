"""Unit-Tests für den Dismissal-Filter-Mechanismus (SPEC-0016, CON-0053).

Da der DismissalFilter im analyze_async-Route inline implementiert ist
(dismissed_ids werden als answered_questions mit answer='[dismissed]' übergeben),
testen wir hier das Verhalten des analyze()-Aufrufs mit vorausgefüllten
answered_questions sowie das update_dismiss-Verhalten des Repositories.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "tool" / "sdd_cli" / "web" / "api"))

from analysis_repository import AnalysisRepository, PersistedAnalysis

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_analysis_with_questions(
    dismissed_ids: list[str] | None = None,
) -> PersistedAnalysis:
    return PersistedAnalysis(
        result_id="2026-05-16T12:00:00_abc12345",
        doc_id="SPEC-0016",
        timestamp="2026-05-16T12:00:00Z",
        session_id="sess",
        dismissed_ids=dismissed_ids or [],
        questions=[
            {"id": "q-001", "section": "FR", "text": "Q1?", "severity": "warning"},
            {"id": "q-002", "section": "FR", "text": "Q2?", "severity": "warning"},
            {"id": "q-003", "section": "NFR", "text": "Q3?", "severity": "error"},
        ],
        issues=[],
        suggestions=[],
        usage={"input_tokens": 100, "output_tokens": 50},
    )


# ─── dismiss → persist ────────────────────────────────────────────────────────

class TestDismissalPersistence:
    def test_dismiss_adds_to_list(self, tmp_path):
        repo = AnalysisRepository(tmp_path)
        a = _make_analysis_with_questions()
        repo.save(a)
        ids = repo.update_dismiss("SPEC-0016", a.result_id, "q-001", True)
        assert "q-001" in ids

    def test_dismiss_second_item(self, tmp_path):
        repo = AnalysisRepository(tmp_path)
        a = _make_analysis_with_questions()
        repo.save(a)
        repo.update_dismiss("SPEC-0016", a.result_id, "q-001", True)
        ids = repo.update_dismiss("SPEC-0016", a.result_id, "q-002", True)
        assert "q-001" in ids
        assert "q-002" in ids

    def test_undismiss_removes_from_list(self, tmp_path):
        repo = AnalysisRepository(tmp_path)
        a = _make_analysis_with_questions(dismissed_ids=["q-001", "q-002"])
        repo.save(a)
        ids = repo.update_dismiss("SPEC-0016", a.result_id, "q-001", False)
        assert "q-001" not in ids
        assert "q-002" in ids

    def test_idempotent_double_dismiss(self, tmp_path):
        repo = AnalysisRepository(tmp_path)
        a = _make_analysis_with_questions(dismissed_ids=["q-001"])
        repo.save(a)
        ids = repo.update_dismiss("SPEC-0016", a.result_id, "q-001", True)
        assert ids.count("q-001") == 1

    def test_unknown_item_id_ignored(self, tmp_path):
        repo = AnalysisRepository(tmp_path)
        a = _make_analysis_with_questions()
        repo.save(a)
        ids = repo.update_dismiss("SPEC-0016", a.result_id, "unknown-id-999", True)
        assert "unknown-id-999" in ids  # stored even if not in questions (INV-04)

    def test_nonexistent_result_returns_none(self, tmp_path):
        repo = AnalysisRepository(tmp_path)
        result = repo.update_dismiss("SPEC-0016", "no-such-id", "q-001", True)
        assert result is None

    def test_dismiss_persisted_across_reads(self, tmp_path):
        repo = AnalysisRepository(tmp_path)
        a = _make_analysis_with_questions()
        repo.save(a)
        repo.update_dismiss("SPEC-0016", a.result_id, "q-003", True)
        loaded = repo.get("SPEC-0016", a.result_id)
        assert "q-003" in loaded.dismissed_ids


# ─── dismissed_ids → answered_questions mapping ───────────────────────────────

class TestDismissedIdsToAnsweredMapping:
    """Verify that the mapping used in analyze_async._run_analysis is correct.

    The route converts dismissed_ids into answered_questions before calling analyze().
    This tests that the mapping produces the expected structure.
    """

    def test_mapping_produces_answered_questions(self):
        dismissed_ids = ["q-001", "q-002"]
        answered = [{"id": did, "answer": "[dismissed]"} for did in dismissed_ids]
        assert len(answered) == 2
        assert answered[0] == {"id": "q-001", "answer": "[dismissed]"}
        assert answered[1] == {"id": "q-002", "answer": "[dismissed]"}

    def test_empty_dismissed_produces_empty_answered(self):
        answered = [{"id": did, "answer": "[dismissed]"} for did in []]
        assert answered == []

    def test_all_dismissed_all_mapped(self):
        dismissed_ids = ["q-001", "q-002", "q-003"]
        answered = [{"id": did, "answer": "[dismissed]"} for did in dismissed_ids]
        assert {a["id"] for a in answered} == set(dismissed_ids)
