"""ReviewPipeline – Chain of Responsibility für Task-Ergebnisse (CON-0100).

Stufen: SyntaxCheckHandler → UnitTestHandler → ClaudeReviewHandler
Jede Stufe kann die Kette abbrechen und einen Retry auslösen.
"""
from __future__ import annotations

import abc
import subprocess
from pathlib import Path

from .task_model import Task
from .task_lifecycle import TaskLifecycle, MAX_RETRIES


class ReviewResult:
    def __init__(self, passed: bool, reason: str = "") -> None:
        self.passed = passed
        self.reason = reason

    def __bool__(self) -> bool:
        return self.passed


class ReviewHandler(abc.ABC):
    def __init__(self, next_handler: "ReviewHandler | None" = None) -> None:
        self._next = next_handler

    @abc.abstractmethod
    def handle(self, task: Task, work_dir: Path) -> ReviewResult:
        pass

    def _continue(self, task: Task, work_dir: Path) -> ReviewResult:
        if self._next:
            return self._next.handle(task, work_dir)
        return ReviewResult(True)


class SyntaxCheckHandler(ReviewHandler):
    def handle(self, task: Task, work_dir: Path) -> ReviewResult:
        try:
            proc = subprocess.run(
                ["python", "-m", "py_compile"] + list(work_dir.rglob("*.py")),
                capture_output=True,
                text=True,
                cwd=work_dir,
            )
            if proc.returncode != 0:
                return ReviewResult(False, f"Syntax-Fehler: {proc.stderr[:500]}")
        except Exception as exc:
            return ReviewResult(False, f"Syntax-Check fehlgeschlagen: {exc}")
        return self._continue(task, work_dir)


class UnitTestHandler(ReviewHandler):
    def __init__(self, next_handler: "ReviewHandler | None" = None, test_args: list[str] | None = None) -> None:
        super().__init__(next_handler)
        self._test_args = test_args or ["pytest", "-x", "--tb=short", "-q"]

    def handle(self, task: Task, work_dir: Path) -> ReviewResult:
        try:
            proc = subprocess.run(
                self._test_args,
                capture_output=True,
                text=True,
                cwd=work_dir,
            )
            if proc.returncode != 0:
                output = (proc.stdout + proc.stderr)[:800]
                return ReviewResult(False, f"Tests fehlgeschlagen:\n{output}")
        except Exception as exc:
            return ReviewResult(False, f"Test-Ausführung fehlgeschlagen: {exc}")
        return self._continue(task, work_dir)


class ClaudeReviewHandler(ReviewHandler):
    def __init__(
        self,
        next_handler: "ReviewHandler | None" = None,
        provider=None,
    ) -> None:
        super().__init__(next_handler)
        self._provider = provider

    def handle(self, task: Task, work_dir: Path) -> ReviewResult:
        if self._provider is None:
            return self._continue(task, work_dir)
        prompt = (
            f"Task: {task.title}\n\n"
            f"Beschreibung: {task.description}\n\n"
            "Prüfe den implementierten Code auf Korrektheit, SOLID-Prinzipien "
            "und Stil. Antworte mit PASS oder FAIL:<Grund>."
        )
        try:
            result = self._provider.complete(prompt, max_tokens=512, timeout=120)
            text = result.text.strip()
            if text.upper().startswith("FAIL"):
                reason = text[4:].lstrip(":").strip() or "Code-Review fehlgeschlagen"
                return ReviewResult(False, reason)
        except Exception as exc:
            return ReviewResult(False, f"Claude-Review Fehler: {exc}")
        return self._continue(task, work_dir)


class ReviewPipeline:
    """Führt die vollständige Review-Chain aus und aktualisiert den Task-Status."""

    def __init__(self, work_dir: Path, provider=None, test_args: list[str] | None = None) -> None:
        claude = ClaudeReviewHandler(provider=provider)
        tests = UnitTestHandler(next_handler=claude, test_args=test_args)
        syntax = SyntaxCheckHandler(next_handler=tests)
        self._chain = syntax
        self._work_dir = work_dir

    def run(self, task: Task, commit_fn: "callable[[Task], str] | None" = None) -> bool:
        lc = TaskLifecycle(task)
        lc.submit_for_review()

        result = self._chain.handle(task, self._work_dir)

        if result.passed:
            lc.mark_passed()
            if commit_fn:
                commit_hash = commit_fn(task)
                lc.commit(commit_hash)
            return True

        lc.mark_failed(result.reason)
        if task.retry_count >= MAX_RETRIES:
            lc.block()
        else:
            lc.retry()
        return False
