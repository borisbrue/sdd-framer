"""LocalLLMExecutor – Async TDD-Loop via lokales LLM (CON-0172)."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..llm import get_completion_provider


@dataclass
class TDDLoopResult:
    status: str  # "pass" | "fail"
    pytest_stdout: str
    pytest_returncode: int
    iteration: int
    error: str | None = None


class LocalLLMExecutor:
    """Führt den TDD-Loop für einen einzelnen Task aus (Template Method Pattern).

    Ablauf (fest): test schreiben → test_file auf Disk → impl schreiben →
    impl_file auf Disk → pytest ausführen → TDDLoopResult zurückgeben.
    """

    def __init__(self, config: Any = None) -> None:
        self._config = config

    async def execute(
        self, task: Any, workspace: Path, iteration: int
    ) -> TDDLoopResult:
        """Führt einen TDD-Zyklus aus.

        INV-01: Testdatei wird VOR Implementierungsdatei auf Disk geschrieben.
        INV-02: Testdatei liegt unter tests/unit/test_<task_id>.py.
        INV-03: pytest via asyncio.create_subprocess_exec (kein blocking call).
        INV-04: Ergebnis enthält status, pytest_stdout, pytest_returncode, iteration.
        INV-06: LLM-Call via get_completion_provider, kein direkter HTTP-Call.
        """
        try:
            provider = get_completion_provider(self._config, "local_llm")
        except TimeoutError as exc:
            return TDDLoopResult(
                status="fail",
                pytest_stdout="",
                pytest_returncode=-1,
                iteration=iteration,
                error=f"LLM timeout: {exc}",
            )

        try:
            test_code = provider.complete(
                f"Write a pytest test for task: {task.description}"
            ).text
        except TimeoutError as exc:
            return TDDLoopResult(
                status="fail",
                pytest_stdout="",
                pytest_returncode=-1,
                iteration=iteration,
                error=f"LLM timeout: {exc}",
            )

        # INV-01: Test ZUERST schreiben
        test_file = workspace / "tests" / "unit" / f"test_{task.id}.py"
        await self._write_file(test_file, test_code)

        impl_code = provider.complete(
            f"Implement the following: {task.description}"
        ).text
        impl_file = workspace / f"{task.id}.py"
        await self._write_file(impl_file, impl_code)

        returncode, stdout = await self._run_pytest(test_file, workspace)
        return TDDLoopResult(
            status="pass" if returncode == 0 else "fail",
            pytest_stdout=stdout,
            pytest_returncode=returncode,
            iteration=iteration,
        )

    async def _write_file(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    async def _run_pytest(self, test_file: Path, workspace: Path) -> tuple[int, str]:
        proc = await asyncio.create_subprocess_exec(
            "pytest", str(test_file), "--tb=short",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(workspace),
        )
        stdout_bytes, _ = await proc.communicate()
        return proc.returncode, stdout_bytes.decode("utf-8", errors="replace")


async def run_concurrent(
    tasks: list[Any],
    max_concurrent: int,
    workspace: Path,
) -> list[TDDLoopResult]:
    """Führt Tasks mit Semaphore-Begrenzung parallel aus (INV-05).

    Maximal max_concurrent Tasks laufen gleichzeitig.
    """
    sem = asyncio.Semaphore(max_concurrent)
    executor = LocalLLMExecutor()

    async def _one(task: Any) -> TDDLoopResult:
        async with sem:
            return await executor.execute(task, workspace=workspace, iteration=1)

    return list(await asyncio.gather(*[_one(t) for t in tasks]))
