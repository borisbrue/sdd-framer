"""Sub-Agenten-Delegation für sdd implement (SPEC-0035).

Mediator Pattern: SubAgentOrchestrator koordiniert sequenzielle Task-Delegation.
Decorator Pattern: track_tokens umhüllt jeden Sub-Agenten-Aufruf mit Token-Tracking.
"""
from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .config import SddConfig
from .task_model import Task
from .token_extractor import ClaudeSDKTokenExtractor, TokenExtractor, TokenRecord

_CLAUDE_PROVIDERS = frozenset({"anthropic", "claude-cli"})


def is_claude_provider(config: SddConfig) -> bool:
    """Returns True when the active ai_routes provider is Claude (anthropic or claude-cli)."""
    provider = (
        config.raw.get("llm", {})
        .get("ai_routes", {})
        .get("provider", "anthropic")
    )
    return provider in _CLAUDE_PROVIDERS


def filter_contracts(
    task_con_ids: list[str],
    all_contracts: dict[str, Any],
) -> dict[str, Any]:
    """Returns only the contracts whose IDs appear in task_con_ids (FR-07, CON-0122 G-01)."""
    if not task_con_ids:
        return {}
    return {k: v for k, v in all_contracts.items() if k in task_con_ids}


@dataclass
class SubAgentResult:
    task_id: str
    task_title: str
    success: bool
    tokens: TokenRecord = field(default_factory=TokenRecord)
    error: str | None = None


@dataclass
class OrchestratorReport:
    spec_id: str
    completed_tasks: list[SubAgentResult] = field(default_factory=list)
    failed_task: SubAgentResult | None = None
    halted: bool = False

    @property
    def success(self) -> bool:
        return not self.halted and self.failed_task is None


def track_tokens(
    task_id: str,
    task_label: str,
    agent_call: Callable[[], Any],
    extractor: TokenExtractor,
    config: SddConfig,
    spec_id: str,
) -> SubAgentResult:
    """Decorator: wraps a sub-agent call, extracts and persists token usage."""
    from .estimation import persist_token_usage

    start = time.monotonic()
    try:
        result = agent_call()
        duration_ms = int((time.monotonic() - start) * 1000)
        usage = getattr(result, "usage", None)
        tokens = extractor.extract(usage)
        persist_token_usage(
            config,
            component="sdd-implement-subagent",
            model=config.raw.get("llm", {}).get("ai_routes", {}).get("model", ""),
            input_tokens=tokens.input_tokens,
            output_tokens=tokens.output_tokens,
            cache_read_tokens=tokens.cache_read_tokens,
            cache_write_tokens=tokens.cache_write_tokens,
            duration_ms=duration_ms,
            spec_id=spec_id,
            task_id=task_id,
            task_label=task_label,
        )
        return SubAgentResult(task_id=task_id, task_title=task_label, success=True, tokens=tokens)
    except Exception as exc:
        duration_ms = int((time.monotonic() - start) * 1000)
        return SubAgentResult(
            task_id=task_id,
            task_title=task_label,
            success=False,
            error=str(exc),
        )


class SubAgentOrchestrator:
    """Mediator: sequences sub-agent delegation for all decompose tasks (CON-0122)."""

    def __init__(
        self,
        config: SddConfig,
        spec_id: str,
        extractor: TokenExtractor | None = None,
        max_retries: int = 1,
    ) -> None:
        self.config = config
        self.spec_id = spec_id
        self.extractor = extractor or ClaudeSDKTokenExtractor()
        self.max_retries = max_retries

    def run(
        self,
        tasks: list[Task],
        spawn_fn: Callable[[Task], Any],
    ) -> OrchestratorReport:
        """Executes tasks sequentially; on failure retries once then halts."""
        report = OrchestratorReport(spec_id=self.spec_id)

        for task in tasks:
            result = self._run_with_retry(task, spawn_fn)
            if result.success:
                report.completed_tasks.append(result)
            else:
                report.failed_task = result
                report.halted = True
                break

        return report

    def _run_with_retry(self, task: Task, spawn_fn: Callable[[Task], Any]) -> SubAgentResult:
        result = track_tokens(
            task_id=task.id,
            task_label=task.title,
            agent_call=lambda: spawn_fn(task),
            extractor=self.extractor,
            config=self.config,
            spec_id=self.spec_id,
        )
        if not result.success:
            result = track_tokens(
                task_id=task.id,
                task_label=task.title,
                agent_call=lambda: spawn_fn(task),
                extractor=self.extractor,
                config=self.config,
                spec_id=self.spec_id,
            )
        return result
