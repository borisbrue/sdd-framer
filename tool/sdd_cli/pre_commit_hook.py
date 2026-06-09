"""Pre-Commit-Hook — Blocking Regressions-Gate (SPEC-0041 FR-08, CON-0155).

Liest git diff --cached, prüft ob main.py/routes/*.py/App.tsx betroffen sind,
ermittelt betroffene Spec-IDs und führt deren Tests aus.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path


_TRIGGER_PATTERNS = [
    re.compile(r"(^|/)main\.py$"),
    re.compile(r"/routes/[^/]+\.py$"),
    re.compile(r"(^|/)App\.tsx$"),
]


def _matches_trigger(path: str) -> bool:
    return any(p.search(path) for p in _TRIGGER_PATTERNS)


def find_affected_spec_ids(staged: list[str], tasks_dir: Path) -> set[str]:
    """Gibt alle Spec-IDs zurück deren Tasks test_files oder test_commands haben."""
    affected: set[str] = set()
    if not tasks_dir.exists():
        return affected
    for task_file in tasks_dir.glob("SPEC-*.json"):
        try:
            tasks = json.loads(task_file.read_text(encoding="utf-8"))
        except Exception:
            continue
        spec_id = task_file.stem
        for task in tasks:
            if task.get("test_file") or task.get("test_ids"):
                affected.add(spec_id)
                break
    return affected


class PreCommitHook:
    def __init__(self, project_root: Path, cfg_raw: dict) -> None:
        self._root = Path(project_root)
        self._cfg = cfg_raw

    def run(self) -> int:
        compliance = self._cfg.get("compliance") or {}
        if not compliance.get("post_commit_hook", True):
            return 0

        staged = self._get_staged_files()
        triggered = [f for f in staged if _matches_trigger(f)]
        if not triggered:
            return 0

        tasks_dir = self._root / ".sdd" / "tasks"
        spec_ids = find_affected_spec_ids(triggered, tasks_dir)
        if not spec_ids:
            return 0

        return self._run_tests(spec_ids)

    def _get_staged_files(self) -> list[str]:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            cwd=self._root,
        )
        return [line for line in result.stdout.splitlines() if line.strip()]

    def _run_tests(self, spec_ids: set[str]) -> int:
        spec_filter = " or ".join(spec_ids)
        result = subprocess.run(
            ["pytest", "tests/", "-k", spec_filter, "--tb=short"],
            cwd=self._root,
        )
        return result.returncode


def main() -> int:
    """Entry-Point für das installierte Hook-Skript."""
    import sys
    from .config import SddConfig

    cwd = Path.cwd()
    config_path = cwd / ".sdd" / "config.yaml"
    if not config_path.exists():
        return 0

    import yaml
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    cfg_raw = raw if isinstance(raw, dict) else {}

    hook = PreCommitHook(project_root=cwd, cfg_raw=cfg_raw)
    code = hook.run()
    if code != 0:
        print(
            "\n[sdd pre-commit] Tests rot — Commit abgebrochen.\n"
            "  Nutze 'git commit --no-verify' um zu überspringen (wird protokolliert).",
            file=sys.stderr,
        )
    return code
