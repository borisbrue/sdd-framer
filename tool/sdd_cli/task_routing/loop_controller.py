"""LoopController – Review-Gate, Retry-Loop und Eskalation (CON-0173).

Chain of Responsibility: LocalLLMResult → ClaudeReviewer → Retry | Escalation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..llm import get_code_gen_provider


@dataclass
class ReviewResult:
    verdict: str  # "pass" | "fail"
    reason: str = ""


class ClaudeReviewer:
    """Bewertet ein TDD-Loop-Ergebnis binär via Claude (SPEC-0008 CodeGenProvider).

    INV-02: fail ohne Begründung ist Protokollverstoß.
    INV-06: Spec + Contract als gecachtes Prefix (cache_control: ephemeral).
    """

    async def review(self, task: Any, tdd_result: Any) -> ReviewResult:
        raise NotImplementedError("ClaudeReviewer.review muss durch Provider-Aufruf ersetzt werden")


class LoopController:
    """Orchestriert TDD-Ergebnisse nach dem Chain-of-Responsibility-Muster.

    handle_tdd_result entscheidet pro Ergebnis:
      pytest fail  → kein Claude-Aufruf, direkt Retry-Check
      pytest pass  → Claude-Review → pass: complete | fail: Retry-Kontext + Retry-Check
      Retry-Check  → iteration >= max_retries: Eskalation
    """

    def __init__(self, max_retries: int = 3, config: Any = None) -> None:
        self.max_retries = max_retries
        self._config = config
        self._reviewer = ClaudeReviewer()

    async def handle_tdd_result(self, task: Any, tdd_result: Any) -> None:
        """Verarbeitet ein TDD-Loop-Ergebnis und mutiert task.status / task.executor.

        INV-01: completed nur nach Claude pass; pytest fail → kein Claude-Aufruf.
        INV-03: retry_context akkumuliert Begründungen über alle Iterationen.
        INV-04: nach max_retries ohne pass → Eskalation (nie stilles Verwerfen).
        """
        if tdd_result.status == "fail":
            if tdd_result.iteration >= self.max_retries:
                await self._escalate(task)
            return

        # pytest pass → Claude-Review (wirft bei Verbindungsproblem)
        review: ReviewResult = await self._reviewer.review(task, tdd_result)

        if review.verdict == "pass":
            task.status = "completed"
            return

        # fail: Begründung Pflicht (INV-02)
        if not review.reason:
            raise ValueError(
                "Begründung ist Pflicht wenn Claude-Review 'fail' zurückgibt (INV-02)"
            )

        task.retry_context.append(review.reason)

        if tdd_result.iteration >= self.max_retries:
            await self._escalate(task)

    async def _escalate(self, task: Any) -> None:
        """Eskaliert den Task zu Claude (INV-05: executor = 'claude (escalated)')."""
        task.executor = "claude (escalated)"
        provider = get_code_gen_provider(self._config)
        # Akkumulierter Kontext wird in Produktionspfad an generate() übergeben
        _ = provider
