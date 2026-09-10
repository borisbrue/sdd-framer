"""DistributionOrchestrator – Mediator für SPEC-0026 (CON-0101).

Koordiniert: Branch-Erstellung, Container, LLM-Verteilung, ReviewPipeline,
PR-Erstellung, Tests, Merge und Spec-Status-Update.

Mediator Pattern: Keine Komponente kennt eine andere direkt.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from .config import SddConfig
from .llm_pool import LlmPoolRegistry, LlmSelector, LlmUnavailableError
from .review_pipeline import ReviewPipeline
from .task_lifecycle import TaskLifecycle
from .task_model import Task, TaskStatus

if TYPE_CHECKING:
    pass


SPEC_BRANCH_PREFIX = "spec"


@dataclass
class DistributionReport:
    spec_id: str
    branch: str
    committed: list[str] = field(default_factory=list)
    blocked: list[str] = field(default_factory=list)
    pr_url: str | None = None
    merged: bool = False
    error: str | None = None


def _git(args: list[str], *, cwd: Path, capture: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git"] + args,
        capture_output=capture,
        text=True,
        cwd=cwd,
    )


def _gh(args: list[str], *, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["gh"] + args,
        capture_output=True,
        text=True,
        cwd=cwd,
    )


class DistributionOrchestrator:
    def __init__(
        self,
        config: SddConfig,
        registry: LlmPoolRegistry,
        work_dir: Path | None = None,
        dry_run: bool = False,
    ) -> None:
        self._config = config
        self._registry = registry
        self._selector = LlmSelector(registry)
        self._root = config.root
        self._work_dir = work_dir or self._root
        self._dry_run = dry_run

    # ── Branch ───────────────────────────────────────────────────────────────

    def ensure_branch(self, spec_id: str) -> str:
        branch = f"{SPEC_BRANCH_PREFIX}/{spec_id}"
        result = _git(["branch", "--list", branch], cwd=self._root)
        if not result.stdout.strip():
            _git(["checkout", "-b", branch], cwd=self._root)
        else:
            _git(["checkout", branch], cwd=self._root)
        return branch

    # ── Task → LLM ───────────────────────────────────────────────────────────

    def assign_llm(self, task: Task) -> str:
        entry = self._selector.select(task)
        lc = TaskLifecycle(task)
        lc.assign(entry.id)
        return entry.id

    # ── Commit ───────────────────────────────────────────────────────────────

    def commit_task(self, task: Task) -> str:
        if self._dry_run:
            return "dry-run-hash"
        _git(["add", "-A"], cwd=self._work_dir)
        msg = f"feat(SPEC-0026): {task.title}"
        _git(["commit", "-m", msg], cwd=self._work_dir)
        result = _git(["rev-parse", "HEAD"], cwd=self._work_dir)
        return result.stdout.strip()

    # ── PR ───────────────────────────────────────────────────────────────────

    def create_pr(self, spec_id: str, tasks: list[Task]) -> str | None:
        committed = [t for t in tasks if t.status == TaskStatus.COMMITTED]
        if not committed:
            return None
        if self._dry_run:
            return "https://github.com/example/pr/1"
        blocked = [t for t in tasks if t.status == TaskStatus.BLOCKED]
        if not committed:
            return None
        body_lines = ["## Tasks\n"]
        for t in committed:
            body_lines.append(f"- ✓ {t.title}")
        if blocked:
            body_lines.append("\n## ⚠ Blockierte Tasks (manueller Eingriff nötig)")
            for t in blocked:
                body_lines.append(f"- ✗ {t.title}")
        body = "\n".join(body_lines)
        result = _gh(
            ["pr", "create",
             "--title", "feat(SPEC-0026): LLM Task Distribution Engine",
             "--body", body,
             "--base", "main"],
            cwd=self._root,
        )
        if result.returncode != 0:
            return None
        return result.stdout.strip()

    def run_tests(self) -> bool:
        if self._dry_run:
            return True
        result = subprocess.run(
            ["pytest", "tests/", "-x", "--tb=short", "-q"],
            capture_output=True,
            text=True,
            cwd=self._root,
        )
        return result.returncode == 0

    def merge_pr(self, pr_url: str) -> bool:
        if self._dry_run:
            return True
        result = _gh(["pr", "merge", "--squash", "--auto", pr_url], cwd=self._root)
        return result.returncode == 0

    def update_spec_status(self, spec_id: str) -> None:
        from .frontmatter import parse_safe
        for md in self._config.specs_dir.rglob("*.md"):
            doc = parse_safe(md)
            if doc and doc.frontmatter.get("id") == spec_id:
                content = md.read_text(encoding="utf-8")
                content = content.replace("status: in-progress", "status: implemented", 1)
                md.write_text(content, encoding="utf-8")
                return

    # ── Full Run ─────────────────────────────────────────────────────────────

    def run(self, spec_id: str, tasks: list[Task]) -> DistributionReport:
        branch = self.ensure_branch(spec_id)
        report = DistributionReport(spec_id=spec_id, branch=branch)

        pipeline = ReviewPipeline(work_dir=self._work_dir)

        for task in tasks:
            try:
                self.assign_llm(task)
            except LlmUnavailableError as exc:
                task.status = TaskStatus.BLOCKED
                task.error_context.append(str(exc))
                report.blocked.append(task.title)
                continue

            lc = TaskLifecycle(task)
            lc.start_running(container_id="local")

            passed = pipeline.run(task, commit_fn=self.commit_task)
            if passed:
                report.committed.append(task.title)
            else:
                report.blocked.append(task.title)

        if not report.committed:
            report.error = "Keine Tasks erfolgreich committed – kein PR erstellt."
            return report

        # Einheitliche Finalisierung via SpecFinalizer (Container-Test + PR)
        from .finalize import SpecFinalizer
        finalizer = SpecFinalizer(self._config, dry_run=self._dry_run)
        fin_report = finalizer.run(
            spec_id,
            no_commit=True,   # Tasks wurden bereits einzeln committed
            branch=branch,
        )
        report.pr_url = fin_report.pr_url
        report.merged = fin_report.tests_passed and fin_report.pr_url is not None
        if not fin_report.tests_passed:
            report.error = fin_report.error
        elif fin_report.tests_passed:
            self.update_spec_status(spec_id)

        return report
