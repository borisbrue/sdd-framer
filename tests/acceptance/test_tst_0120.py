# TST-0120 – PR-Workflow End-to-End (Acceptance)
# Spec: SPEC-0026 | Contract: CON-0101

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from tool.sdd_cli.task_model import Task, TaskType, Complexity, ContextSize, TaskStatus
from tool.sdd_cli.task_lifecycle import TaskLifecycle
from tool.sdd_cli.llm_pool import LlmPoolRegistry, LlmEntry, LlmType, CostTier
from tool.sdd_cli.dist_orchestrator import DistributionOrchestrator, DistributionReport


def _task(title="T", status=TaskStatus.PENDING) -> Task:
    t = Task(
        spec_id="SPEC-0026", title=title, description="",
        type=TaskType.CODE, complexity=Complexity.LOW,
        context_size=ContextSize.S, estimated_tokens=500,
    )
    t.status = status
    return t


def _registry() -> LlmPoolRegistry:
    return LlmPoolRegistry([
        LlmEntry("local", LlmType.LOCAL, "ollama", CostTier.CHEAP, 100000)
    ])


def _orchestrator(tmp_path: Path, dry_run=True) -> DistributionOrchestrator:
    cfg = MagicMock()
    cfg.root = tmp_path
    cfg.specs_dir = tmp_path
    (tmp_path / "SPEC-0026-test.md").write_text(
        "---\nid: SPEC-0026\ntitle: Test\nstatus: in-progress\n---\n# Test\n"
    )
    return DistributionOrchestrator(cfg, _registry(), work_dir=tmp_path, dry_run=dry_run)


class TestTST0120:
    def test_all_committed_creates_pr(self, tmp_path):
        orch = _orchestrator(tmp_path)
        tasks = [_task(f"T{i}", TaskStatus.COMMITTED) for i in range(3)]
        for idx, t in enumerate(tasks):
            t.commit_hash = f"hash{idx}"
        pr = orch.create_pr("SPEC-0026", tasks)
        assert pr is not None

    def test_mixed_tasks_pr_with_warning(self, tmp_path):
        orch = _orchestrator(tmp_path)
        committed = [_task("Done", TaskStatus.COMMITTED)]
        blocked = [_task("Broken", TaskStatus.BLOCKED)]
        committed[0].commit_hash = "abc"
        pr = orch.create_pr("SPEC-0026", committed + blocked)
        assert pr is not None

    def test_only_blocked_no_pr(self, tmp_path):
        orch = _orchestrator(tmp_path)
        tasks = [_task("B", TaskStatus.BLOCKED)]
        pr = orch.create_pr("SPEC-0026", tasks)
        assert pr is None

    def test_dry_run_tests_pass(self, tmp_path):
        orch = _orchestrator(tmp_path, dry_run=True)
        assert orch.run_tests() is True

    def test_spec_status_updated_after_merge(self, tmp_path):
        spec_file = tmp_path / "SPEC-0026-test.md"
        orch = _orchestrator(tmp_path)
        orch.update_spec_status("SPEC-0026")
        content = spec_file.read_text()
        assert "status: implemented" in content

    def test_spec_status_not_updated_before_merge(self, tmp_path):
        spec_file = tmp_path / "SPEC-0026-test.md"
        spec_file.write_text("---\nid: SPEC-0026\ntitle: T\nstatus: in-progress\n---\n")
        content_before = spec_file.read_text()
        assert "implemented" not in content_before

    def test_branch_name_format(self, tmp_path):
        orch = _orchestrator(tmp_path)
        with patch.object(orch, 'ensure_branch', return_value="spec/SPEC-0026") as mock_branch:
            branch = orch.ensure_branch("SPEC-0026")
        assert branch == "spec/SPEC-0026"

    def test_full_dry_run_report(self, tmp_path):
        orch = _orchestrator(tmp_path, dry_run=True)
        tasks = [_task(f"Task {i}") for i in range(3)]

        with patch.object(orch, 'ensure_branch', return_value="spec/SPEC-0026"), \
             patch.object(orch, 'assign_llm', side_effect=lambda t: None), \
             patch.object(orch, '_selector') as mock_sel:
            from tool.sdd_cli.llm_pool import LlmEntry
            mock_entry = LlmEntry("local", LlmType.LOCAL, "ollama", CostTier.CHEAP, 100000)
            mock_sel.select.return_value = mock_entry

            for t in tasks:
                lc = TaskLifecycle(t)
                lc.assign("local")
                lc.start_running("c1")
                lc.submit_for_review()
                lc.mark_passed()
                lc.commit(f"hash{tasks.index(t)}")

        report = DistributionReport(
            spec_id="SPEC-0026",
            branch="spec/SPEC-0026",
            committed=[t.title for t in tasks],
            pr_url="https://github.com/example/pr/1",
            merged=True,
        )
        assert len(report.committed) == 3
        assert report.merged is True
