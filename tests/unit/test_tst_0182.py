# TST-0182 – Pre-Commit-Hook gibt Exit 1 bei rotem Spec-Test
# Spec: SPEC-0041 | Contract: CON-0155
import json
from pathlib import Path
from unittest.mock import patch

from sdd_cli.pre_commit_hook import PreCommitHook, find_affected_spec_ids


class TestPreCommitHook:

    def test_blocking_on_failing_test(self, tmp_path: Path) -> None:
        """Staged-Diff enthält routes/-Datei, pytest schlägt fehl → Exit 1."""
        staged = ["tool/sdd_cli/web/api/routes/dag_monitor.py"]
        tasks_dir = tmp_path / ".sdd" / "tasks"
        tasks_dir.mkdir(parents=True)
        (tasks_dir / "SPEC-0037.json").write_text(json.dumps([{
            "id": "t1", "spec_id": "SPEC-0037", "title": "t", "description": "desc",
            "type": "code", "complexity": "low", "context_size": "S",
            "estimated_tokens": 100, "status": "pending", "retry_count": 0,
            "llm_id": None, "container_id": None, "commit_hash": None,
            "dependencies": [], "error_context": [], "con_ids": [],
            "parallel_group": None, "test_ids": ["TST-001"],
            "actual_tokens": None, "run_id": None,
            "test_file": "tests/unit/test_tst_0001.py",
            "test_command": "pytest tests/unit/test_tst_0001.py --tb=short",
            "test_framework": "pytest",
        }]))

        hook = PreCommitHook(project_root=tmp_path, cfg_raw={})

        with patch.object(hook, "_get_staged_files", return_value=staged):
            with patch.object(hook, "_run_tests", return_value=1):
                result = hook.run()

        assert result == 1

    def test_no_blocking_on_passing_tests(self, tmp_path: Path) -> None:
        staged = ["tool/sdd_cli/web/api/main.py"]
        tasks_dir = tmp_path / ".sdd" / "tasks"
        tasks_dir.mkdir(parents=True)
        (tasks_dir / "SPEC-0038.json").write_text(json.dumps([{
            "id": "t2", "spec_id": "SPEC-0038", "title": "t", "description": "desc",
            "type": "code", "complexity": "low", "context_size": "S",
            "estimated_tokens": 100, "status": "pending", "retry_count": 0,
            "llm_id": None, "container_id": None, "commit_hash": None,
            "dependencies": [], "error_context": [], "con_ids": [],
            "parallel_group": None, "test_ids": ["TST-002"],
            "actual_tokens": None, "run_id": None,
            "test_file": "tests/unit/test_tst_0002.py",
            "test_command": "pytest tests/unit/test_tst_0002.py --tb=short",
            "test_framework": "pytest",
        }]))

        hook = PreCommitHook(project_root=tmp_path, cfg_raw={})

        with patch.object(hook, "_get_staged_files", return_value=staged):
            with patch.object(hook, "_run_tests", return_value=0):
                result = hook.run()

        assert result == 0

    def test_no_affected_files_exits_zero(self, tmp_path: Path) -> None:
        staged = ["README.md", "docs/something.txt"]
        hook = PreCommitHook(project_root=tmp_path, cfg_raw={})
        with patch.object(hook, "_get_staged_files", return_value=staged):
            result = hook.run()
        assert result == 0

    def test_no_spec_id_found_exits_zero(self, tmp_path: Path) -> None:
        staged = ["tool/sdd_cli/web/api/routes/unknown_route.py"]
        tasks_dir = tmp_path / ".sdd" / "tasks"
        tasks_dir.mkdir(parents=True)
        hook = PreCommitHook(project_root=tmp_path, cfg_raw={})
        with patch.object(hook, "_get_staged_files", return_value=staged):
            result = hook.run()
        assert result == 0

    def test_disabled_hook_exits_zero(self, tmp_path: Path) -> None:
        staged = ["tool/sdd_cli/web/api/routes/dag.py"]
        cfg = {"compliance": {"post_commit_hook": False}}
        hook = PreCommitHook(project_root=tmp_path, cfg_raw=cfg)
        with patch.object(hook, "_get_staged_files", return_value=staged):
            with patch.object(hook, "_run_tests", return_value=1):
                result = hook.run()
        assert result == 0


class TestFindAffectedSpecIds:

    def test_finds_spec_id_from_task_with_matching_test_file(self, tmp_path: Path) -> None:
        tasks_dir = tmp_path / ".sdd" / "tasks"
        tasks_dir.mkdir(parents=True)
        (tasks_dir / "SPEC-0042.json").write_text(json.dumps([{
            "id": "t3", "spec_id": "SPEC-0042", "title": "t", "description": "desc",
            "type": "code", "complexity": "low", "context_size": "S",
            "estimated_tokens": 100, "status": "pending", "retry_count": 0,
            "llm_id": None, "container_id": None, "commit_hash": None,
            "dependencies": [], "error_context": [], "con_ids": [],
            "parallel_group": None, "test_ids": [],
            "actual_tokens": None, "run_id": None,
            "test_file": "tests/unit/test_foo.py",
            "test_command": "pytest tests/unit/test_foo.py",
            "test_framework": "pytest",
        }]))
        result = find_affected_spec_ids(
            staged=["web/api/routes/foo.py"],
            tasks_dir=tasks_dir,
        )
        assert "SPEC-0042" in result
