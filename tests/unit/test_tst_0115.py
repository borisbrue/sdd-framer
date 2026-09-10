# TST-0115 – Task-Schema JSON-Validierung (Unit)
# Spec: SPEC-0026 | Contract: CON-0096

import json
from pathlib import Path

import pytest

try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False

from tool.sdd_cli.task_model import Complexity, ContextSize, Task, TaskStatus, TaskType

SCHEMA_PATH = Path(__file__).parents[2] / "contracts" / "data" / "task.schema.json"


def _schema():
    return json.loads(SCHEMA_PATH.read_text())


def _valid_task_dict(**overrides) -> dict:
    base = {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "spec_id": "SPEC-0026",
        "title": "Implementiere TaskLifecycle",
        "description": "...",
        "type": "code",
        "complexity": "medium",
        "context_size": "M",
        "estimated_tokens": 3000,
        "status": "pending",
        "retry_count": 0,
        "llm_id": None,
        "container_id": None,
        "commit_hash": None,
        "dependencies": [],
        "error_context": [],
    }
    base.update(overrides)
    return base


def _validate(instance: dict):
    if not HAS_JSONSCHEMA:
        pytest.skip("jsonschema nicht installiert")
    schema = _schema()
    jsonschema.validate(instance=instance, schema=schema)


def _validate_fails(instance: dict):
    if not HAS_JSONSCHEMA:
        pytest.skip("jsonschema nicht installiert")
    schema = _schema()
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=instance, schema=schema)


class TestTST0115:
    def test_valid_pending_task(self):
        _validate(_valid_task_dict())

    def test_invalid_empty_id(self):
        _validate_fails(_valid_task_dict(id=""))

    def test_invalid_retry_count_exceeds_max(self):
        _validate_fails(_valid_task_dict(retry_count=4))

    def test_invalid_committed_without_hash(self):
        _validate_fails(_valid_task_dict(status="committed", commit_hash=None))

    def test_valid_committed_with_hash(self):
        _validate(_valid_task_dict(status="committed", commit_hash="abc123"))

    def test_invalid_unknown_type(self):
        _validate_fails(_valid_task_dict(type="unknown"))

    def test_invalid_estimated_tokens_zero(self):
        _validate_fails(_valid_task_dict(estimated_tokens=0))

    def test_invalid_error_context_too_many(self):
        _validate_fails(_valid_task_dict(error_context=["a", "b", "c", "d"]))

    def test_valid_task_to_dict_round_trip(self):
        t = Task(
            spec_id="SPEC-0026", title="T", description="D",
            type=TaskType.CODE, complexity=Complexity.MEDIUM,
            context_size=ContextSize.M, estimated_tokens=500,
        )
        _validate(t.to_dict())

    def test_valid_committed_task_round_trip(self):
        t = Task(
            spec_id="SPEC-0026", title="T", description="D",
            type=TaskType.CODE, complexity=Complexity.MEDIUM,
            context_size=ContextSize.M, estimated_tokens=500,
            status=TaskStatus.COMMITTED, commit_hash="deadbeef",
        )
        _validate(t.to_dict())
