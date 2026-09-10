"""TST-0197 – Task-Routing-Entscheidung: complexity_score → executor (Unit)
Spec: SPEC-0045 · Contract: CON-0171
"""
from dataclasses import dataclass
from typing import Literal

import pytest

# ---------------------------------------------------------------------------
# Minimal stubs — werden durch echte Implementierung ersetzt
# ---------------------------------------------------------------------------

@dataclass
class TaskRoutingConfig:
    enabled: bool = False
    complexity_threshold: int = 30
    max_retries: int = 3
    max_concurrent: int = 3
    local_llm_configured: bool = True  # True wenn llm.local_llm in config vorhanden


@dataclass
class Task:
    id: str
    complexity_score: int
    executor: Literal["local", "claude", "claude (escalated)"] | None = None


def decide_executor(task: Task, config: TaskRoutingConfig) -> str:
    """Routing-Entscheidung per INV-01–05 aus CON-0171."""
    from tool.sdd_cli.task_routing.router import decide_executor as _impl
    return _impl(task, config)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRoutingDecision:
    def test_trivial_task_goes_local(self):
        config = TaskRoutingConfig(enabled=True, complexity_threshold=30)
        task = Task(id="TSK-001", complexity_score=20)
        assert decide_executor(task, config) == "local"

    def test_threshold_inclusive(self):
        """Score == threshold → local (INV-04: ≤ ist inklusiv)."""
        config = TaskRoutingConfig(enabled=True, complexity_threshold=30)
        task = Task(id="TSK-002", complexity_score=30)
        assert decide_executor(task, config) == "local"

    def test_above_threshold_goes_claude(self):
        config = TaskRoutingConfig(enabled=True, complexity_threshold=30)
        task = Task(id="TSK-003", complexity_score=31)
        assert decide_executor(task, config) == "claude"

    def test_routing_disabled_always_claude(self):
        """INV-03: enabled=false → immer claude, unabhängig vom Score."""
        config = TaskRoutingConfig(enabled=False, complexity_threshold=30)
        task = Task(id="TSK-004", complexity_score=5)
        assert decide_executor(task, config) == "claude"

    def test_no_local_llm_config_always_claude(self):
        """INV-03: llm.local_llm nicht konfiguriert → immer claude."""
        config = TaskRoutingConfig(enabled=True, complexity_threshold=30,
                                   local_llm_configured=False)
        task = Task(id="TSK-005", complexity_score=10)
        assert decide_executor(task, config) == "claude"

    def test_score_zero_goes_local(self):
        """Untergrenze 0 → local."""
        config = TaskRoutingConfig(enabled=True, complexity_threshold=30)
        task = Task(id="TSK-006", complexity_score=0)
        assert decide_executor(task, config) == "local"

    def test_score_100_goes_claude(self):
        """Obergrenze 100 > threshold(30) → claude."""
        config = TaskRoutingConfig(enabled=True, complexity_threshold=30)
        task = Task(id="TSK-007", complexity_score=100)
        assert decide_executor(task, config) == "claude"

    def test_invalid_score_raises(self):
        """INV-01: Score außerhalb 0–100 → ValueError."""
        config = TaskRoutingConfig(enabled=True, complexity_threshold=30)
        task = Task(id="TSK-008", complexity_score=-1)
        with pytest.raises(ValueError, match="0.*100"):
            decide_executor(task, config)

    def test_deterministic(self):
        """INV-05: Gleiche Eingabe → gleiche Ausgabe."""
        config = TaskRoutingConfig(enabled=True, complexity_threshold=30)
        task = Task(id="TSK-009", complexity_score=25)
        results = [decide_executor(task, config) for _ in range(5)]
        assert len(set(results)) == 1

    def test_executor_always_set(self):
        """INV-02: executor ist niemals None nach Routing-Entscheidung."""
        config = TaskRoutingConfig(enabled=True, complexity_threshold=50)
        for score in [0, 25, 50, 51, 100]:
            task = Task(id=f"TSK-{score}", complexity_score=score)
            result = decide_executor(task, config)
            assert result in ("local", "claude")
