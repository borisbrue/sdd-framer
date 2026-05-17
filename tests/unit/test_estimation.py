"""Unit-Tests für estimation.py – Token-Kostenschätzung (SPEC-0011)."""
from __future__ import annotations

import math
import sqlite3
from pathlib import Path

import pytest

from sdd_cli.config import SddConfig
from sdd_cli.estimation import (
    SpecFeatures,
    HistoricalPoint,
    Neighbor,
    init_token_usage_table,
    persist_token_usage,
    extract_features,
    _normalize,
    _euclidean,
    _calc_usd,
    _confidence,
    _load_historical,
    _knn,
    PRIORITY_WEIGHTS,
    TOKEN_USAGE_TABLE,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _cfg(tmp_path: Path) -> SddConfig:
    sdd = tmp_path / ".sdd"
    sdd.mkdir(parents=True, exist_ok=True)
    return SddConfig(root=tmp_path, raw={})


def _write_spec(path: Path, spec_id: str = "SPEC-0001",
                contracts: int = 1, tests: int = 1,
                priority: str = "medium", body: str = "",
                depends_on: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    dep_yaml = f"\ndepends_on: {depends_on}" if depends_on else ""
    path.write_text(
        f"---\nid: {spec_id}\ntitle: T\nstatus: draft\nowner: b\n"
        f"created: 2026-01-01\nupdated: 2026-01-01\n"
        f"contracts: {[f'CON-{i:04d}' for i in range(contracts)]}\n"
        f"tests: {[f'TST-{i:04d}' for i in range(tests)]}\n"
        f"priority: {priority}{dep_yaml}\n---\n{body}\n",
        encoding="utf-8",
    )


# ─── init_token_usage_table ───────────────────────────────────────────────────

class TestInitTokenUsageTable:
    def test_creates_table(self, tmp_path):
        cfg = _cfg(tmp_path)
        init_token_usage_table(cfg)
        db = tmp_path / ".sdd" / "evaluations.db"
        assert db.exists()
        with sqlite3.connect(db) as conn:
            tables = [r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()]
        assert TOKEN_USAGE_TABLE in tables

    def test_idempotent(self, tmp_path):
        cfg = _cfg(tmp_path)
        init_token_usage_table(cfg)
        init_token_usage_table(cfg)  # must not raise


# ─── persist_token_usage ──────────────────────────────────────────────────────

class TestPersistTokenUsage:
    def test_stores_row(self, tmp_path):
        cfg = _cfg(tmp_path)
        persist_token_usage(
            cfg,
            component="evaluator",
            model="claude-sonnet-4-6",
            input_tokens=1000,
            output_tokens=200,
            spec_id="SPEC-0001",
        )
        db = tmp_path / ".sdd" / "evaluations.db"
        with sqlite3.connect(db) as conn:
            row = conn.execute(f"SELECT * FROM {TOKEN_USAGE_TABLE}").fetchone()
        assert row is not None
        assert row[2] == "SPEC-0001"   # spec_id
        assert row[3] == "evaluator"   # component

    def test_stores_cache_tokens(self, tmp_path):
        cfg = _cfg(tmp_path)
        persist_token_usage(
            cfg,
            component="codegen",
            model="claude-opus-4-7",
            input_tokens=500,
            output_tokens=100,
            cache_read_tokens=200,
            cache_write_tokens=50,
        )
        db = tmp_path / ".sdd" / "evaluations.db"
        with sqlite3.connect(db) as conn:
            row = conn.execute(
                f"SELECT cache_read_tokens, cache_write_tokens FROM {TOKEN_USAGE_TABLE}"
            ).fetchone()
        assert row[0] == 200
        assert row[1] == 50

    def test_silently_ignores_errors(self, tmp_path):
        cfg = SddConfig(root=Path("/nonexistent/path"), raw={})
        persist_token_usage(cfg, component="c", model="m",
                            input_tokens=1, output_tokens=1)
        # must not raise


# ─── extract_features ─────────────────────────────────────────────────────────

class TestExtractFeatures:
    def test_basic_extraction(self, tmp_path):
        path = tmp_path / "SPEC-0001.md"
        _write_spec(path, "SPEC-0001", contracts=2, tests=3, priority="high")
        ft = extract_features(path)
        assert ft is not None
        assert ft.spec_id == "SPEC-0001"
        assert ft.contract_count == 2
        assert ft.test_count == 3
        assert ft.priority_weight == PRIORITY_WEIGHTS["high"]

    def test_returns_none_for_no_frontmatter(self, tmp_path):
        path = tmp_path / "no_fm.md"
        path.write_text("no frontmatter here", encoding="utf-8")
        assert extract_features(path) is None

    def test_user_story_count(self, tmp_path):
        path = tmp_path / "SPEC-0001.md"
        body = "| US-001 | Story 1 |\n| US-002 | Story 2 |\n| not-us | other |"
        _write_spec(path, "SPEC-0001", body=body)
        ft = extract_features(path)
        assert ft.user_story_count == 2

    def test_fr_count(self, tmp_path):
        path = tmp_path / "SPEC-0001.md"
        body = "**FR-001** first\n**FR-002** second\n**FR-003** third"
        _write_spec(path, "SPEC-0001", body=body)
        ft = extract_features(path)
        assert ft.fr_count == 3

    def test_dependency_count(self, tmp_path):
        path = tmp_path / "SPEC-0001.md"
        _write_spec(path, "SPEC-0001", depends_on=["SPEC-0002", "SPEC-0003"])
        ft = extract_features(path)
        assert ft.dependency_count == 2

    def test_priority_weights(self, tmp_path):
        for priority, expected in PRIORITY_WEIGHTS.items():
            path = tmp_path / f"{priority}.md"
            _write_spec(path, "SPEC-0001", priority=priority)
            ft = extract_features(path)
            assert ft.priority_weight == expected

    def test_unknown_priority_defaults_to_medium(self, tmp_path):
        path = tmp_path / "SPEC-0001.md"
        _write_spec(path, "SPEC-0001", priority="unknown_priority")
        ft = extract_features(path)
        assert ft.priority_weight == PRIORITY_WEIGHTS["medium"]

    def test_body_chars_counted(self, tmp_path):
        path = tmp_path / "SPEC-0001.md"
        body = "x" * 500
        _write_spec(path, "SPEC-0001", body=body)
        ft = extract_features(path)
        assert ft.body_chars >= 500


# ─── SpecFeatures.as_vector ───────────────────────────────────────────────────

class TestSpecFeaturesAsVector:
    def test_returns_float_list(self):
        ft = SpecFeatures(
            spec_id="SPEC-0001", body_chars=100, contract_count=2, test_count=3,
            user_story_count=1, fr_count=5, dependency_count=0, priority_weight=2,
        )
        vec = ft.as_vector()
        assert len(vec) == 7
        assert all(isinstance(v, float) for v in vec)

    def test_vector_values_match_fields(self):
        ft = SpecFeatures(
            spec_id="SPEC-0001", body_chars=200, contract_count=3, test_count=4,
            user_story_count=2, fr_count=6, dependency_count=1, priority_weight=3,
        )
        vec = ft.as_vector()
        assert vec[0] == 200.0
        assert vec[1] == 3.0
        assert vec[6] == 3.0


# ─── _normalize ───────────────────────────────────────────────────────────────

class TestNormalize:
    def test_empty_returns_empty(self):
        normed, mins, ranges = _normalize([])
        assert normed == [] and mins == [] and ranges == []

    def test_single_vector(self):
        normed, mins, ranges = _normalize([[1.0, 2.0, 3.0]])
        assert len(normed) == 1
        # Single vector → all values normalized to 0 (min==max → range=1)
        assert all(v == 0.0 for v in normed[0])

    def test_two_vectors_normalized_to_0_1(self):
        normed, _, _ = _normalize([[0.0, 0.0], [1.0, 10.0]])
        # First vector should be all 0s
        assert normed[0] == [0.0, 0.0]
        # Second vector should be all 1s
        assert normed[1] == [1.0, 1.0]

    def test_equal_values_range_is_one(self):
        normed, _, ranges = _normalize([[5.0], [5.0]])
        assert ranges[0] == 1.0  # prevents division by zero


# ─── _euclidean ───────────────────────────────────────────────────────────────

class TestEuclidean:
    def test_identical_vectors_distance_zero(self):
        assert _euclidean([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == 0.0

    def test_unit_vectors(self):
        d = _euclidean([0.0, 0.0], [1.0, 0.0])
        assert abs(d - 1.0) < 1e-9

    def test_3d_distance(self):
        d = _euclidean([0.0, 0.0, 0.0], [1.0, 1.0, 1.0])
        assert abs(d - math.sqrt(3)) < 1e-9


# ─── _calc_usd ────────────────────────────────────────────────────────────────

class TestCalcUsd:
    def _price(self, input_pm=3.0, output_pm=15.0,
               cache_read_pm=0.08, cache_write_pm=1.0):
        return {
            "input_per_million": input_pm,
            "output_per_million": output_pm,
            "cache_read_per_million": cache_read_pm,
            "cache_write_per_million": cache_write_pm,
        }

    def test_zero_tokens_zero_cost(self):
        assert _calc_usd(self._price(), 0, 0) == 0.0

    def test_input_only(self):
        # 1M input tokens at $3/M = $3
        cost = _calc_usd(self._price(), input_t=1_000_000, output_t=0)
        assert abs(cost - 3.0) < 1e-4

    def test_output_only(self):
        # 1M output tokens at $15/M = $15
        cost = _calc_usd(self._price(), input_t=0, output_t=1_000_000)
        assert abs(cost - 15.0) < 1e-4

    def test_cache_tokens(self):
        # 1M cache read at $0.08/M = $0.08
        cost = _calc_usd(self._price(), input_t=0, output_t=0,
                         cache_read_t=1_000_000, cache_write_t=0)
        assert abs(cost - 0.08) < 1e-4

    def test_result_rounded_to_6_decimals(self):
        cost = _calc_usd(self._price(), 1234, 567)
        assert len(str(cost).split(".")[-1]) <= 6


# ─── _confidence ──────────────────────────────────────────────────────────────

class TestConfidence:
    def test_low_below_3(self):
        assert _confidence(0) == "LOW"
        assert _confidence(2) == "LOW"

    def test_medium_3_to_9(self):
        assert _confidence(3) == "MEDIUM"
        assert _confidence(9) == "MEDIUM"

    def test_high_10_plus(self):
        assert _confidence(10) == "HIGH"
        assert _confidence(100) == "HIGH"


# ─── _load_historical ─────────────────────────────────────────────────────────

class TestLoadHistorical:
    def test_empty_db_returns_empty(self, tmp_path):
        cfg = _cfg(tmp_path)
        result = _load_historical(cfg)
        assert result == []

    def test_no_db_file_returns_empty(self, tmp_path):
        cfg = _cfg(tmp_path)
        result = _load_historical(cfg)
        assert result == []

    def test_loads_aggregated_per_spec(self, tmp_path):
        cfg = _cfg(tmp_path)
        persist_token_usage(cfg, component="c", model="m",
                            input_tokens=100, output_tokens=50, spec_id="SPEC-0001")
        persist_token_usage(cfg, component="c", model="m",
                            input_tokens=200, output_tokens=30, spec_id="SPEC-0001")
        result = _load_historical(cfg)
        assert len(result) == 1
        assert result[0].input_tokens == 300
        assert result[0].output_tokens == 80

    def test_separate_specs_separate_points(self, tmp_path):
        cfg = _cfg(tmp_path)
        persist_token_usage(cfg, component="c", model="m",
                            input_tokens=100, output_tokens=50, spec_id="SPEC-0001")
        persist_token_usage(cfg, component="c", model="m",
                            input_tokens=200, output_tokens=30, spec_id="SPEC-0002")
        result = _load_historical(cfg)
        assert len(result) == 2
