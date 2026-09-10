# TST-0181 – sdd spec approve blockiert bei fehlendem FR-Test
# Spec: SPEC-0041 | Contract: CON-0153
from pathlib import Path

from sdd_cli.compliance import FrCoverageSpecification

BODY_WITH_FR = """\
## 4. Funktionale Anforderungen

- **FR-01:** Erste Anforderung
- **FR-02:** Zweite Anforderung
"""


class TestSpecApproveCompliance:
    """Prüft FrCoverageSpecification als Kern des spec_approve-Enforcement."""

    def test_uncovered_fr_produces_uncovered_list(self, tmp_path: Path) -> None:
        from sdd_cli.frontmatter import Document
        from sdd_cli.task_model import Complexity, ContextSize, Task, TaskStatus, TaskType

        spec = Document(
            path=tmp_path / "SPEC-TEST.md",
            frontmatter={"id": "SPEC-TEST", "status": "approved", "tests": ["TST-001"]},
            body=BODY_WITH_FR,
        )
        tasks = [
            Task(
                spec_id="SPEC-TEST",
                title="FR-01 impl",
                description="Implements FR-01 logic",
                type=TaskType.CODE,
                complexity=Complexity.LOW,
                context_size=ContextSize.S,
                estimated_tokens=100,
                status=TaskStatus.PENDING,
                test_ids=["TST-001"],
            )
        ]
        # FR-02 hat kein Task mit test_ids → uncovered
        result = FrCoverageSpecification().is_satisfied_by(spec, tasks)
        assert "FR-02" in result.uncovered
        assert "FR-01" in result.covered

    def test_all_frs_covered_passes(self, tmp_path: Path) -> None:
        from sdd_cli.frontmatter import Document
        from sdd_cli.task_model import Complexity, ContextSize, Task, TaskStatus, TaskType

        spec = Document(
            path=tmp_path / "SPEC-TEST.md",
            frontmatter={"id": "SPEC-TEST", "status": "approved"},
            body=BODY_WITH_FR,
        )
        tasks = [
            Task(
                spec_id="SPEC-TEST",
                title="covers FRs",
                description="Implements FR-01 and FR-02",
                type=TaskType.CODE,
                complexity=Complexity.LOW,
                context_size=ContextSize.S,
                estimated_tokens=100,
                status=TaskStatus.PENDING,
                test_ids=["TST-001"],
            )
        ]
        result = FrCoverageSpecification().is_satisfied_by(spec, tasks)
        assert result.uncovered == []

    def test_disabled_fr_coverage_check_skips(self) -> None:
        from sdd_cli.compliance import FrCoverageChecker
        from sdd_cli.frontmatter import Document

        spec = Document(
            path=Path("fake.md"),
            frontmatter={"id": "SPEC-TEST", "status": "approved"},
            body=BODY_WITH_FR,
        )
        checker = FrCoverageChecker(tasks=[])
        cfg = {"compliance": {"fr_coverage_check": False}}
        issues = checker.check(spec, cfg)
        assert issues == []

    def test_fr_test_map_override_covers_fr(self, tmp_path: Path) -> None:
        from sdd_cli.frontmatter import Document

        spec = Document(
            path=tmp_path / "SPEC-TEST.md",
            frontmatter={
                "id": "SPEC-TEST",
                "status": "approved",
                "fr_test_map": {"FR-01": "TST-001", "FR-02": "TST-002"},
            },
            body=BODY_WITH_FR,
        )
        result = FrCoverageSpecification().is_satisfied_by(spec, tasks=[])
        assert result.uncovered == []
