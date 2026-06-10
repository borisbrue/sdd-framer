"""ImplOnlyExecutor – lokales LLM implementiert Code für vorhandene Test-Datei.

Setzt voraus, dass die Test-Datei bereits existiert und rot ist (RED-Phase durch
Claude abgeschlossen). Der Executor übernimmt nur die Implementierungsphase.

Pattern: Strategy (austauschbare Implementierungsstrategie im TDD-Loop)
"""
from __future__ import annotations

import re
import shlex
import subprocess
from pathlib import Path
from typing import Any


class ImplOnlyExecutor:
    """Führt den Implementierungsschritt für einen Task via lokalem LLM aus.

    Ablauf: Test lesen → Modulpfade ableiten → Prompt bauen →
    LLM aufrufen → Code auf Disk schreiben → pytest ausführen.
    """

    def __init__(self, config: Any, project_root: Path) -> None:
        self._config = config
        self._project_root = project_root

    def execute(
        self,
        task: Any,
        test_file: Path,
        iteration: int = 1,
        error_context: str = "",
    ) -> tuple[bool, str]:
        """Implementiert einen Task via lokalem LLM.

        Args:
            task: Task-Objekt oder dict mit description + test_command.
            test_file: Pfad zur bereits vorhandenen roten Test-Datei.
            iteration: Versuchs-Nummer (≥2 = Retry mit Fehlerkontext).
            error_context: pytest-Ausgabe des vorherigen fehlgeschlagenen Versuchs.

        Returns:
            (success, pytest_output)
        """
        from ..llm import get_completion_provider

        provider = get_completion_provider(self._config, "local_llm")
        test_content = test_file.read_text()
        targets = self._extract_impl_targets(test_content)

        if not targets:
            raise ValueError(
                f"Keine 'from tool.sdd_cli.*'-Imports in {test_file} gefunden. "
                "Implementierungsdatei kann nicht abgeleitet werden."
            )

        for module, impl_file in targets:
            prompt = self._build_prompt(
                task, test_content, impl_file, iteration, error_context
            )
            result = provider.complete(prompt, max_tokens=4096)
            code = _strip_code_block(result.text)
            impl_file.parent.mkdir(parents=True, exist_ok=True)
            impl_file.write_text(code)

        desc = getattr(task, "test_command", None) or {}
        cmd = (
            task.get("test_command") if isinstance(task, dict) else getattr(task, "test_command", None)
        ) or f"pytest {test_file} -x --tb=short"
        return _run_tests(cmd, self._project_root)

    def _extract_impl_targets(self, test_content: str) -> list[tuple[str, Path]]:
        seen: set[str] = set()
        targets: list[tuple[str, Path]] = []
        for m in re.finditer(r"from (tool\.sdd_cli\.[^\s]+) import", test_content):
            module = m.group(1)
            if module not in seen:
                seen.add(module)
                targets.append((module, self._module_to_path(module)))
        return targets

    def _module_to_path(self, module: str) -> Path:
        parts = module.split(".")
        return self._project_root.joinpath(*parts).with_suffix(".py")

    def _build_prompt(
        self,
        task: Any,
        test_content: str,
        impl_file: Path,
        iteration: int,
        error_context: str,
    ) -> str:
        if isinstance(task, dict):
            desc = task.get("description", task.get("title", ""))
        else:
            desc = getattr(task, "description", str(task))

        lines = [
            "Du bist ein Python-Entwickler. Implementiere den Code damit dieser Test grün wird.",
            "",
            f"Aufgabe: {desc}",
            f"Zieldatei: {impl_file}",
            "",
            "Test-Datei (bereits vorhanden, muss nach deiner Implementierung grün sein):",
            "```python",
            test_content,
            "```",
        ]
        if iteration > 1 and error_context:
            lines += [
                "",
                f"Versuch {iteration - 1} ist fehlgeschlagen. pytest-Ausgabe:",
                "```",
                error_context,
                "```",
                "Analysiere den Fehler und korrigiere die Implementierung.",
            ]
        lines += [
            "",
            "Gib NUR validen Python-Code zurück — kein Markdown, keine Erklärungen, kein Präambel.",
        ]
        return "\n".join(lines)


def decide_routing(task_dict: dict, routing_config: Any) -> str:
    """Gibt 'local' oder 'claude' zurück für einen Task-Dict.

    Nutzt den complexity-Wert des Tasks als Proxy für complexity_score,
    da Task-JSONs aus .sdd/tasks/ keine computed score-Felder haben.
    """
    from .config import TaskRoutingConfig
    from .router import decide_executor

    if not isinstance(routing_config, TaskRoutingConfig):
        raise TypeError("routing_config muss TaskRoutingConfig sein")

    # Complexity-Text → approximate score
    _SCORE_MAP = {"low": 15, "medium": 50, "high": 80}
    complexity = task_dict.get("complexity", "medium")
    score = _SCORE_MAP.get(complexity, 50)

    class _Proxy:
        complexity_score = score

    return decide_executor(_Proxy(), routing_config)


def _strip_code_block(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        inner = lines[1:]
        if inner and inner[-1].strip() == "```":
            inner = inner[:-1]
        text = "\n".join(inner)
    return text


def _run_tests(test_command: str, cwd: Path) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            shlex.split(test_command),
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=120,
        )
        output = result.stdout + result.stderr
        return result.returncode == 0, output
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT: Test-Command überschritt 120 Sekunden."
