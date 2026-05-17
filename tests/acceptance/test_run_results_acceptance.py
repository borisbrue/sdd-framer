"""Acceptance-Tests für SPEC-0006 – Gherkin-Szenarien aus CON-0018 (TST-0023)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from sdd_cli.config import SddConfig
from sdd_cli.test_runner import RunReport, TestResult, _persist, latest_report, run


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture()
def project(tmp_path: Path) -> SddConfig:
    sdd_dir = tmp_path / ".sdd"
    sdd_dir.mkdir()
    (sdd_dir / "config.yaml").write_text(
        "ids:\n  padding: 4\ntest_runner:\n  command: pytest\n  timeout_per_spec: 30\n",
        encoding="utf-8",
    )
    for d in [".sdd/specs", ".sdd/tests", ".sdd/contracts", "tests/unit"]:
        (tmp_path / d).mkdir(parents=True)
    return SddConfig(root=tmp_path, raw={
        "ids": {"padding": 4},
        "test_runner": {"command": "pytest", "timeout_per_spec": 30},
    })


def _write_spec(p: SddConfig, spec_id: str, tests: list[str], contracts: list[str] | None = None) -> None:
    fm = (
        f"---\nid: {spec_id}\ntitle: T\nstatus: draft\n"
        f"contracts: {json.dumps(contracts or [])}\ntests: {json.dumps(tests)}\n---\n\n# T\n"
    )
    (p.specs_dir / f"{spec_id}-t.md").write_text(fm, encoding="utf-8")


def _write_tst(p: SddConfig, tst_id: str, artifact: str, contract: str = "CON-0017") -> None:
    d = p.tests_dir / "unit"
    d.mkdir(parents=True, exist_ok=True)
    fm = (
        f'---\nid: {tst_id}\ntitle: T\nlevel: unit\nspec: SPEC-0099\n'
        f'contract: {contract}\nstatus: planned\nartifact: "{artifact}"\n---\n\n# T\n'
    )
    (d / f"{tst_id}.md").write_text(fm, encoding="utf-8")


# ─── Szenario: Test-Run auslösen → Run-JSON wird persistiert ─────────────────

class TestTriggerTestRun:
    """Entspricht Szenario 'Test-Run für eine Spec auslösen' aus CON-0018."""

    def test_run_creates_json_file(self, project: SddConfig, tmp_path: Path):
        passing_test = tmp_path / "tests" / "unit" / "test_trivial.py"
        passing_test.write_text("def test_ok(): assert True\n", encoding="utf-8")

        _write_tst(project, "TST-0099", "tests/unit/test_trivial.py")
        _write_spec(project, "SPEC-0099", tests=["TST-0099"], contracts=["CON-0017"])

        report = run(project, "SPEC-0099")

        assert project.test_runs_dir.exists()
        saved = list(project.test_runs_dir.glob("SPEC-0099-*.json"))
        assert len(saved) == 1

        data = json.loads(saved[0].read_text())
        assert data["spec_id"] == "SPEC-0099"
        assert data["exit_code"] == 0

    def test_passing_test_sets_exit_code_0(self, project: SddConfig, tmp_path: Path):
        passing_test = tmp_path / "tests" / "unit" / "test_pass.py"
        passing_test.write_text("def test_ok(): assert True\n", encoding="utf-8")

        _write_tst(project, "TST-0099", "tests/unit/test_pass.py")
        _write_spec(project, "SPEC-0099", tests=["TST-0099"])

        report = run(project, "SPEC-0099")
        assert report.exit_code == 0
        assert report.passed == 1

    def test_failing_test_sets_exit_code_1(self, project: SddConfig, tmp_path: Path):
        failing_test = tmp_path / "tests" / "unit" / "test_fail.py"
        failing_test.write_text("def test_nok(): assert False\n", encoding="utf-8")

        _write_tst(project, "TST-0099", "tests/unit/test_fail.py")
        _write_spec(project, "SPEC-0099", tests=["TST-0099"])

        report = run(project, "SPEC-0099")
        assert report.exit_code == 1
        assert report.failed == 1
        assert report.tests[0].message  # Fehlermeldung vorhanden


# ─── Szenario: Ergebnisübersicht abrufen ─────────────────────────────────────

class TestFetchResults:
    """Entspricht Szenario 'Ergebnisübersicht abrufen' aus CON-0018."""

    def test_latest_report_returns_last_run(self, project: SddConfig):
        for i in range(3):
            ts = f"2026-05-12T1{i}:00:00+00:00"
            r = RunReport("SPEC-0099", "pytest", ts, 0.1, i % 2)
            _persist(project, r)

        loaded = latest_report(project, "SPEC-0099")
        assert loaded is not None
        assert loaded.started_at == "2026-05-12T12:00:00+00:00"

    def test_no_run_returns_none(self, project: SddConfig):
        assert latest_report(project, "SPEC-9999") is None


# ─── Szenario: Spec ohne Tests ────────────────────────────────────────────────

class TestSpecWithoutTests:
    """Entspricht Szenario 'Spec ohne verknüpfte Tests' aus CON-0018."""

    def test_raises_value_error(self, project: SddConfig):
        _write_spec(project, "SPEC-0099", tests=[])
        with pytest.raises(ValueError):
            run(project, "SPEC-0099")


# ─── Szenario: Contract-Coverage ─────────────────────────────────────────────

class TestContractCoverage:
    """Prüft dass Contract-Coverage korrekt berechnet wird."""

    def test_covered_contract_when_test_passes(self, project: SddConfig, tmp_path: Path):
        passing_test = tmp_path / "tests" / "unit" / "test_cov.py"
        passing_test.write_text("def test_ok(): assert True\n", encoding="utf-8")

        _write_tst(project, "TST-0099", "tests/unit/test_cov.py", contract="CON-0017")
        _write_spec(project, "SPEC-0099", tests=["TST-0099"], contracts=["CON-0017"])

        report = run(project, "SPEC-0099")
        assert report.contract_coverage.get("CON-0017") is True

    def test_uncovered_contract_when_test_missing(self, project: SddConfig):
        _write_tst(project, "TST-0099", "tests/<level>/<name>.test.<ext>", contract="CON-0017")
        _write_spec(project, "SPEC-0099", tests=["TST-0099"], contracts=["CON-0017"])

        report = run(project, "SPEC-0099")
        assert report.contract_coverage.get("CON-0017") is False
