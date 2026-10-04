"""TST-0229 – CON-0200: Rollenausgaben (decomposer, test_author, implementer, reviewer).

Spec: SPEC-0053 · Contract: CON-0200
"""
from __future__ import annotations

from tests.support.quality_project import def_errors

TASK = {"title": "Modell", "description": "Modell anlegen", "type": "code", "complexity": "low",
        "fr_ids": ["FR-01"], "dependencies": [], "test_file": "tests/unit/test_m.py",
        "test_command": "pytest tests/unit/test_m.py", "allowed_paths": ["tool/m/**"]}


def test_tc01_valid_instance_passes():
    """Valide Ausgaben aller vier Rollen (CON-0200)."""
    assert def_errors("role_outputs", "decomposer", {"tasks": [TASK]}) == []
    assert def_errors("role_outputs", "test_author", {"test_file": "tests/t.py",
                                                      "content": "x", "fr_ids": ["FR-01"]}) == []
    assert def_errors("role_outputs", "implementer", {"files": [{"path": "a.py", "content": ""}],
                                                      "explanation": "e"}) == []
    assert def_errors("role_outputs", "reviewer", {"verdict": "pass", "findings": []}) == []


def test_tc02_invalid_instance_rejected():
    """Beispiel aus dem Contract: code-Task ohne FR, test_file und test_command."""
    task = {k: v for k, v in TASK.items() if k not in ("test_file", "test_command")}
    assert def_errors("role_outputs", "decomposer", {"tasks": [{**task, "fr_ids": []}]})


def test_inv01_doc_task_ohne_fr_erlaubt():
    task = {k: v for k, v in TASK.items() if k not in ("test_file", "test_command")}
    assert def_errors("role_outputs", "decomposer",
                      {"tasks": [{**task, "type": "doc", "fr_ids": []}]}) == []


def test_inv01_test_task_braucht_fr():
    assert def_errors("role_outputs", "decomposer",
                      {"tasks": [{**TASK, "type": "test", "fr_ids": []}]})


def test_inv01_leere_zerlegung():
    assert def_errors("role_outputs", "decomposer", {"tasks": []})


def test_inv02_allowed_paths_pflicht():
    task = {k: v for k, v in TASK.items() if k != "allowed_paths"}
    assert def_errors("role_outputs", "decomposer", {"tasks": [task]})


def test_inv03_test_author_braucht_fr():
    assert def_errors("role_outputs", "test_author",
                      {"test_file": "tests/t.py", "content": "x", "fr_ids": []})


def test_inv04_implementer_ohne_pfadflucht():
    assert def_errors("role_outputs", "implementer",
                      {"files": [{"path": "../x.py", "content": ""}], "explanation": "e"})
    # SPEC-0066 FR-02 (CON-0200 0.4.0): `files: []` heißt „keine Änderung nötig“.
    assert not def_errors("role_outputs", "implementer", {"files": [], "explanation": "e"})


def test_inv05_fail_braucht_befund():
    assert def_errors("role_outputs", "reviewer", {"verdict": "fail", "findings": []})
    assert def_errors("role_outputs", "reviewer", {"verdict": "fail", "findings": [
        {"category": "style", "file": "a.py", "reason": "r"}]})
