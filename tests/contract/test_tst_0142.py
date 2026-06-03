# TST-0142 | SPEC-0035 | CON-0121
# Token-History-Task-Schema: task_id-Felder werden korrekt validiert

import json
from pathlib import Path

import jsonschema
import pytest

_SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / ".sdd/contracts/data/token-history-task-schema.schema.json"
)


def _schema():
    return json.loads(_SCHEMA_PATH.read_text())


def _base_row(**extra):
    row = {
        "id": 1,
        "timestamp": "2026-06-03T00:00:00Z",
        "component": "test",
        "model": "claude-sonnet-4-6",
        "input_tokens": 100,
        "output_tokens": 50,
    }
    row.update(extra)
    return row


class TestTST0142:
    def test_tc01_valid_row_without_task_fields_passes(self) -> None:
        jsonschema.validate(_base_row(), _schema())

    def test_tc02_valid_row_with_task_id_and_label_passes(self) -> None:
        jsonschema.validate(_base_row(task_id="t1", task_label="Implement schema"), _schema())

    def test_tc03_task_id_without_task_label_rejected(self) -> None:
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(_base_row(task_id="t1"), _schema())

    def test_tc04_null_task_id_with_task_label_passes(self) -> None:
        jsonschema.validate(_base_row(task_id=None, task_label="some label"), _schema())

    def test_tc05_missing_required_field_rejected(self) -> None:
        row = _base_row()
        del row["input_tokens"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(row, _schema())

    def test_tc06_task_id_wrong_type_rejected(self) -> None:
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(_base_row(task_id=42), _schema())
