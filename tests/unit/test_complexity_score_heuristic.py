"""tests for compute_complexity_score heuristic (FR-01, SPEC-0045)."""
from dataclasses import dataclass, field

import pytest


@dataclass
class DecomposeTask:
    id: str
    affected_files: list[str] = field(default_factory=list)
    estimated_lines: int = 0
    dependent_contracts: int = 0


class TestComplexityScoreHeuristic:
    def test_returns_int_in_range(self):
        from tool.sdd_cli.task_routing.heuristic import compute_complexity_score

        task = DecomposeTask(id="TSK-001")
        score = compute_complexity_score(task)
        assert isinstance(score, int)
        assert 0 <= score <= 100

    def test_empty_task_scores_low(self):
        from tool.sdd_cli.task_routing.heuristic import compute_complexity_score

        task = DecomposeTask(id="TSK-002", affected_files=[], estimated_lines=0, dependent_contracts=0)
        score = compute_complexity_score(task)
        assert score <= 30

    def test_many_files_increases_score(self):
        from tool.sdd_cli.task_routing.heuristic import compute_complexity_score

        low = DecomposeTask(id="TSK-003", affected_files=["a.py"], estimated_lines=5, dependent_contracts=0)
        high = DecomposeTask(id="TSK-004", affected_files=[f"f{i}.py" for i in range(10)], estimated_lines=5, dependent_contracts=0)
        assert compute_complexity_score(high) > compute_complexity_score(low)

    def test_many_lines_increases_score(self):
        from tool.sdd_cli.task_routing.heuristic import compute_complexity_score

        low = DecomposeTask(id="TSK-005", affected_files=["a.py"], estimated_lines=10, dependent_contracts=0)
        high = DecomposeTask(id="TSK-006", affected_files=["a.py"], estimated_lines=300, dependent_contracts=0)
        assert compute_complexity_score(high) > compute_complexity_score(low)

    def test_many_contracts_increases_score(self):
        from tool.sdd_cli.task_routing.heuristic import compute_complexity_score

        low = DecomposeTask(id="TSK-007", affected_files=["a.py"], estimated_lines=10, dependent_contracts=0)
        high = DecomposeTask(id="TSK-008", affected_files=["a.py"], estimated_lines=10, dependent_contracts=5)
        assert compute_complexity_score(high) > compute_complexity_score(low)

    def test_score_capped_at_100(self):
        from tool.sdd_cli.task_routing.heuristic import compute_complexity_score

        task = DecomposeTask(
            id="TSK-009",
            affected_files=[f"f{i}.py" for i in range(50)],
            estimated_lines=10000,
            dependent_contracts=20,
        )
        assert compute_complexity_score(task) == 100

    def test_score_minimum_is_zero(self):
        from tool.sdd_cli.task_routing.heuristic import compute_complexity_score

        task = DecomposeTask(id="TSK-010", affected_files=[], estimated_lines=0, dependent_contracts=0)
        assert compute_complexity_score(task) >= 0
