# AUTO-GENERATED from CON-0212 via sdd test generate — do not delete
"""TST-0241 – CON-0212: Profile, Rollenbelegung, Session-Auftrag und reopen.

Spec: SPEC-0061 · Contract: CON-0212
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

REPO = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((REPO / ".sdd/contracts/data/profile-rollenbelegung-session-auftrag-und-reopen"
                             ".schema.json").read_text(encoding="utf-8"))
PROFILE = {"lokal": {"provider": "openai-compat", "base_url": "http://x/v1", "model": "qwen"},
           "claude": {"provider": "claude-cli"}}


def _fehler(definition: str, instanz) -> list[str]:
    v = Draft202012Validator({"$ref": f"#/$defs/{definition}", "$defs": SCHEMA["$defs"]})
    return [e.message for e in v.iter_errors(instanz)]


def test_tc01_valid_instance_passes():
    """Beispiel aus dem Contract (CON-0212)."""
    assert _fehler("profiles", PROFILE) == []
    assert _fehler("role_binding", {"profile": "claude", "by_complexity": {
        "low": "lokal", "medium": "lokal", "high": "session"}}) == []
    assert _fehler("pipeline_config", {"task_gates": ["tests", "architecture"],
                                       "auto_steps": ["holdout", "finalize", "automerge"]}) == []
    assert _fehler("reopen_command", {"point": "S3", "command": "reopen", "reason": "r",
                                      "task_ids": ["T01"], "hint": "h"}) == []


def test_tc02_invalid_instance_rejected():
    """Beispiel aus dem Contract: profile und provider zugleich, unbekannte Stufe."""
    assert _fehler("role_binding", {"profile": "claude", "provider": "claude-cli"})
    assert _fehler("role_binding", {"by_complexity": {"extrem": "lokal"}})


def test_inv01_profil_braucht_provider():
    assert _fehler("profile", {"model": "qwen"})
    assert _fehler("profile", {"provider": "claude-cli", "farbe": "blau"})


def test_inv04_geschlossene_listen():
    assert _fehler("pipeline_config", {"task_gates": ["security"]})
    assert _fehler("pipeline_config", {"auto_steps": ["deploy"]})


def test_inv05_auftrag_mit_kind_work():
    auftrag = {"kind": "work", "request_id": "w-1", "role": "implementer", "task_id": "T01",
               "created_at": "2026-09-26T10:00:00Z", "allowed_paths": ["src/**"], "sources": {}}
    assert _fehler("work_request", auftrag) == []
    assert _fehler("work_request", {**auftrag, "role": "supervisor"})
    assert _fehler("work_request", {k: v for k, v in auftrag.items() if k != "kind"})


def test_inv06_reopen_im_command_schema():
    """Das Command-Schema der Pipeline kennt reopen nur an S3."""
    from sdd_cli.pipeline.schemas import errors

    cmd = {"point": "S3", "command": "reopen", "reason": "Holdout rot", "task_ids": ["T01"],
           "hint": "Grenzfall leerer Eingabe"}
    assert errors("supervisor-decision", cmd) == []
    assert errors("supervisor-decision", {**cmd, "point": "S2"})
    assert errors("supervisor-decision", {**cmd, "task_ids": []})


def _issues(tmp_path, llm: dict) -> list[tuple[str, str]]:
    from sdd_cli.config_validator import ConfigValidator

    return [(i.level, i.path) for i in ConfigValidator({"llm": llm}, tmp_path).validate()
            if i.path.startswith(("llm.roles", "llm.profiles"))]


def test_inv02_unbekanntes_profil_ist_fehler(tmp_path):
    issues = _issues(tmp_path, {"profiles": PROFILE, "roles": {
        "implementer": {"by_complexity": {"low": "gibtsnicht"}}}})
    assert ("error", "llm.roles.implementer.by_complexity.low") in issues


def test_inv02_by_complexity_ohne_task_ist_warnung(tmp_path):
    issues = _issues(tmp_path, {"profiles": PROFILE, "roles": {
        "decomposer": {"by_complexity": {"high": "lokal"}}}})
    assert ("warning", "llm.roles.decomposer.by_complexity") in issues


@pytest.mark.parametrize("rolle", ["decomposer", "test_author", "implementer", "reviewer"])
def test_inv03_session_fuer_arbeitsrollen(tmp_path, rolle):
    issues = _issues(tmp_path, {"roles": {rolle: {"mode": "session"}}})
    assert not [i for i in issues if i[0] == "error"]


def test_inv01_profil_und_provider_zugleich_ist_fehler(tmp_path):
    issues = _issues(tmp_path, {"profiles": PROFILE, "roles": {
        "reviewer": {"profile": "claude", "provider": "claude-cli"}}})
    assert ("error", "llm.roles.reviewer") in issues
