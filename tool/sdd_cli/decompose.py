"""TaskDecomposer – zerlegt ein Spec via LLM in klassifizierte Tasks (CON-0097).

Nutzt ClaudeCliCompletionProvider (kein API-Key nötig) als Default.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from .config import SddConfig
from .frontmatter import parse_safe
from .task_model import Complexity, ContextSize, Task, TaskStatus, TaskType

_SYSTEM_PROMPT = """\
Du bist ein Software-Architekt. Deine Aufgabe: Zerlege ein Spec in atomare, \
implementierbare Tasks nach dem TDD-Prinzip (Test-first).

Regeln:
- Jeder Task adressiert genau eine funktionale Verantwortlichkeit (atomic).
- Gib NUR valides JSON zurück – kein Markdown, kein Text darum herum.
- Jeder Task hat folgende Felder:
    title, description, type (code|test|config|doc),
    complexity (low|medium|high), context_size (S|M|L), estimated_tokens (int > 0),
    dependencies (Liste von Titeln anderer Tasks die vorher abgeschlossen sein müssen),
    parallel_group (String-Label für Tasks die parallel laufen können, null wenn sequenziell),
    test_file (Pfad zur Test-Datei die DIESEN Task verifiziert, muss noch nicht existieren),
    test_command (Shell-Befehl um NUR diese Test-Datei auszuführen),
    test_framework (pytest | deno | npm | jest | vitest).
- test_file und test_command sind PFLICHTFELDER für jeden Task vom type "code".
  Bei type "test", "config", "doc": test_file=null, test_command=null, test_framework=null.
- test_file-Konventionen:
    Python-Code → "tests/unit/test_<snake_case_title>.py" (pytest)
    TypeScript/React-Logik → "<pkg>/src/__tests__/<slug>.test.ts" (deno oder vitest)
    TypeScript-Komponente → "<pkg>/src/__tests__/<slug>.test.tsx" (vitest)
    API/Integration → "tests/integration/test_<slug>.py" (pytest)
- test_command muss NUR die eine test_file ausführen, nicht das gesamte Testsuite.
  Beispiele:
    pytest: "pytest tests/unit/test_hub_logic.py -x --tb=short"
    deno:   "deno test --no-check --unstable-sloppy-imports --allow-read --allow-env web/pwa/src/__tests__/hub_logic.test.ts"
- Die test_file muss so gewählt sein, dass sie VOR der Implementierung rot ist
  (weil sie Code importiert der noch nicht existiert) und NACH der Implementierung grün.
- Extrahiere reine Logik aus Komponenten/Views in separate Module wenn möglich,
  damit sie direkt testbar sind (ohne DOM, ohne Mock-Framework).
- Tasks die sich NICHT gegenseitig beeinflussen: parallel_group setzen.
- Tasks mit dependencies: parallel_group=null.
- Mindestens ein Task pro FR im Spec.
- Keine doppelten Titel.
- Keine zirkulären dependencies.

Ausgabeformat (JSON-Array):
[
  {
    "title": "...",
    "description": "...",
    "type": "code",
    "complexity": "medium",
    "context_size": "M",
    "estimated_tokens": 3000,
    "dependencies": [],
    "parallel_group": "group-1",
    "test_file": "tests/unit/test_my_feature.py",
    "test_command": "pytest tests/unit/test_my_feature.py -x --tb=short",
    "test_framework": "pytest"
  }
]
"""


def detect_circular_dependencies(tasks: list[Task]) -> set[str]:
    """DFS-basierte Zirkel-Erkennung. Gibt IDs der betroffenen Tasks zurück."""
    title_to_id = {t.title: t.id for t in tasks}
    adj: dict[str, set[str]] = {t.id: set() for t in tasks}
    for t in tasks:
        for dep_title in t.dependencies:
            dep_id = title_to_id.get(dep_title)
            if dep_id:
                adj[t.id].add(dep_id)

    visited: set[str] = set()
    in_stack: set[str] = set()
    circular: set[str] = set()

    def dfs(node: str) -> bool:
        visited.add(node)
        in_stack.add(node)
        for neighbor in adj.get(node, set()):
            if neighbor not in visited:
                if dfs(neighbor):
                    circular.add(node)
                    return True
            elif neighbor in in_stack:
                circular.add(node)
                circular.add(neighbor)
                return True
        in_stack.discard(node)
        return False

    for task_id in list(adj.keys()):
        if task_id not in visited:
            dfs(task_id)

    return circular


class TaskDecomposer:
    def __init__(self, provider=None) -> None:
        if provider is None:
            from .llm.providers.claude_cli import ClaudeCliCompletionProvider
            provider = ClaudeCliCompletionProvider()
        self._provider = provider

    def decompose(self, spec_id: str, config: SddConfig) -> list[Task]:
        spec_text = self._load_spec(spec_id, config)
        prompt = f"Spec:\n\n{spec_text}\n\nZerlege dieses Spec in atomare Tasks."
        result = self._provider.complete(
            prompt,
            system_prompt=_SYSTEM_PROMPT,
            max_tokens=4096,
            timeout=180,
        )
        raw = result.text.strip()
        # LLM wraps JSON in code block sometimes — extract array directly
        m = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", raw, re.DOTALL)
        if m:
            raw = m.group(1)
        else:
            m = re.search(r"\[.*\]", raw, re.DOTALL)
            if m:
                raw = m.group(0)
        try:
            items: list[dict] = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"LLM lieferte kein valides JSON: {exc}\n{raw[:200]}") from exc

        if not items:
            print("Keine Tasks ableitbar", file=sys.stderr)
            sys.exit(1)

        tasks: list[Task] = []
        seen_titles: set[str] = set()
        for item in items:
            title = item.get("title", "").strip()
            if not title:
                continue
            if title in seen_titles:
                raise ValueError(f"Doppelter Task-Titel: {title!r}")
            seen_titles.add(title)
            estimated = int(item.get("estimated_tokens", 0))
            if estimated <= 0:
                estimated = 1000
            tasks.append(Task(
                spec_id=spec_id,
                title=title,
                description=item.get("description", ""),
                type=TaskType(item.get("type", "code")),
                complexity=Complexity(item.get("complexity", "medium")),
                context_size=ContextSize(item.get("context_size", "M")),
                estimated_tokens=estimated,
                dependencies=item.get("dependencies", []),
                parallel_group=item.get("parallel_group"),
                test_file=item.get("test_file") or None,
                test_command=item.get("test_command") or None,
                test_framework=item.get("test_framework") or None,
            ))

        if not tasks:
            print("Keine Tasks ableitbar", file=sys.stderr)
            sys.exit(1)

        circular = detect_circular_dependencies(tasks)
        if circular:
            for task_id in circular:
                task = next((t for t in tasks if t.id == task_id), None)
                if task:
                    task.status = TaskStatus.BLOCKED
                    task.error_context.append("circular dependency detected")

        return tasks

    def _load_spec(self, spec_id: str, config: SddConfig) -> str:
        for md in config.specs_dir.rglob("*.md"):
            doc = parse_safe(md)
            if doc and doc.frontmatter.get("id") == spec_id:
                return md.read_text(encoding="utf-8")
        raise ValueError(f"Spec nicht gefunden: {spec_id}")

    def save(self, tasks: list[Task], config: SddConfig) -> Path:
        tasks_dir = config.root / ".sdd" / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)
        if not tasks:
            raise ValueError("Leere Task-Liste kann nicht gespeichert werden.")
        spec_id = tasks[0].spec_id
        out = tasks_dir / f"{spec_id}.json"
        out.write_text(
            json.dumps([t.to_dict() for t in tasks], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return out

    def load(self, spec_id: str, config: SddConfig) -> list[Task]:
        path = config.root / ".sdd" / "tasks" / f"{spec_id}.json"
        if not path.exists():
            return []
        items = json.loads(path.read_text(encoding="utf-8"))
        return [Task.from_dict(d) for d in items]
