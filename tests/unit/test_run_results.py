"""Unit-Tests für SPEC-0006 – test_runner.py (TST-0019, TST-0020, TST-0021, TST-0022)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from sdd_cli.config import SddConfig
from sdd_cli.test_runner import (
    RunReport,
    TestResult,
    _persist,
    latest_report,
    run,
)

# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture()
def project(tmp_path: Path) -> SddConfig:
    """Minimales SDD-Projekt im tmp-Verzeichnis."""
    sdd_dir = tmp_path / ".sdd"
    sdd_dir.mkdir()
    (sdd_dir / "config.yaml").write_text(
        "ids:\n  padding: 4\ntest_runner:\n  command: pytest\n  timeout_per_spec: 30\n",
        encoding="utf-8",
    )
    (tmp_path / ".sdd" / "specs").mkdir(parents=True)
    (tmp_path / ".sdd" / "tests").mkdir(parents=True)
    (tmp_path / ".sdd" / "contracts").mkdir(parents=True)
    return SddConfig(root=tmp_path, raw={
        "ids": {"padding": 4},
        "test_runner": {"command": "pytest", "timeout_per_spec": 30},
    })


def _write_spec(project: SddConfig, spec_id: str, tests: list[str], contracts: list[str] | None = None) -> None:
    fm = (
        f"---\nid: {spec_id}\ntitle: Test Spec\nstatus: draft\n"
        f"contracts: {json.dumps(contracts or [])}\n"
        f"tests: {json.dumps(tests)}\n---\n\n# {spec_id}\n"
    )
    (project.specs_dir / f"{spec_id}-test.md").write_text(fm, encoding="utf-8")


def _write_tst(project: SddConfig, tst_id: str, artifact: str, contract: str = "CON-0017") -> None:
    level_dir = project.tests_dir / "unit"
    level_dir.mkdir(parents=True, exist_ok=True)
    fm = (
        f'---\nid: {tst_id}\ntitle: Test\nlevel: unit\n'
        f'spec: SPEC-0099\ncontract: {contract}\nstatus: planned\n'
        f'artifact: "{artifact}"\n---\n\n# {tst_id}\n'
    )
    (level_dir / f"{tst_id}-test.md").write_text(fm, encoding="utf-8")


# ─── TST-0019: JSON-Serialisierung / Deserialisierung ─────────────────────────

class TestRunJsonSerialization:
    def test_to_json_contains_required_fields(self):
        report = RunReport(
            spec_id="SPEC-0099",
            runner="pytest",
            started_at="2026-05-12T10:00:00+00:00",
            duration_s=1.5,
            exit_code=0,
            tests=[TestResult("TST-0001", "tests/unit/foo.py", "passed", 0.5)],
            contract_coverage={"CON-0017": True},
        )
        data = report.to_json()

        assert data["spec_id"] == "SPEC-0099"
        assert data["runner"] == "pytest"
        assert data["exit_code"] == 0
        assert data["passed"] == 1
        assert data["failed"] == 0
        assert data["skipped"] == 0
        assert data["contract_coverage"] == {"CON-0017": True}
        assert len(data["tests"]) == 1
        assert data["tests"][0]["status"] == "passed"

    def test_roundtrip_via_latest_report(self, project: SddConfig):
        report = RunReport(
            spec_id="SPEC-0099",
            runner="pytest",
            started_at="2026-05-12T10:00:00+00:00",
            duration_s=0.8,
            exit_code=1,
            tests=[
                TestResult("TST-A", "tests/unit/a.py", "passed", 0.3),
                TestResult("TST-B", "tests/unit/b.py", "failed", 0.5, "AssertionError"),
            ],
        )
        _persist(project, report)

        loaded = latest_report(project, "SPEC-0099")
        assert loaded is not None
        assert loaded.spec_id == "SPEC-0099"
        assert loaded.exit_code == 1
        assert len(loaded.tests) == 2
        assert loaded.tests[1].status == "failed"
        assert loaded.tests[1].message == "AssertionError"


# ─── TST-0020: Rotation – mehr als 50 Runs löscht den ältesten ────────────────

class TestRunRotation:
    def test_rotation_keeps_max_50(self, project: SddConfig):
        from sdd_cli.test_runner import MAX_RUNS_PER_SPEC

        for i in range(MAX_RUNS_PER_SPEC + 5):
            ts = f"2026-05-12T10:{i:02d}:00+00:00"
            report = RunReport("SPEC-0099", "pytest", ts, 0.1, 0)
            _persist(project, report)

        runs = list(project.test_runs_dir.glob("SPEC-0099-*.json"))
        assert len(runs) == MAX_RUNS_PER_SPEC

    def test_rotation_removes_oldest(self, project: SddConfig):
        from sdd_cli.test_runner import MAX_RUNS_PER_SPEC

        for i in range(MAX_RUNS_PER_SPEC + 1):
            ts = f"2026-05-12T{i:02d}:00:00+00:00"
            report = RunReport("SPEC-0099", "pytest", ts, 0.1, 0)
            _persist(project, report)

        runs = sorted(project.test_runs_dir.glob("SPEC-0099-*.json"))
        # älteste Datei (i=0) darf nicht mehr existieren
        oldest_ts = "2026-05-12T00-00-00+00-00"
        assert not any(oldest_ts in r.name for r in runs)


# ─── TST-0021: Leeres tests:-Frontmatter → ValueError ────────────────────────

class TestEmptyTestsFrontmatter:
    def test_raises_when_tests_list_empty(self, project: SddConfig):
        _write_spec(project, "SPEC-0099", tests=[])

        with pytest.raises(ValueError, match="keine Tests"):
            run(project, "SPEC-0099")

    def test_raises_when_tests_key_missing(self, project: SddConfig):
        fm = "---\nid: SPEC-0099\ntitle: T\nstatus: draft\ncontracts: []\ntests: []\n---\n\n# T\n"
        (project.specs_dir / "SPEC-0099-test.md").write_text(fm, encoding="utf-8")

        with pytest.raises(ValueError):
            run(project, "SPEC-0099")


# ─── TST-0022: Fehlendes Artefakt → status: missing ──────────────────────────

class TestMissingArtifact:
    def test_placeholder_artifact_gives_missing(self, project: SddConfig):
        _write_tst(project, "TST-0099", "tests/<level>/<name>.test.<ext>")
        _write_spec(project, "SPEC-0099", tests=["TST-0099"])

        report = run(project, "SPEC-0099")

        assert len(report.tests) == 1
        assert report.tests[0].status == "missing"
        assert report.exit_code == 0  # missing ist kein Fehler

    def test_nonexistent_tst_doc_gives_missing(self, project: SddConfig):
        _write_spec(project, "SPEC-0099", tests=["TST-9999"])

        report = run(project, "SPEC-0099")

        assert report.tests[0].status == "missing"

    def test_unsupported_extension_gives_skipped(self, project: SddConfig):
        _write_tst(project, "TST-0099", "tests/acceptance/login.feature")
        _write_spec(project, "SPEC-0099", tests=["TST-0099"])

        report = run(project, "SPEC-0099")

        assert report.tests[0].status == "skipped"
        assert report.exit_code == 0
