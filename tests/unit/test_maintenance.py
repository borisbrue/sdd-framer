"""Unit-Tests für maintenance.py – Quality Maintenance Sweep (SPEC-0004 §3.8)."""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest

from sdd_cli.config import SddConfig
from sdd_cli.maintenance import (
    MaintenanceIssue,
    MaintenanceReport,
    _parse_date,
    run_maintenance_sweep,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _cfg(tmp_path: Path, raw: dict | None = None) -> SddConfig:
    sdd = tmp_path / ".sdd"
    (sdd / "specs").mkdir(parents=True)
    (sdd / "contracts").mkdir(parents=True)
    (sdd / "tests").mkdir(parents=True)
    return SddConfig(root=tmp_path, raw=raw or {})


def _write_spec(path: Path, spec_id: str, updated: str | None = None,
                contracts: list[str] | None = None, status: str = "draft") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"id: {spec_id}", f"status: {status}"]
    if updated:
        lines.append(f"updated: {updated}")
    if contracts is not None:
        lines.append(f"contracts: {contracts}")
    path.write_text("---\n" + "\n".join(lines) + "\n---\nbody\n", encoding="utf-8")


def _write_contract(path: Path, contract_id: str, spec_id: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\nid: {contract_id}\nspec: {spec_id}\n---\nbody\n", encoding="utf-8"
    )


def _write_test(path: Path, test_id: str, contract_id: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\nid: {test_id}\ncontract: {contract_id}\n---\nbody\n", encoding="utf-8"
    )


# ─── _parse_date ──────────────────────────────────────────────────────────────

class TestParseDate:
    def test_date_object(self):
        d = date(2026, 1, 1)
        assert _parse_date(d) == d

    def test_iso_string(self):
        assert _parse_date("2026-01-15") == date(2026, 1, 15)

    def test_invalid_string(self):
        assert _parse_date("not-a-date") is None

    def test_none_input(self):
        assert _parse_date(None) is None

    def test_int_input(self):
        assert _parse_date(20260101) is None


# ─── MaintenanceIssue ─────────────────────────────────────────────────────────

class TestMaintenanceIssue:
    def test_format_stale(self, tmp_path):
        issue = MaintenanceIssue(
            severity="stale",
            spec_id="SPEC-0001",
            spec_file=tmp_path / ".sdd" / "specs" / "SPEC-0001.md",
            message="30 Tagen alt",
            action="sdd orchestrate --spec SPEC-0001",
        )
        text = issue.format(tmp_path)
        assert "stale" in text
        assert "SPEC-0001.md" in text

    def test_format_missing_contract(self, tmp_path):
        issue = MaintenanceIssue(
            severity="missing_contract",
            spec_id="SPEC-0001",
            spec_file=tmp_path / "SPEC-0001.md",
            message="Keine Contracts",
            action="sdd new contract ...",
        )
        text = issue.format(tmp_path)
        assert "missing_contract" in text

    def test_to_dict(self, tmp_path):
        issue = MaintenanceIssue(
            severity="drift",
            spec_id="SPEC-0001",
            spec_file=tmp_path / "specs" / "SPEC-0001.md",
            message="Drift",
            action="fix it",
        )
        d = issue.to_dict(tmp_path)
        assert d["severity"] == "drift"
        assert d["spec_id"] == "SPEC-0001"
        assert d["action"] == "fix it"


# ─── MaintenanceReport ────────────────────────────────────────────────────────

class TestMaintenanceReport:
    def _make_issue(self, severity: str, tmp_path: Path) -> MaintenanceIssue:
        return MaintenanceIssue(
            severity=severity, spec_id="SPEC-0001",
            spec_file=tmp_path / "f.md", message="msg", action="act",
        )

    def test_stale_property(self, tmp_path):
        r = MaintenanceReport(stale_after_weeks=4)
        r.issues.append(self._make_issue("stale", tmp_path))
        r.issues.append(self._make_issue("missing_contract", tmp_path))
        assert len(r.stale) == 1
        assert len(r.drift) == 1

    def test_drift_property_excludes_stale(self, tmp_path):
        r = MaintenanceReport(stale_after_weeks=4)
        r.issues.append(self._make_issue("missing_test", tmp_path))
        assert len(r.stale) == 0
        assert len(r.drift) == 1

    def test_to_dict(self, tmp_path):
        r = MaintenanceReport(stale_after_weeks=4)
        r.issues.append(self._make_issue("stale", tmp_path))
        d = r.to_dict(tmp_path)
        assert d["stale_after_weeks"] == 4
        assert d["total_issues"] == 1
        assert d["stale_specs"] == 1
        assert d["drift_issues"] == 0
        assert len(d["issues"]) == 1


# ─── run_maintenance_sweep ────────────────────────────────────────────────────

class TestRunMaintenanceSweep:
    def test_empty_project_no_issues(self, tmp_path):
        cfg = _cfg(tmp_path)
        report = run_maintenance_sweep(cfg)
        assert len(report.issues) == 0

    def test_stale_spec_detected(self, tmp_path):
        cfg = _cfg(tmp_path, raw={"maintenance": {"stale_after_weeks": 4}})
        old_date = (date.today() - timedelta(weeks=5)).isoformat()
        _write_spec(
            tmp_path / ".sdd" / "specs" / "SPEC-0001.md",
            "SPEC-0001", updated=old_date, contracts=["CON-0001"]
        )
        _write_contract(tmp_path / ".sdd" / "contracts" / "CON-0001.md", "CON-0001", "SPEC-0001")
        _write_test(tmp_path / ".sdd" / "tests" / "TST-0001.md", "TST-0001", "CON-0001")
        report = run_maintenance_sweep(cfg)
        stale = [i for i in report.issues if i.severity == "stale"]
        assert len(stale) == 1
        assert stale[0].spec_id == "SPEC-0001"

    def test_recent_spec_not_stale(self, tmp_path):
        cfg = _cfg(tmp_path, raw={"maintenance": {"stale_after_weeks": 4}})
        recent_date = (date.today() - timedelta(days=7)).isoformat()
        _write_spec(
            tmp_path / ".sdd" / "specs" / "SPEC-0001.md",
            "SPEC-0001", updated=recent_date, contracts=["CON-0001"]
        )
        _write_contract(tmp_path / ".sdd" / "contracts" / "CON-0001.md", "CON-0001", "SPEC-0001")
        _write_test(tmp_path / ".sdd" / "tests" / "TST-0001.md", "TST-0001", "CON-0001")
        report = run_maintenance_sweep(cfg)
        stale = [i for i in report.issues if i.severity == "stale"]
        assert len(stale) == 0

    def test_spec_without_contracts_flagged(self, tmp_path):
        cfg = _cfg(tmp_path)
        _write_spec(tmp_path / ".sdd" / "specs" / "SPEC-0001.md",
                    "SPEC-0001", contracts=[])
        report = run_maintenance_sweep(cfg)
        missing = [i for i in report.issues if i.severity == "missing_contract"]
        assert len(missing) == 1
        assert missing[0].spec_id == "SPEC-0001"

    def test_contract_without_test_flagged(self, tmp_path):
        cfg = _cfg(tmp_path)
        _write_spec(
            tmp_path / ".sdd" / "specs" / "SPEC-0001.md",
            "SPEC-0001", contracts=["CON-0001"]
        )
        _write_contract(tmp_path / ".sdd" / "contracts" / "CON-0001.md", "CON-0001", "SPEC-0001")
        # No test linked to CON-0001
        report = run_maintenance_sweep(cfg)
        missing_tests = [i for i in report.issues if i.severity == "missing_test"]
        assert len(missing_tests) == 1
        assert "CON-0001" in missing_tests[0].message

    def test_contract_with_test_not_flagged(self, tmp_path):
        cfg = _cfg(tmp_path)
        _write_spec(
            tmp_path / ".sdd" / "specs" / "SPEC-0001.md",
            "SPEC-0001", contracts=["CON-0001"]
        )
        _write_contract(tmp_path / ".sdd" / "contracts" / "CON-0001.md", "CON-0001", "SPEC-0001")
        _write_test(tmp_path / ".sdd" / "tests" / "TST-0001.md", "TST-0001", "CON-0001")
        report = run_maintenance_sweep(cfg)
        missing_tests = [i for i in report.issues if i.severity == "missing_test"]
        assert len(missing_tests) == 0

    def test_deprecated_spec_ignored(self, tmp_path):
        cfg = _cfg(tmp_path)
        old_date = (date.today() - timedelta(weeks=10)).isoformat()
        _write_spec(
            tmp_path / ".sdd" / "specs" / "SPEC-0001.md",
            "SPEC-0001", updated=old_date, contracts=[], status="deprecated"
        )
        report = run_maintenance_sweep(cfg)
        assert len(report.issues) == 0

    def test_archived_spec_ignored(self, tmp_path):
        cfg = _cfg(tmp_path)
        old_date = (date.today() - timedelta(weeks=10)).isoformat()
        _write_spec(
            tmp_path / ".sdd" / "specs" / "SPEC-0001.md",
            "SPEC-0001", updated=old_date, contracts=[], status="archived"
        )
        report = run_maintenance_sweep(cfg)
        assert len(report.issues) == 0

    def test_no_updated_field_not_stale(self, tmp_path):
        cfg = _cfg(tmp_path)
        _write_spec(tmp_path / ".sdd" / "specs" / "SPEC-0001.md",
                    "SPEC-0001", updated=None, contracts=["CON-0001"])
        _write_contract(tmp_path / ".sdd" / "contracts" / "CON-0001.md", "CON-0001", "SPEC-0001")
        _write_test(tmp_path / ".sdd" / "tests" / "TST-0001.md", "TST-0001", "CON-0001")
        report = run_maintenance_sweep(cfg)
        stale = [i for i in report.issues if i.severity == "stale"]
        assert len(stale) == 0

    def test_stale_weeks_configurable(self, tmp_path):
        cfg = _cfg(tmp_path, raw={"maintenance": {"stale_after_weeks": 1}})
        slightly_old = (date.today() - timedelta(weeks=2)).isoformat()
        _write_spec(
            tmp_path / ".sdd" / "specs" / "SPEC-0001.md",
            "SPEC-0001", updated=slightly_old, contracts=["CON-0001"]
        )
        _write_contract(tmp_path / ".sdd" / "contracts" / "CON-0001.md", "CON-0001", "SPEC-0001")
        _write_test(tmp_path / ".sdd" / "tests" / "TST-0001.md", "TST-0001", "CON-0001")
        report = run_maintenance_sweep(cfg)
        assert report.stale_after_weeks == 1
        stale = [i for i in report.issues if i.severity == "stale"]
        assert len(stale) == 1

    def test_report_stale_after_weeks_default(self, tmp_path):
        cfg = _cfg(tmp_path)
        report = run_maintenance_sweep(cfg)
        assert report.stale_after_weeks == 4

    def test_sweep_action_contains_spec_id(self, tmp_path):
        cfg = _cfg(tmp_path)
        _write_spec(tmp_path / ".sdd" / "specs" / "SPEC-0001.md",
                    "SPEC-0001", contracts=[])
        report = run_maintenance_sweep(cfg)
        assert any("SPEC-0001" in i.action for i in report.issues)
