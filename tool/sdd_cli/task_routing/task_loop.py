"""execute_task_loop – Headless Batch-Modus für task_routing (SPEC-0045).

Verarbeitet alle Tasks einer Spec unbeaufsichtigt (kein interaktives
`/sdd-implement`): Routing → lokaler TDD-Loop mit Claude-Review-Gate,
Retry und Eskalation (CON-0173) für lokal geroutete `type=code`-Tasks,
direkter Claude-Pfad für `claude`-geroutete oder nicht-code Tasks.
Persistiert das Ergebnis zurück in `.sdd/tasks/<SPEC-ID>.json`.

Ergänzt die bereits bestehenden `sdd task-route`/`sdd task-exec`-Befehle
(genutzt von der interaktiven `/sdd-implement`-Skill) um einen zweiten,
unabhängigen Einstiegspunkt ohne laufende Claude-Code-Session.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..llm import get_code_gen_provider
from ..task_model import Task, TaskStatus, TaskType
from .config import load_task_routing_config
from .local_llm import LocalLLMExecutor
from .loop_controller import LoopController
from .task_exec import _run_tests, decide_routing


@dataclass
class TaskRunState:
    """Adapter zwischen Task (SPEC-0026) und LoopController/ClaudeReviewer (CON-0173).

    LoopController/ClaudeReviewer erwarten id/description/spec_id/con_ids/status/
    executor/retry_context (TST-0199) — das kanonische Task-Datenmodell nutzt dafür
    error_context statt retry_context und eine TaskStatus-Enum statt Strings.
    """

    id: str
    description: str
    spec_id: str | None
    con_ids: list[str] = field(default_factory=list)
    status: str = "pending"
    executor: str = "local"
    retry_context: list[str] = field(default_factory=list)


@dataclass
class TaskOutcome:
    task: Task
    status: str  # "completed" | "failed"
    executor: str
    iterations: int
    detail: str = ""


@dataclass
class TaskLoopReport:
    outcomes: list[TaskOutcome]

    @property
    def all_passed(self) -> bool:
        return all(o.status == "completed" for o in self.outcomes)


async def execute_task_loop(
    spec_id: str,
    config: Any,
    workspace: Path,
    *,
    max_concurrent: int | None = None,
) -> TaskLoopReport:
    """Verarbeitet alle Tasks von .sdd/tasks/<spec_id>.json unbeaufsichtigt.

    Tasks vom Typ 'code' durchlaufen RED(vorhanden)-GREEN via Routing;
    andere Typen (test/config/doc) haben kein TDD-Gate (analog zur
    /sdd-implement-Skill) und laufen einmalig über Claude.
    BLOCKED-Tasks (zirkuläre Dependencies, von `sdd decompose` erkannt)
    werden übersprungen und als failed berichtet statt still verworfen.
    """
    routing_cfg = load_task_routing_config(config.raw)
    concurrency = max_concurrent or routing_cfg.max_concurrent

    task_file = workspace / ".sdd" / "tasks" / f"{spec_id}.json"
    raw_tasks: list[dict] = json.loads(task_file.read_text())
    raw_by_id = {d["id"]: d for d in raw_tasks}
    tasks = [Task.from_dict(d) for d in raw_tasks]

    blocked = [t for t in tasks if t.status == TaskStatus.BLOCKED]
    code_tasks = [
        t for t in tasks if t.type == TaskType.CODE and t.status != TaskStatus.BLOCKED
    ]
    other_tasks = [
        t for t in tasks if t.type != TaskType.CODE and t.status != TaskStatus.BLOCKED
    ]

    outcomes: list[TaskOutcome] = [
        TaskOutcome(t, "failed", "none", 0, "BLOCKED: zirkuläre Abhängigkeit") for t in blocked
    ]
    done_titles: set[str] = set()
    sem = asyncio.Semaphore(concurrency)

    remaining = list(code_tasks)
    while remaining:
        ready = [t for t in remaining if all(dep in done_titles for dep in t.dependencies)]
        if not ready:
            for t in remaining:
                outcomes.append(
                    TaskOutcome(t, "failed", "none", 0, "Abhängigkeit nie erfüllt")
                )
            break

        results = await asyncio.gather(
            *[
                _run_code_task(t, raw_by_id[t.id], config, routing_cfg, workspace, sem)
                for t in ready
            ]
        )
        for t, outcome in zip(ready, results, strict=True):
            outcomes.append(outcome)
            if outcome.status == "completed":
                done_titles.add(t.title)
            remaining.remove(t)

    for t in other_tasks:
        outcomes.append(await _run_direct_claude_task(t, config, workspace))

    _persist(task_file, raw_tasks, outcomes)
    return TaskLoopReport(outcomes=outcomes)


async def _run_code_task(
    task: Task,
    task_dict: dict,
    config: Any,
    routing_cfg: Any,
    workspace: Path,
    sem: asyncio.Semaphore,
) -> TaskOutcome:
    async with sem:
        if decide_routing(task_dict, routing_cfg) == "claude":
            return await _run_direct_claude_task(task, config, workspace)
        return await _run_local_task_loop(task, routing_cfg, config, workspace)


async def _run_local_task_loop(
    task: Task, routing_cfg: Any, config: Any, workspace: Path
) -> TaskOutcome:
    state = TaskRunState(
        id=task.id, description=task.description, spec_id=task.spec_id, con_ids=task.con_ids
    )
    local_executor = LocalLLMExecutor(config)
    controller = LoopController(
        max_retries=routing_cfg.max_retries, config=config, workspace=workspace
    )

    iteration = 1
    while True:
        error_context = "\n\n".join(state.retry_context)
        tdd_result = await local_executor.execute(
            task, workspace=workspace, iteration=iteration, error_context=error_context
        )
        await controller.handle_tdd_result(state, tdd_result)

        if state.status == "completed":
            return TaskOutcome(task, "completed", "local", iteration)

        if state.executor == "claude (escalated)":
            success, output = _verify_green(task, workspace)
            return TaskOutcome(
                task, "completed" if success else "failed", "claude (escalated)",
                iteration, output,
            )

        iteration += 1


def _build_direct_claude_prompt(task: Task, config: Any) -> str:
    from ..orchestrator import _load_contracts, _load_spec

    parts = [
        "You are an expert software engineer. Implement the following task.",
        "Return ONLY a JSON object — no markdown fences, no prose:",
        '{"files":[{"path":"relative/path","content":"..."}],"explanation":"<one line>"}',
        "",
        "## Aufgabe",
        f"{task.title}: {task.description}",
        "",
    ]
    if task.spec_id:
        try:
            parts += ["## Spec", _load_spec(config, task.spec_id), ""]
        except ValueError:
            pass
        for cid, content in _load_contracts(config, task.spec_id):
            parts += [f"## Contract: {cid}", content, ""]
    return "\n".join(parts)


async def _run_direct_claude_task(task: Task, config: Any, workspace: Path) -> TaskOutcome:
    provider = get_code_gen_provider(config)
    prompt = _build_direct_claude_prompt(task, config)
    timeout = 600
    if config is not None:
        try:
            timeout = config.llm_timeout()
        except AttributeError:
            pass
    files, explanation = provider.generate(prompt, workspace, timeout=timeout)

    if task.type != TaskType.CODE:
        return TaskOutcome(task, "completed" if files else "failed", "claude", 1, explanation)

    success, output = _verify_green(task, workspace)
    return TaskOutcome(task, "completed" if success else "failed", "claude", 1, output or explanation)


def _verify_green(task: Task, workspace: Path) -> tuple[bool, str]:
    if not task.test_command:
        return True, "kein test_command definiert"
    return _run_tests(task.test_command, workspace)


def _persist(task_file: Path, raw_tasks: list[dict], outcomes: list[TaskOutcome]) -> None:
    by_id = {o.task.id: o for o in outcomes}
    for entry in raw_tasks:
        outcome = by_id.get(entry.get("id"))
        if outcome is None:
            continue
        entry["status"] = (
            TaskStatus.PASSED.value if outcome.status == "completed" else TaskStatus.FAILED.value
        )
        entry["executor"] = outcome.executor
    task_file.write_text(json.dumps(raw_tasks, indent=2, ensure_ascii=False), encoding="utf-8")
