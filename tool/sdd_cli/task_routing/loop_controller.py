"""LoopController – Review-Gate, Retry-Loop und Eskalation (CON-0173).

Chain of Responsibility: LocalLLMResult → ClaudeReviewer → Retry | Escalation.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..llm import get_code_gen_provider, get_completion_provider

_ESCALATION_PROMPT = """Die lokale Implementierung von Task {task_id} ist nach mehreren \
Versuchen gescheitert. Implementiere den Task vollständig neu.

## Aufgabe
{description}
{test_section}{reasons_section}{pytest_section}
Return ONLY a JSON object — no markdown fences, no prose:
{{"files":[{{"path":"relative/path","content":"..."}}],"explanation":"<one line>"}}
"""

_REVIEW_PROMPT = """Du prüfst das Ergebnis eines lokalen TDD-Loops für Task {task_id}.

## Aufgabe
{description}

## pytest-Ergebnis (Iteration {iteration}, Exit-Code {returncode})
```
{pytest_stdout}
```
{code_section}
Bewerte, ob die Implementierung die Aufgabe korrekt und vollständig löst — auch
wenn pytest grün ist, kann die Implementierung die Aufgabe verfehlen (z.B. den
Test statt die eigentliche Anforderung erfüllen).

Antworte NUR mit einem JSON-Objekt, keine Erklärung davor oder danach:
{{"verdict": "pass" oder "fail", "reason": "<Begründung, Pflicht bei fail>"}}
"""


@dataclass
class ReviewResult:
    verdict: str  # "pass" | "fail"
    reason: str = ""


class ClaudeReviewer:
    """Bewertet ein TDD-Loop-Ergebnis binär via Claude (SPEC-0008 CompletionProvider).

    INV-02: fail ohne Begründung ist Protokollverstoß.
    INV-06: Spec + Contract als gecachtes Prefix (cache_control: ephemeral) —
    die Provider-Schicht übernimmt das für system_prompt (nur Anthropic-Provider
    setzt tatsächlich cache_control; andere Provider ignorieren es).
    """

    def __init__(self, config: Any = None) -> None:
        self._config = config

    async def review(self, task: Any, tdd_result: Any) -> ReviewResult:
        provider = get_completion_provider(self._config, "evaluator")
        prompt = self._build_prompt(task, tdd_result)
        result = provider.complete(
            prompt, max_tokens=1024, system_prompt=self._build_system_prompt(task)
        )
        return self._parse_verdict(result.text)

    def _build_system_prompt(self, task: Any) -> str | None:
        spec_id = getattr(task, "spec_id", None)
        if not spec_id:
            return None
        from ..orchestrator import _load_contracts, _load_spec

        parts = [_load_spec(self._config, spec_id)]
        parts += [content for _cid, content in _load_contracts(self._config, spec_id)]
        return "\n\n".join(parts)

    def _build_prompt(self, task: Any, tdd_result: Any) -> str:
        code_section = ""
        test_code = getattr(tdd_result, "test_code", "")
        impl_code = getattr(tdd_result, "impl_code", "")
        if test_code or impl_code:
            blocks = []
            if test_code:
                blocks.append(f"### Test\n```python\n{test_code}\n```")
            if impl_code:
                blocks.append(f"### Implementierung\n```python\n{impl_code}\n```")
            code_section = "\n## Code\n" + "\n\n".join(blocks) + "\n"

        return _REVIEW_PROMPT.format(
            task_id=getattr(task, "id", "?"),
            description=getattr(task, "description", "") or str(task),
            iteration=getattr(tdd_result, "iteration", "?"),
            returncode=getattr(tdd_result, "pytest_returncode", "?"),
            pytest_stdout=getattr(tdd_result, "pytest_stdout", ""),
            code_section=code_section,
        )

    def _parse_verdict(self, raw: str) -> ReviewResult:
        raw = raw.strip()
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start == -1 or end == 0:
            raise ValueError(f"Claude-Review lieferte kein JSON-Verdict: {raw!r}")
        data = json.loads(raw[start:end])
        verdict = data.get("verdict")
        if verdict not in ("pass", "fail"):
            raise ValueError(f"Claude-Review lieferte kein gültiges verdict: {data!r}")
        return ReviewResult(verdict=verdict, reason=data.get("reason", ""))


class LoopController:
    """Orchestriert TDD-Ergebnisse nach dem Chain-of-Responsibility-Muster.

    handle_tdd_result entscheidet pro Ergebnis:
      pytest fail  → kein Claude-Aufruf, direkt Retry-Check
      pytest pass  → Claude-Review → pass: complete | fail: Retry-Kontext + Retry-Check
      Retry-Check  → iteration >= max_retries: Eskalation
    """

    def __init__(self, max_retries: int = 3, config: Any = None, workspace: Any = None) -> None:
        self.max_retries = max_retries
        self._config = config
        self._workspace = workspace if workspace is not None else Path(".")
        self._reviewer = ClaudeReviewer(config)

    async def handle_tdd_result(self, task: Any, tdd_result: Any) -> None:
        """Verarbeitet ein TDD-Loop-Ergebnis und mutiert task.status / task.executor.

        INV-01: completed nur nach Claude pass; pytest fail → kein Claude-Aufruf.
        INV-03: retry_context akkumuliert Begründungen über alle Iterationen.
        INV-04: nach max_retries ohne pass → Eskalation (nie stilles Verwerfen).

        pytest fail (kein Claude-Review) speist den pytest-Output ebenfalls in
        retry_context ein, damit Iteration N+1 den Fehler als Kontext bekommt
        (CON-0173 Szenario "Lokaler pytest fail → direkt Retry mit Fehlerkontext").
        """
        if tdd_result.status == "fail":
            task.retry_context.append(
                f"Iteration {tdd_result.iteration} — pytest fail:\n{tdd_result.pytest_stdout}"
            )
            if tdd_result.iteration >= self.max_retries:
                await self._escalate(task, tdd_result)
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
            await self._escalate(task, tdd_result)

    async def _escalate(self, task: Any, tdd_result: Any) -> None:
        """Eskaliert den Task zu Claude (INV-05: executor = 'claude (escalated)').

        Implementiert den Task über den bestehenden Claude-Code-Gen-Pfad
        (SPEC-0008 CodeGenProvider) neu, mit dem akkumulierten Retry-Kontext.
        Setzt bewusst NICHT task.status — die abschließende Grün-Verifikation
        liegt beim Aufrufer (task_loop.py), analog zum lokalen Erfolgspfad,
        der ebenfalls erst nach Claude-Review abschließt.
        """
        task.executor = "claude (escalated)"
        provider = get_code_gen_provider(self._config)
        prompt = self._build_escalation_prompt(task, tdd_result)
        timeout = 600
        if self._config is not None:
            try:
                timeout = self._config.llm_timeout()
            except AttributeError:
                pass
        provider.generate(prompt, self._workspace, timeout=timeout)

    def _build_escalation_prompt(self, task: Any, tdd_result: Any) -> str:
        test_code = getattr(tdd_result, "test_code", "")
        test_section = (
            f"\n## Test (muss grün werden)\n```python\n{test_code}\n```\n" if test_code else ""
        )

        reasons = getattr(task, "retry_context", None) or []
        reasons_section = ""
        if reasons:
            numbered = "\n".join(f"{i}. {r}" for i, r in enumerate(reasons, 1))
            reasons_section = f"\n## Fehlgeschlagene Versuche — Begründungen\n{numbered}\n"

        pytest_stdout = getattr(tdd_result, "pytest_stdout", "")
        pytest_section = (
            f"\n## Letzter pytest-Output\n```\n{pytest_stdout}\n```\n" if pytest_stdout else ""
        )

        return _ESCALATION_PROMPT.format(
            task_id=getattr(task, "id", "?"),
            description=getattr(task, "description", "") or str(task),
            test_section=test_section,
            reasons_section=reasons_section,
            pytest_section=pytest_section,
        )
