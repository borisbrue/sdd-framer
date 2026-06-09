"""Unit-Tests für generate_holdouts.generate_holdout_scenarios (SPEC-0033)."""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from sdd_cli.generate_holdouts import generate_holdout_scenarios
from sdd_cli.llm.base import CompletionResult, UsageMetadata


def _make_provider(response: str) -> MagicMock:
    provider = MagicMock()
    provider.complete.return_value = CompletionResult(text=response)
    return provider


_SAMPLE_SCENARIOS = [
    {
        "title": "Happy Path",
        "priority": "critical",
        "type": "cli",
        "description": "sdd generate-holdouts SPEC-0001 produziert HOL-Dateien.",
        "setup": None,
        "test": {
            "action": {"command": "sdd", "args": ["generate-holdouts", "SPEC-0001"]},
            "assert": {"exit_code": 0, "stdout_contains": ["HOL-"]},
        },
        "teardown": None,
        "evaluation_hint": "- Exit-Code 0\n- HOL-Dateien vorhanden",
    },
    {
        "title": "Draft-Spec wird abgelehnt",
        "priority": "normal",
        "type": "cli",
        "description": "sdd generate-holdouts mit Draft-Spec schlägt fehl.",
        "setup": None,
        "test": {
            "action": {"command": "sdd", "args": ["generate-holdouts", "SPEC-0002"]},
            "assert": {"exit_code": 1, "stdout_contains": ["approved oder in-progress"]},
        },
        "teardown": None,
        "evaluation_hint": "- Exit-Code 1\n- Fehlermeldung enthält 'approved'",
    },
]


def test_returns_list_of_scenarios() -> None:
    provider = _make_provider(json.dumps(_SAMPLE_SCENARIOS))
    result = generate_holdout_scenarios("contract body", "CON-0001", "spec body", provider)
    assert isinstance(result, list)
    assert len(result) == 2


def test_scenario_has_required_keys() -> None:
    provider = _make_provider(json.dumps(_SAMPLE_SCENARIOS))
    result = generate_holdout_scenarios("contract body", "CON-0001", "spec body", provider)
    for scenario in result:
        assert "title" in scenario
        assert "priority" in scenario
        assert "type" in scenario
        assert "test" in scenario
        assert "evaluation_hint" in scenario


def test_retries_once_on_failure() -> None:
    provider = MagicMock()
    provider.complete.side_effect = [
        RuntimeError("timeout"),
        CompletionResult(text=json.dumps(_SAMPLE_SCENARIOS)),
    ]
    result = generate_holdout_scenarios("contract", "CON-0001", "spec", provider)
    assert len(result) == 2
    assert provider.complete.call_count == 2


def test_raises_after_two_failures() -> None:
    provider = MagicMock()
    provider.complete.side_effect = RuntimeError("API down")
    with pytest.raises(RuntimeError, match="fehlgeschlagen"):
        generate_holdout_scenarios("contract", "CON-0001", "spec", provider)


def test_raises_on_non_array_response() -> None:
    provider = _make_provider('{"error": "not an array"}')
    with pytest.raises(RuntimeError):
        generate_holdout_scenarios("contract", "CON-0001", "spec", provider)
