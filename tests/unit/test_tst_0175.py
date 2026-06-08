# TST-0175
# Contract: CON-0151 – Antwortzeitanforderungen (SLO, v0.1.0)
# Level: performance (offline – validates SLO YAML structure and p95/p99 calculations)

from __future__ import annotations

import math
from pathlib import Path

import pytest
import yaml

_SLO_PATH = (
    Path(__file__).resolve().parents[2]
    / "contracts" / "performance" / "antwortzeitanforderungen-slo.slo.yaml"
)


def _load_slos() -> list[dict]:
    with open(_SLO_PATH, encoding="utf-8") as fh:
        return yaml.safe_load(fh)["slos"]


def percentile(samples: list[float], p: float) -> float:
    if not samples:
        raise ValueError("Keine Messungen")
    sorted_samples = sorted(samples)
    idx = math.ceil(p / 100 * len(sorted_samples)) - 1
    return sorted_samples[max(idx, 0)]


def slo_passes(samples: list[float], threshold: float, p: float) -> bool:
    return percentile(samples, p) <= threshold


@pytest.fixture(scope="module")
def slos() -> list[dict]:
    return _load_slos()


def _find(slos: list[dict], name: str) -> dict:
    return next(s for s in slos if s["name"] == name)


class TestTST0175:
    """CON-0151: SLO-Einhaltung – Antwortzeitanforderungen (p95/p99)."""

    def test_slo_file_exists(self):
        assert _SLO_PATH.exists()

    def test_slo_file_is_valid_yaml_with_slos_key(self):
        doc = yaml.safe_load(_SLO_PATH.read_text(encoding="utf-8"))
        assert "slos" in doc and isinstance(doc["slos"], list)

    def test_slo_count_matches_contract(self, slos):
        assert len(slos) == 5

    def test_all_slos_have_required_fields(self, slos):
        for slo in slos:
            assert {"name", "objective", "sli"} <= slo.keys()
            assert {"threshold", "aggregation"} <= slo["sli"].keys()

    # ── SLO-1: initial_status_load – p95 ≤ 2s ───────────────────────────────

    def test_slo1_threshold_is_2s(self, slos):
        slo = _find(slos, "initial_status_load")
        assert slo["sli"]["threshold"] == 2.0
        assert slo["sli"]["aggregation"] == "p95"
        assert slo["objective"] == 95

    def test_slo1_passes_when_p95_within_2s(self):
        samples = [0.5, 0.8, 1.0, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8,
                   0.6, 0.9, 1.1, 1.3, 1.5, 1.6, 1.7, 1.8, 1.9, 1.95]
        assert slo_passes(samples, threshold=2.0, p=95)

    def test_slo1_fails_when_p95_exceeds_2s(self):
        samples = [0.5] * 18 + [2.1, 2.5]
        assert not slo_passes(samples, threshold=2.0, p=95)

    # ── SLO-2: action_status_visibility – p95 ≤ 5s ──────────────────────────

    def test_slo2_threshold_is_5s(self, slos):
        slo = _find(slos, "action_status_visibility")
        assert slo["sli"]["threshold"] == 5.0
        assert slo["sli"]["aggregation"] == "p95"
        assert slo["objective"] == 95

    def test_slo2_passes_when_p95_within_5s(self):
        samples = [1.0] * 18 + [4.5, 4.9]
        assert slo_passes(samples, threshold=5.0, p=95)

    def test_slo2_fails_when_p95_exceeds_5s(self):
        samples = [1.0] * 18 + [5.1, 5.5]
        assert not slo_passes(samples, threshold=5.0, p=95)

    # ── SLO-3: offline_indicator_latency – p99 ≤ 3s ─────────────────────────

    def test_slo3_threshold_is_3s_p99(self, slos):
        slo = _find(slos, "offline_indicator_latency")
        assert slo["sli"]["threshold"] == 3.0
        assert slo["sli"]["aggregation"] == "p99"
        assert slo["objective"] == 99

    def test_slo3_passes_when_p99_within_3s(self):
        samples = [0.5] * 98 + [2.8, 2.9]
        assert slo_passes(samples, threshold=3.0, p=99)

    def test_slo3_fails_when_p99_exceeds_3s(self):
        samples = [0.5] * 98 + [3.1, 3.5]
        assert not slo_passes(samples, threshold=3.0, p=99)

    # ── SLO-4: project_list_completeness – min ratio = 1.0 (100%) ────────────

    def test_slo4_completeness_objective_is_100(self, slos):
        slo = _find(slos, "project_list_completeness")
        assert slo["objective"] == 100
        assert slo["sli"]["threshold"] == 1.0
        assert slo["sli"]["aggregation"] == "min"

    # ── SLO-5: phantom_action_rate – 0% phantom actions ─────────────────────

    def test_slo5_phantom_action_rate_is_zero(self, slos):
        slo = _find(slos, "phantom_action_rate")
        assert slo["objective"] == 100
        assert slo["sli"]["threshold"] == 1.0
        assert slo["sli"]["aggregation"] == "min"

    # ── Statistical helper ────────────────────────────────────────────────────

    def test_percentile_single_sample(self):
        assert percentile([1.5], 95) == 1.5

    def test_percentile_empty_raises(self):
        with pytest.raises(ValueError):
            percentile([], 95)

    def test_p95_of_1_to_100(self):
        samples = list(range(1, 101))
        assert percentile(samples, 95) == 95

    def test_p99_of_1_to_100(self):
        samples = list(range(1, 101))
        assert percentile(samples, 99) == 99

    def test_slo_passes_at_exact_threshold(self):
        samples = [2.0] * 20
        assert slo_passes(samples, threshold=2.0, p=95)

    def test_slo_fails_just_above_threshold(self):
        samples = [2.0] * 18 + [2.001, 2.001]
        assert not slo_passes(samples, threshold=2.0, p=95)
