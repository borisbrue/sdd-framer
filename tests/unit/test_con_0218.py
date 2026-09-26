# AUTO-GENERATED from CON-0218 via sdd test generate — do not delete
"""TST-0247 – CON-0218: Eval-Report und Baseline.

Spec: SPEC-0055 · Contract: CON-0218
Reports entstehen aus synthetischen Laufergebnissen; kein LLM nötig.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from sdd_cli.pipeline.evals.cases import Case, RoleHome
from sdd_cli.pipeline.evals.ratchet import baseline_from
from sdd_cli.pipeline.evals.report import aggregate, build_report, case_result, persist
from sdd_cli.pipeline.evals.runner import CaseRuns, EvalSetup, RunResult
from sdd_cli.pipeline.providers import RoleBinding
from sdd_cli.pipeline.roles import load_blueprint_role
from sdd_cli.pipeline.schemas import errors

TOKENS = {"input_tokens": 100, "output_tokens": 40, "reasoning_tokens": None}


def _case(cid: str, holdout: bool = False) -> Case:
    return Case(cid, "decomposer", Path("/nicht/da") / cid, holdout,
                {"id": cid, "role": "decomposer", "origin": "manual",
                 "expect": {"checks": [{"json_schema": {}}]}})


def _run(n: int, score: float, passed: bool) -> RunResult:
    return RunResult(n, score, passed, [{"name": "fr_coverage", "status": "pass" if passed
                                         else "fail", "score": score, "details": []}],
                     {}, dict(TOKENS), 1200)


def _setup() -> EvalSetup:
    rolle = load_blueprint_role("decomposer")
    bindung = RoleBinding("decomposer", "openai-compat", "qwen", "http://h/v1", "geheim-key",
                          {}, "profile:lokal")
    return EvalSetup(rolle, bindung, "lokal", None, None, [])


def _ergebnisse() -> list[CaseRuns]:
    return [CaseRuns(_case("DEC-001"), [_run(1, 1.0, True), _run(2, 0.5, False),
                                        _run(3, 1.0, True)]),
            CaseRuns(_case("DEC-002"), [_run(1, 0.0, False), _run(2, 0.0, False),
                                        _run(3, 1.0, True)]),
            CaseRuns(_case("DEC-006", True), [_run(1, 0.8, True)] * 3),
            CaseRuns(_case("DEC-007", True), [_run(1, 0.4, False)] * 3)]


def test_tc01_valid_instance_passes():
    """Valide Instanz besteht Schema-Validierung (CON-0218)."""
    daten = build_report(_setup(), _ergebnisse(), runs=3, include_holdout=False,
                         role_file=None).to_dict()
    assert errors("role-eval-report", daten) == []
    assert errors("role-eval-report", baseline_from(daten, version="1.1.0")) == []


def test_tc02_invalid_instance_rejected():
    """Invalide Instanz wird abgelehnt (CON-0218)."""
    daten = build_report(_setup(), _ergebnisse(), runs=3, include_holdout=False,
                         role_file=None).to_dict()
    kaputt = {**daten, "prompt_hash": "abc"}
    assert errors("role-eval-report", kaputt)
    assert errors("role-eval-report", {**daten, "kind": "anders"})


def test_aggregation_je_fall_und_gesamt():
    """INV-02: Mittel, Streuung, Mehrheit, pass@1, pass^k."""
    [erster, zweiter, *_] = [case_result(r) for r in _ergebnisse()]
    assert erster["score"] == pytest.approx(2.5 / 3, abs=1e-4)
    assert erster["passed"] and erster["pass_at_1"] and not erster["pass_all"]
    assert not zweiter["passed"] and not zweiter["pass_at_1"]
    agg = aggregate([erster, zweiter])
    assert agg["cases"] == 2 and agg["pass_at_1"] == 0.5 and agg["pass_all"] == 0.0
    assert aggregate([])["mean"] is None


def test_holdout_nur_als_aggregat():
    """INV-03/04: ohne include_holdout keine IDs, total über alle Fälle."""
    daten = build_report(_setup(), _ergebnisse(), runs=3, include_holdout=False,
                         role_file=None).to_dict()
    text = json.dumps(daten)
    assert "DEC-006" not in text and "DEC-007" not in text
    assert daten["holdout"]["cases"] == 2 and daten["holdout"]["mean"] == pytest.approx(0.6)
    assert daten["total"]["cases"] == 4 and [c["id"] for c in daten["visible"]] == [
        "DEC-001", "DEC-002"]
    mit = build_report(_setup(), _ergebnisse(), runs=3, include_holdout=True,
                       role_file=None).to_dict()
    assert mit["include_holdout"] and {c["id"] for c in mit["holdout"]} == {"DEC-006", "DEC-007"}


def test_report_ohne_prompts_und_keys():
    """INV-01: keine Prompt-Texte, keine API-Keys; Prompt-Hash sha256."""
    setup = _setup()
    daten = build_report(setup, _ergebnisse(), runs=3, include_holdout=False,
                         role_file=None).to_dict()
    text = json.dumps(daten)
    assert "geheim-key" not in text and setup.role_def.prompt[:60] not in text
    assert daten["prompt_hash"].startswith("sha256:") and len(daten["prompt_hash"]) == 71
    assert daten["profile"] == {"name": "lokal", "provider": "openai-compat", "model": "qwen"}


def test_ablage_mit_und_ohne_holdout(tmp_path):
    """INV-06 und CON-0218 INV-03: Holdout-Details nie unter .sdd/role-evals/."""
    home = RoleHome("decomposer", tmp_path / ".sdd/roles/decomposer.md",
                    tmp_path / ".sdd/roles/decomposer/cases",
                    tmp_path / ".sdd/holdout/roles/decomposer")
    ohne = persist(tmp_path, home, build_report(_setup(), _ergebnisse(), runs=3,
                                                include_holdout=False, role_file=None))
    mit = persist(tmp_path, home, build_report(_setup(), _ergebnisse(), runs=3,
                                               include_holdout=True, role_file=None))
    assert ohne.parent == tmp_path / ".sdd/role-evals"
    assert mit.parent == home.holdout_reports


def test_baseline_enthaelt_faelle_und_forced():
    """INV-05: Baseline mit Scores je sichtbarem Fall; forced.reason bei --force."""
    daten = build_report(_setup(), _ergebnisse(), runs=3, include_holdout=False,
                         role_file=None).to_dict()
    basis = baseline_from(daten, version="1.1.0", reason="Rubrik ersetzt")
    assert set(basis["cases"]) == {"DEC-001", "DEC-002"} and basis["role_version"] == "1.1.0"
    assert basis["forced"] == {"reason": "Rubrik ersetzt"}
