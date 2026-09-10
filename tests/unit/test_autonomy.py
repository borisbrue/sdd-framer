"""Unit-Tests für autonomy.py – Autonomy Level Tracking (SPEC-0004)."""
from __future__ import annotations

from pathlib import Path

from sdd_cli.autonomy import (
    LEVEL_CRITERIA,
    VALID_LEVELS,
    _level_float,
    auto_merge_allowed,
    compute_level_stats,
    init_db,
    level_label,
    record_evaluation,
    record_false_positive,
    record_pr_result,
    record_resume_event,
)
from sdd_cli.config import SddConfig

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _cfg(tmp_path: Path) -> SddConfig:
    sdd = tmp_path / ".sdd"
    sdd.mkdir(parents=True, exist_ok=True)
    return SddConfig(root=tmp_path, raw={})


_PR_COUNTER: dict[str, int] = {}


def _populate_prs(cfg: SddConfig, project_id: str, count: int, passed: bool,
                  pass_rate: float, offset: int = 0) -> None:
    for i in range(count):
        record_pr_result(cfg, project_id, f"PR-{project_id}-{offset+i:04d}",
                         passed=passed, pass_rate=pass_rate)


# ─── _level_float ─────────────────────────────────────────────────────────────

class TestLevelFloat:
    def test_int_input(self):
        assert _level_float(3) == 3.0

    def test_string_input(self):
        assert _level_float("3.5") == 3.5

    def test_invalid_string_returns_1(self):
        assert _level_float("invalid") == 1.0

    def test_unknown_level_returns_1(self):
        assert _level_float(99) == 1.0

    def test_none_returns_1(self):
        assert _level_float(None) == 1.0

    def test_all_valid_levels(self):
        for lvl in VALID_LEVELS:
            assert _level_float(lvl) == lvl


# ─── level_label ──────────────────────────────────────────────────────────────

class TestLevelLabel:
    def test_known_level(self):
        label = level_label(3)
        assert "3" in label
        assert "AI-reviewed" in label

    def test_unknown_level(self):
        label = level_label(99.9)
        assert "unbekannt" in label

    def test_all_known_levels(self):
        for lvl in VALID_LEVELS:
            label = level_label(lvl)
            assert str(lvl) in label
            assert LEVEL_CRITERIA[lvl]["label"] in label


# ─── init_db ──────────────────────────────────────────────────────────────────

class TestInitDb:
    def test_creates_db_file(self, tmp_path):
        cfg = _cfg(tmp_path)
        init_db(cfg)
        db_path = tmp_path / ".sdd" / "evaluations.db"
        assert db_path.exists()

    def test_idempotent(self, tmp_path):
        cfg = _cfg(tmp_path)
        init_db(cfg)
        init_db(cfg)  # Should not raise
        db_path = tmp_path / ".sdd" / "evaluations.db"
        assert db_path.exists()


# ─── record_evaluation ────────────────────────────────────────────────────────

class TestRecordEvaluation:
    def test_stores_row(self, tmp_path):
        import sqlite3
        cfg = _cfg(tmp_path)
        record_evaluation(cfg, "PRJ-0001", "PR-0001", "HOL-0001", 1, True, cost_usd=0.05)
        db = tmp_path / ".sdd" / "evaluations.db"
        with sqlite3.connect(db) as conn:
            row = conn.execute("SELECT * FROM evaluations").fetchone()
        assert row is not None
        assert row[2] == "PR-0001"  # pr_number
        assert row[5] == 1          # passed


# ─── record_pr_result ─────────────────────────────────────────────────────────

class TestRecordPrResult:
    def test_stores_row(self, tmp_path):
        import sqlite3
        cfg = _cfg(tmp_path)
        record_pr_result(cfg, "PRJ-0001", "PR-0001", passed=True, pass_rate=0.95)
        db = tmp_path / ".sdd" / "evaluations.db"
        with sqlite3.connect(db) as conn:
            row = conn.execute("SELECT * FROM pr_results").fetchone()
        assert row[2] == "PR-0001"

    def test_upsert_replaces_existing(self, tmp_path):
        import sqlite3
        cfg = _cfg(tmp_path)
        record_pr_result(cfg, "PRJ-0001", "PR-0001", passed=False, pass_rate=0.5)
        record_pr_result(cfg, "PRJ-0001", "PR-0001", passed=True, pass_rate=0.9)
        db = tmp_path / ".sdd" / "evaluations.db"
        with sqlite3.connect(db) as conn:
            count = conn.execute("SELECT COUNT(*) FROM pr_results").fetchone()[0]
        assert count == 1


# ─── record_false_positive ────────────────────────────────────────────────────

class TestRecordFalsePositive:
    def test_stores_row(self, tmp_path):
        import sqlite3
        cfg = _cfg(tmp_path)
        record_false_positive(cfg, "PRJ-0001", "PR-0001")
        db = tmp_path / ".sdd" / "evaluations.db"
        with sqlite3.connect(db) as conn:
            count = conn.execute("SELECT COUNT(*) FROM false_positives").fetchone()[0]
        assert count == 1


# ─── record_resume_event ──────────────────────────────────────────────────────

class TestRecordResumeEvent:
    def test_stores_row(self, tmp_path):
        import sqlite3
        cfg = _cfg(tmp_path)
        record_resume_event(cfg, "PR-0001", triggered_by="cli")
        db = tmp_path / ".sdd" / "evaluations.db"
        with sqlite3.connect(db) as conn:
            row = conn.execute("SELECT * FROM resume_events").fetchone()
        assert row[1] == "PR-0001"
        assert row[2] == "cli"


# ─── compute_level_stats ──────────────────────────────────────────────────────

class TestComputeLevelStats:
    def test_empty_db_returns_zero_stats(self, tmp_path):
        cfg = _cfg(tmp_path)
        stats = compute_level_stats(cfg, "PRJ-0001", current_level=1)
        assert stats.total_prs == 0
        assert stats.pass_rate == 0.0
        assert stats.override_rate == 0.0
        # Level 1→2 has no PR minimum (window=0); upgrade is always proposed from level 1
        assert stats.upgrade_proposal == 2
        assert stats.downgrade_proposal is None

    def test_pass_rate_computed_correctly(self, tmp_path):
        cfg = _cfg(tmp_path)
        _populate_prs(cfg, "PRJ-0001", count=8, passed=True, pass_rate=0.9, offset=0)
        _populate_prs(cfg, "PRJ-0001", count=2, passed=False, pass_rate=0.5, offset=8)
        stats = compute_level_stats(cfg, "PRJ-0001", current_level=2)
        assert stats.total_prs == 10
        # average of 8×0.9 + 2×0.5 = 7.2+1.0 = 8.2 / 10 = 0.82
        assert abs(stats.pass_rate - 0.82) < 0.01

    def test_override_rate_from_false_positives(self, tmp_path):
        cfg = _cfg(tmp_path)
        _populate_prs(cfg, "PRJ-0001", count=10, passed=True, pass_rate=0.9)
        record_false_positive(cfg, "PRJ-0001", "PR-0002")
        record_false_positive(cfg, "PRJ-0001", "PR-0003")
        stats = compute_level_stats(cfg, "PRJ-0001", current_level=3)
        assert abs(stats.override_rate - 0.2) < 0.01

    def test_upgrade_proposal_when_criteria_met(self, tmp_path):
        cfg = _cfg(tmp_path)
        # Level 2 → 3 needs: min_prs=10, min_pass_rate=0.70
        # Level 2's own window = min_prs or 10 = 10, so recent_rows has up to 10 entries
        _populate_prs(cfg, "PRJ-0001", count=10, passed=True, pass_rate=0.92)
        stats = compute_level_stats(cfg, "PRJ-0001", current_level=2)
        assert stats.upgrade_proposal == 3

    def test_no_upgrade_proposal_insufficient_prs(self, tmp_path):
        cfg = _cfg(tmp_path)
        # Level 2 → 3 needs 10 PRs; only 5 provided
        _populate_prs(cfg, "PRJ-0001", count=5, passed=True, pass_rate=0.95)
        stats = compute_level_stats(cfg, "PRJ-0001", current_level=2)
        assert stats.upgrade_proposal is None

    def test_no_upgrade_proposal_at_max_level(self, tmp_path):
        cfg = _cfg(tmp_path)
        _populate_prs(cfg, "PRJ-0001", count=60, passed=True, pass_rate=0.95)
        stats = compute_level_stats(cfg, "PRJ-0001", current_level=4)
        assert stats.upgrade_proposal is None

    def test_downgrade_proposal_after_5_consecutive_below(self, tmp_path):
        cfg = _cfg(tmp_path)
        # 5 consecutive PRs below 0.85 threshold for level 3
        _populate_prs(cfg, "PRJ-0001", count=5, passed=False, pass_rate=0.5)
        stats = compute_level_stats(cfg, "PRJ-0001", current_level=3)
        assert stats.downgrade_proposal == 2

    def test_no_downgrade_at_level_1(self, tmp_path):
        cfg = _cfg(tmp_path)
        _populate_prs(cfg, "PRJ-0001", count=5, passed=False, pass_rate=0.0)
        stats = compute_level_stats(cfg, "PRJ-0001", current_level=2)
        assert stats.downgrade_proposal is None

    def test_auto_merge_blocked_below_threshold(self, tmp_path):
        cfg = _cfg(tmp_path)
        # Level 3: min_pass_rate=0.70, min_prs=10
        _populate_prs(cfg, "PRJ-0001", count=10, passed=False, pass_rate=0.5)
        stats = compute_level_stats(cfg, "PRJ-0001", current_level=3)
        assert stats.auto_merge_blocked

    def test_auto_merge_not_blocked_below_min_prs(self, tmp_path):
        cfg = _cfg(tmp_path)
        # Only 5 PRs, but level 3 needs 10 to trigger auto_merge block
        _populate_prs(cfg, "PRJ-0001", count=5, passed=False, pass_rate=0.5)
        stats = compute_level_stats(cfg, "PRJ-0001", current_level=3)
        assert not stats.auto_merge_blocked

    def test_project_id_isolation(self, tmp_path):
        cfg = _cfg(tmp_path)
        # Use project-prefixed PR numbers to avoid UNIQUE collision on pr_number
        _populate_prs(cfg, "PRJ-0001", count=10, passed=True, pass_rate=0.95)
        _populate_prs(cfg, "PRJ-0002", count=3, passed=False, pass_rate=0.3)
        stats1 = compute_level_stats(cfg, "PRJ-0001", current_level=2)
        stats2 = compute_level_stats(cfg, "PRJ-0002", current_level=2)
        assert stats1.total_prs == 10
        assert stats2.total_prs == 3


# ─── auto_merge_allowed ───────────────────────────────────────────────────────

class TestAutoMergeAllowed:
    def _cfg(self, tmp_path):
        return _cfg(tmp_path)

    def test_level_1_never_allowed(self, tmp_path):
        cfg = _cfg(tmp_path)
        allowed, reason = auto_merge_allowed(cfg, "PRJ", 1, total_prs=100, pass_rate=1.0)
        assert not allowed
        assert "Level 1" in reason

    def test_level_2_never_allowed(self, tmp_path):
        cfg = _cfg(tmp_path)
        allowed, reason = auto_merge_allowed(cfg, "PRJ", 2, total_prs=100, pass_rate=1.0)
        assert not allowed

    def test_level_3_5_allowed_when_criteria_met(self, tmp_path):
        cfg = _cfg(tmp_path)
        allowed, reason = auto_merge_allowed(cfg, "PRJ", 3.5, total_prs=30, pass_rate=0.9)
        assert allowed
        assert "freigegeben" in reason

    def test_level_4_blocked_insufficient_prs(self, tmp_path):
        cfg = _cfg(tmp_path)
        allowed, reason = auto_merge_allowed(cfg, "PRJ", 4, total_prs=10, pass_rate=0.95)
        assert not allowed
        assert "Minimum" in reason

    def test_level_4_blocked_low_pass_rate(self, tmp_path):
        cfg = _cfg(tmp_path)
        allowed, reason = auto_merge_allowed(cfg, "PRJ", 4, total_prs=60, pass_rate=0.5)
        assert not allowed
        assert "blockiert" in reason or "Schwellwert" in reason
