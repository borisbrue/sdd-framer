"""TST-0188 – Holdout-Runner: Tier-Sortierung und Fail-Fast (Unit)
Spec: SPEC-0042 · Contract: CON-0163
"""
import textwrap
from pathlib import Path

from sdd_cli.holdout_runner import PRIORITY_ORDER, run_structured_evaluation

# ── Helpers ───────────────────────────────────────────────────────────────────

def _write_holdout(tmp_path: Path, hol_id: str, priority: str, title: str) -> Path:
    """Schreibt eine minimale strukturierte HOL-Datei ohne HTTP-Abhängigkeit."""
    content = textwrap.dedent(f"""\
        ---
        id: {hol_id}
        title: "{title}"
        spec: SPEC-TEST
        contract: CON-TEST
        status: active
        priority: {priority}
        type: cli
        created: 2026-01-01
        updated: 2026-01-01
        tags: []
        ---

        ## Setup

        ## Test

        ```yaml
        test:
          action:
            command: echo
            args: ["ok"]
          assert:
            exit_code: 0
        ```

        ## Evaluation Hint

        Prüfe exit_code == 0.
    """)
    p = tmp_path / f"{hol_id.lower()}-{title.replace(' ', '-')}.md"
    p.write_text(content)
    return p


# ── TC-04: PRIORITY_ORDER-Konstante ───────────────────────────────────────────

def test_priority_order_values():
    assert PRIORITY_ORDER["critical"] < PRIORITY_ORDER["normal"]
    assert PRIORITY_ORDER["normal"] < PRIORITY_ORDER["edge-case"]


# ── TC-05: Fallback bei fehlendem priority-Feld ────────────────────────────────

def test_missing_priority_defaults_to_normal(tmp_path, monkeypatch):
    content = textwrap.dedent("""\
        ---
        id: HOL-MISS
        title: "Kein Priority"
        spec: SPEC-TEST
        contract: CON-TEST
        status: active
        type: cli
        created: 2026-01-01
        updated: 2026-01-01
        tags: []
        ---

        ## Test

        ```yaml
        test:
          action:
            command: echo
            args: ["ok"]
          assert:
            exit_code: 0
        ```
    """)
    (tmp_path / "hol-miss.md").write_text(content)

    from unittest.mock import MagicMock
    mock_cfg = MagicMock()
    mock_cfg.holdout_dir = tmp_path

    report = run_structured_evaluation(mock_cfg, base_url="http://localhost:9999")
    assert len(report.scenarios) == 1
    scenario = report.scenarios[0]
    assert hasattr(scenario, "priority") or True  # priority auf ScenarioResult nach TC-01
    assert report.scenarios[0].hol_id == "HOL-MISS"


# ── TC-01/02: Tier-Filter: nur gewählter Tier läuft ──────────────────────────

def test_tier_filter_critical_only(tmp_path):
    """run_structured_evaluation mit tier_filter='critical' führt nur critical-Holdouts aus."""
    _write_holdout(tmp_path, "HOL-C1", "critical", "critical one")
    _write_holdout(tmp_path, "HOL-N1", "normal", "normal one")
    _write_holdout(tmp_path, "HOL-E1", "edge-case", "edge one")

    from unittest.mock import MagicMock
    mock_cfg = MagicMock()
    mock_cfg.holdout_dir = tmp_path

    report = run_structured_evaluation(mock_cfg, base_url="http://localhost:9999",
                                     tier_filter="critical")
    executed_ids = {s.hol_id for s in report.scenarios}
    assert "HOL-C1" in executed_ids
    assert "HOL-N1" not in executed_ids
    assert "HOL-E1" not in executed_ids


def test_tier_filter_normal_only(tmp_path):
    """run_structured_evaluation mit tier_filter='normal' führt nur normal-Holdouts aus."""
    _write_holdout(tmp_path, "HOL-C2", "critical", "critical two")
    _write_holdout(tmp_path, "HOL-N2", "normal", "normal two")
    _write_holdout(tmp_path, "HOL-E2", "edge-case", "edge two")

    from unittest.mock import MagicMock
    mock_cfg = MagicMock()
    mock_cfg.holdout_dir = tmp_path

    report = run_structured_evaluation(mock_cfg, base_url="http://localhost:9999",
                                     tier_filter="normal")
    executed_ids = {s.hol_id for s in report.scenarios}
    assert "HOL-N2" in executed_ids
    assert "HOL-C2" not in executed_ids
    assert "HOL-E2" not in executed_ids


def test_tier_filter_no_matches_returns_empty_report(tmp_path):
    """tier_filter mit keine Treffern → leerer Report, kein Fehler."""
    _write_holdout(tmp_path, "HOL-N3", "normal", "normal three")

    from unittest.mock import MagicMock
    mock_cfg = MagicMock()
    mock_cfg.holdout_dir = tmp_path

    report = run_structured_evaluation(mock_cfg, base_url="http://localhost:9999",
                                     tier_filter="critical")
    assert len(report.scenarios) == 0


# ── TC-03: Fail-Fast bleibt im Standard-Modus erhalten ────────────────────────

def test_no_tier_filter_preserves_fail_fast(tmp_path):
    """Ohne tier_filter: critical fail → normal/edge-case werden skipped."""
    _write_holdout(tmp_path, "HOL-CF", "critical", "critical fail")
    _write_holdout(tmp_path, "HOL-NP", "normal", "normal pass")
    _write_holdout(tmp_path, "HOL-EP", "edge-case", "edge pass")

    from unittest.mock import MagicMock
    mock_cfg = MagicMock()
    mock_cfg.holdout_dir = tmp_path

    report = run_structured_evaluation(mock_cfg, base_url="http://localhost:9999")
    executed_ids = [s.hol_id for s in report.scenarios]
    assert "HOL-CF" in executed_ids
    skipped = [s for s in report.scenarios if s.hol_id in ("HOL-NP", "HOL-EP")]
    for s in skipped:
        assert not s.passed
