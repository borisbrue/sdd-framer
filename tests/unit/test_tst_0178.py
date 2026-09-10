# TST-0178 – FrCoverageSpecification — covered/uncovered Fixtures
# Spec: SPEC-0041 | Contract: CON-0152
from pathlib import Path

from sdd_cli.compliance import FrCoverageSpecification
from sdd_cli.frontmatter import Document
from sdd_cli.task_model import (
    Complexity,
    ContextSize,
    Task,
    TaskStatus,
    TaskType,
)


def _spec(body: str, frontmatter: dict | None = None) -> Document:
    fm = {"id": "SPEC-TEST", "status": "approved", **(frontmatter or {})}
    return Document(path=Path("fake.md"), frontmatter=fm, body=body)


def _task(description: str, test_ids: list[str]) -> Task:
    return Task(
        spec_id="SPEC-TEST",
        title="t",
        description=description,
        type=TaskType.CODE,
        complexity=Complexity.LOW,
        context_size=ContextSize.S,
        estimated_tokens=100,
        status=TaskStatus.PENDING,
        test_ids=test_ids,
    )


BODY_WITH_FR_SECTION = """\
## 1. Kontext

FR-99 wird hier erwähnt aber zählt nicht.

## 4. Funktionale Anforderungen

- **FR-01:** Erste Anforderung
- **FR-02:** Zweite Anforderung
- **FR-03:** Dritte Anforderung
"""

BODY_WITH_FR05 = """\
## 4. Funktionale Anforderungen

- **FR-05:** Fünfte Anforderung
"""

BODY_EMPTY_FR_SECTION = """\
## 4. Funktionale Anforderungen

Keine FR-Bezeichner hier.
"""

BODY_FR_OUTSIDE_ONLY = """\
## 1. Kontext

FR-01 wird nur hier erwähnt.

## 4. Funktionale Anforderungen

Keine FR-Bezeichner.
"""


class TestFrCoverageSpecification:

    def test_happy_path_all_covered(self) -> None:
        spec = _spec(BODY_WITH_FR_SECTION)
        tasks = [
            _task("Implements FR-01 logic", ["TST-001"]),
            _task("Implements FR-02 and FR-03", ["TST-002"]),
        ]
        result = FrCoverageSpecification().is_satisfied_by(spec, tasks)
        assert result.uncovered == []
        assert set(result.covered) == {"FR-01", "FR-02", "FR-03"}

    def test_missing_test_ids_produces_uncovered(self) -> None:
        spec = _spec(BODY_WITH_FR05)
        tasks = [_task("Implements FR-05", [])]
        result = FrCoverageSpecification().is_satisfied_by(spec, tasks)
        assert "FR-05" in result.uncovered

    def test_fr_test_map_override_covers_fr(self) -> None:
        spec = _spec(
            BODY_WITH_FR05,
            frontmatter={"fr_test_map": {"FR-05": "TST-0099"}},
        )
        result = FrCoverageSpecification().is_satisfied_by(spec, [])
        assert result.uncovered == []
        assert "FR-05" in result.covered

    def test_implemented_spec_returns_empty_result(self) -> None:
        spec = _spec(BODY_WITH_FR05, frontmatter={"status": "implemented"})
        tasks = []
        result = FrCoverageSpecification().is_satisfied_by(spec, tasks)
        assert result.covered == []
        assert result.uncovered == []

    def test_fr_outside_section_not_extracted(self) -> None:
        spec = _spec(BODY_FR_OUTSIDE_ONLY)
        result = FrCoverageSpecification().is_satisfied_by(spec, [])
        assert result.covered == []
        assert result.uncovered == []

    def test_empty_task_list_produces_uncovered(self) -> None:
        spec = _spec(BODY_WITH_FR_SECTION)
        result = FrCoverageSpecification().is_satisfied_by(spec, [])
        assert set(result.uncovered) == {"FR-01", "FR-02", "FR-03"}

    def test_missing_fr_section_returns_empty(self) -> None:
        spec = _spec("## 1. Kontext\n\nKein FR-Abschnitt vorhanden.\n")
        result = FrCoverageSpecification().is_satisfied_by(spec, [])
        assert result.covered == []
        assert result.uncovered == []
