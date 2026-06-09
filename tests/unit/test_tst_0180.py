# TST-0180 – sdd finalize blockiert bei fehlendem FR-Test
# Spec: SPEC-0041 | Contract: CON-0153
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sdd_cli.compliance import (
    ComplianceIssue,
    FrCoverageChecker,
    run_compliance_chain,
)
from sdd_cli.frontmatter import Document
from sdd_cli.task_model import Task, TaskType, Complexity, ContextSize, TaskStatus


BODY_WITH_FR = """\
## 4. Funktionale Anforderungen

- **FR-01:** Erste Anforderung
"""


def _spec(body: str = BODY_WITH_FR, status: str = "in-progress") -> Document:
    return Document(
        path=Path("fake.md"),
        frontmatter={"id": "SPEC-TEST", "status": status, "tags": []},
        body=body,
    )


def _task_with_test(fr: str) -> Task:
    return Task(
        spec_id="SPEC-TEST",
        title=f"impl {fr}",
        description=f"Implements {fr}",
        type=TaskType.CODE,
        complexity=Complexity.LOW,
        context_size=ContextSize.S,
        estimated_tokens=100,
        status=TaskStatus.PENDING,
        test_ids=["TST-001"],
    )


class TestFinalizeComplianceGate:

    def test_uncovered_fr_blocks_finalize(self, tmp_path: Path) -> None:
        """FR-01 ohne Task-test_ids → compliance chain liefert error issues."""
        spec = _spec()
        issues = run_compliance_chain(
            spec=spec,
            tasks=[],
            cfg_raw={},
            tests_dir=tmp_path / ".sdd" / "tests",
            project_root=tmp_path,
        )
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) >= 1
        assert any("FR-01" in i.message for i in errors)

    def test_all_frs_covered_no_block(self, tmp_path: Path) -> None:
        spec = _spec()
        tasks = [_task_with_test("FR-01")]
        issues = run_compliance_chain(
            spec=spec,
            tasks=tasks,
            cfg_raw={},
            tests_dir=tmp_path / ".sdd" / "tests",
            project_root=tmp_path,
        )
        errors = [i for i in issues if i.severity == "error"]
        assert errors == []

    def test_fr_coverage_check_disabled_no_block(self, tmp_path: Path) -> None:
        spec = _spec()
        cfg = {"compliance": {"fr_coverage_check": False}}
        issues = run_compliance_chain(
            spec=spec,
            tasks=[],
            cfg_raw=cfg,
            tests_dir=tmp_path / ".sdd" / "tests",
            project_root=tmp_path,
        )
        fr_errors = [i for i in issues if i.fr_id is not None and i.severity == "error"]
        assert fr_errors == []

    def test_error_message_contains_actionable_hint(self, tmp_path: Path) -> None:
        spec = _spec()
        issues = run_compliance_chain(
            spec=spec,
            tasks=[],
            cfg_raw={},
            tests_dir=tmp_path / ".sdd" / "tests",
            project_root=tmp_path,
        )
        errors = [i for i in issues if i.severity == "error" and i.fr_id]
        assert errors, "Expected at least one FR error"
        assert all(i.hint for i in errors), "Every FR error should have a hint"
