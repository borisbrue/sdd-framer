"""TST-0232 – CON-0203: Task-Schema-Erweiterung fr_ids und allowed_paths.

Spec: SPEC-0053 · Contract: CON-0203
"""
from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from tests.support.pipeline_project import requires_pipeline_cli
from tests.support.quality_project import schema_errors

BASIS = Path(__file__).resolve().parents[2] / "contracts/data/task.schema.json"


def test_tc01_valid_instance_passes():
    """Valide Erweiterung (CON-0203)."""
    assert schema_errors("task_extension", {"type": "code", "fr_ids": ["FR-05"],
                                            "allowed_paths": ["tool/sdd_cli/decompose.py"]}) == []


def test_tc02_invalid_instance_rejected():
    """Beispiel aus dem Contract: code-Task mit leerer FR-Liste."""
    assert schema_errors("task_extension", {"type": "code", "fr_ids": []})


def test_inv01_optional_und_doc_ohne_fr():
    assert schema_errors("task_extension", {"type": "code"}) == []
    assert schema_errors("task_extension", {"type": "doc", "fr_ids": []}) == []


def test_inv01_fr_format():
    assert schema_errors("task_extension", {"type": "code", "fr_ids": ["FR01"]})


@requires_pipeline_cli
def test_inv03_zusammen_mit_basis_schema():
    """Eine vollständige Task-Instanz nach CON-0096 mit den neuen Feldern erfüllt beide Schemas.

    Das Basis-Schema verbietet heute zusätzliche Felder; die Umsetzung von SPEC-0053 erweitert es.
    """
    basis = json.loads(BASIS.read_text(encoding="utf-8"))
    task = {"id": "t-1", "spec_id": "SPEC-0900", "title": "Modell", "description": "d",
            "type": "code", "complexity": "low", "context_size": "S", "estimated_tokens": 100,
            "status": "pending", "retry_count": 0, "llm_id": None, "container_id": None,
            "commit_hash": None, "dependencies": [], "error_context": [],
            "fr_ids": ["FR-01"], "allowed_paths": ["tool/m/**"]}
    assert [e.message for e in Draft202012Validator(basis).iter_errors(task)] == []
    assert schema_errors("task_extension", task) == []
