# TST-0117 – LLM-Pool-Registry und Selector (Unit)
# Spec: SPEC-0026 | Contract: CON-0098

import pytest

from tool.sdd_cli.llm_pool import (
    CostTier,
    LlmEntry,
    LlmPoolRegistry,
    LlmSelector,
    LlmType,
    LlmUnavailableError,
)
from tool.sdd_cli.task_model import Complexity, ContextSize, Task, TaskType


def _task(complexity=Complexity.LOW, context_size=ContextSize.S, tokens=1000) -> Task:
    return Task(
        spec_id="SPEC-0026", title="T", description="",
        type=TaskType.CODE, complexity=complexity,
        context_size=context_size, estimated_tokens=tokens,
    )


def _entry(id, type=LlmType.REMOTE, tier=CostTier.CHEAP, max_tokens=100000) -> LlmEntry:
    return LlmEntry(id=id, type=type, model=id, cost_tier=tier, max_context_tokens=max_tokens)


class TestTST0117:
    def test_low_s_prefers_local_cheap(self):
        registry = LlmPoolRegistry([
            _entry("ollama", type=LlmType.LOCAL, tier=CostTier.CHEAP),
            _entry("haiku", type=LlmType.REMOTE, tier=CostTier.CHEAP),
        ])
        selected = LlmSelector(registry).select(_task(Complexity.LOW, ContextSize.S))
        assert selected.id == "ollama"

    def test_high_l_selects_powerful(self):
        registry = LlmPoolRegistry([
            _entry("ollama", tier=CostTier.CHEAP),
            _entry("opus", tier=CostTier.POWERFUL),
        ])
        selected = LlmSelector(registry).select(_task(Complexity.HIGH, ContextSize.L))
        assert selected.id == "opus"

    def test_fallback_when_preferred_tier_missing(self):
        registry = LlmPoolRegistry([_entry("haiku", tier=CostTier.CHEAP)])
        selected = LlmSelector(registry).select(_task(Complexity.HIGH, ContextSize.L))
        assert selected.id == "haiku"

    def test_context_limit_respected(self):
        registry = LlmPoolRegistry([
            _entry("tiny", tier=CostTier.CHEAP, max_tokens=500),
            _entry("big", tier=CostTier.CHEAP, max_tokens=10000),
        ])
        selected = LlmSelector(registry).select(_task(tokens=1000))
        assert selected.id == "big"

    def test_empty_registry_raises(self):
        registry = LlmPoolRegistry()
        with pytest.raises(LlmUnavailableError):
            LlmSelector(registry).select(_task())

    def test_duplicate_id_raises(self):
        registry = LlmPoolRegistry()
        registry.register(_entry("dup"))
        with pytest.raises(ValueError, match="Doppelte"):
            registry.register(_entry("dup"))

    def test_local_preferred_over_remote_same_tier(self):
        registry = LlmPoolRegistry([
            _entry("remote-haiku", type=LlmType.REMOTE, tier=CostTier.CHEAP),
            _entry("local-ollama", type=LlmType.LOCAL, tier=CostTier.CHEAP),
        ])
        selected = LlmSelector(registry).select(_task())
        assert selected.id == "local-ollama"

    def test_all_context_limits_too_small_raises(self):
        registry = LlmPoolRegistry([
            _entry("tiny", tier=CostTier.POWERFUL, max_tokens=100),
        ])
        with pytest.raises(LlmUnavailableError):
            LlmSelector(registry).select(_task(tokens=50000))
