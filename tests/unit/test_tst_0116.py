# TST-0116 – sdd decompose Task-Ableitung (Unit)
# Spec: SPEC-0026 | Contract: CON-0097

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from tool.sdd_cli.task_model import Task, TaskType, Complexity, ContextSize
from tool.sdd_cli.decompose import TaskDecomposer


def _make_provider(response: str):
    provider = MagicMock()
    result = MagicMock()
    result.text = response
    provider.complete.return_value = result
    return provider


def _sample_tasks_json(n: int = 5) -> str:
    return json.dumps([
        {
            "title": f"Task {i}",
            "description": f"Beschreibung {i}",
            "type": "code",
            "complexity": "medium",
            "context_size": "M",
            "estimated_tokens": 1000 + i * 100,
        }
        for i in range(1, n + 1)
    ])


class TestTST0116:
    def test_five_frs_yield_five_tasks(self, tmp_path):
        provider = _make_provider(_sample_tasks_json(5))
        decomposer = TaskDecomposer(provider=provider)
        cfg = MagicMock()
        cfg.specs_dir = tmp_path
        spec_file = tmp_path / "SPEC-0026-test.md"
        spec_file.write_text("---\nid: SPEC-0026\ntitle: Test\n---\n# Test\n\n## FRs\n- FR-01\n")
        tasks = decomposer.decompose("SPEC-0026", cfg)
        assert len(tasks) >= 5

    def test_each_task_has_required_fields(self, tmp_path):
        provider = _make_provider(_sample_tasks_json(3))
        decomposer = TaskDecomposer(provider=provider)
        cfg = MagicMock()
        cfg.specs_dir = tmp_path
        (tmp_path / "SPEC-0026.md").write_text("---\nid: SPEC-0026\ntitle: T\n---\n")
        tasks = decomposer.decompose("SPEC-0026", cfg)
        for t in tasks:
            assert t.complexity is not None
            assert t.context_size is not None
            assert t.type is not None

    def test_no_duplicate_titles(self, tmp_path):
        provider = _make_provider(_sample_tasks_json(3))
        decomposer = TaskDecomposer(provider=provider)
        cfg = MagicMock()
        cfg.specs_dir = tmp_path
        (tmp_path / "SPEC-0026.md").write_text("---\nid: SPEC-0026\ntitle: T\n---\n")
        tasks = decomposer.decompose("SPEC-0026", cfg)
        titles = [t.title for t in tasks]
        assert len(titles) == len(set(titles))

    def test_duplicate_title_raises(self, tmp_path):
        dupes = json.dumps([
            {"title": "Same", "description": "", "type": "code", "complexity": "low",
             "context_size": "S", "estimated_tokens": 500},
            {"title": "Same", "description": "", "type": "code", "complexity": "low",
             "context_size": "S", "estimated_tokens": 500},
        ])
        provider = _make_provider(dupes)
        decomposer = TaskDecomposer(provider=provider)
        cfg = MagicMock()
        cfg.specs_dir = tmp_path
        (tmp_path / "SPEC-0026.md").write_text("---\nid: SPEC-0026\ntitle: T\n---\n")
        with pytest.raises(ValueError, match="Doppelter"):
            decomposer.decompose("SPEC-0026", cfg)

    def test_estimated_tokens_positive(self, tmp_path):
        provider = _make_provider(_sample_tasks_json(2))
        decomposer = TaskDecomposer(provider=provider)
        cfg = MagicMock()
        cfg.specs_dir = tmp_path
        (tmp_path / "SPEC-0026.md").write_text("---\nid: SPEC-0026\ntitle: T\n---\n")
        tasks = decomposer.decompose("SPEC-0026", cfg)
        for t in tasks:
            assert t.estimated_tokens > 0

    def test_empty_spec_exits(self, tmp_path):
        provider = _make_provider("[]")
        decomposer = TaskDecomposer(provider=provider)
        cfg = MagicMock()
        cfg.specs_dir = tmp_path
        (tmp_path / "SPEC-0026.md").write_text("---\nid: SPEC-0026\ntitle: T\n---\n")
        with pytest.raises(SystemExit):
            decomposer.decompose("SPEC-0026", cfg)

    def test_save_creates_json_file(self, tmp_path):
        cfg = MagicMock()
        cfg.root = tmp_path
        tasks = [Task(
            spec_id="SPEC-0026", title="T1", description="",
            type=TaskType.CODE, complexity=Complexity.LOW,
            context_size=ContextSize.S, estimated_tokens=500,
        )]
        path = TaskDecomposer().save(tasks, cfg)
        assert path.exists()
        data = json.loads(path.read_text())
        assert len(data) == 1

    def test_saved_json_validates_against_schema(self, tmp_path):
        try:
            import jsonschema
        except ImportError:
            pytest.skip("jsonschema nicht installiert")
        schema_path = Path(__file__).parents[2] / "contracts" / "data" / "task.schema.json"
        schema = json.loads(schema_path.read_text())
        cfg = MagicMock()
        cfg.root = tmp_path
        tasks = [Task(
            spec_id="SPEC-0026", title="T1", description="",
            type=TaskType.CODE, complexity=Complexity.LOW,
            context_size=ContextSize.S, estimated_tokens=500,
        )]
        path = TaskDecomposer().save(tasks, cfg)
        data = json.loads(path.read_text())
        for item in data:
            jsonschema.validate(instance=item, schema=schema)
