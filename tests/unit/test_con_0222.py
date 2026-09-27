# AUTO-GENERATED from CON-0222 via sdd test generate — do not delete
"""TST-0251 – CON-0222: Bench-Record.

Spec: SPEC-0056 · Contract: CON-0222
"""
from __future__ import annotations

import pytest

from sdd_cli.bench.meter import BudgetExceeded, Meter
from sdd_cli.llm.base import CompletionResult, UsageMetadata
from sdd_cli.pipeline.providers import RoleBinding
from sdd_cli.pipeline.schemas import errors

BASIS = {"kind": "bench-record", "run_id": "regen-a-m-r1", "suite": "regen",
         "suite_kind": "regen", "q_kind": "quality", "assignment": "a",
         "roles": {"implementer": {"profile": "lokal", "provider": "openai-compat",
                                   "model": "q", "params": {}, "server_model": "q-4bit",
                                   "endpoint": "http://h/v1", "role_version": "1.0.0"}},
         "repetition": 1, "outcome": "completed", "Q": 0.8,
         "tokens": {"implementer": {"input": 10, "output": 5, "reasoning": 0, "calls": 1,
                                    "estimated": False}},
         "T_in": 10, "T_out": 5, "T_reason": 0, "T_claude": 0, "duration_ms": 12,
         "sdd_version": "0", "created_at": "2026-09-27T10:00:00Z", "artifacts": "runs/x",
         "task": "pkg/m.py", "Q_req": 1.0, "Q_arch": None, "Q_code": 0.6, "frs_total": 3,
         "frs_met": 3, "attempts": 1, "failed_attempts": 0, "git_sha": "96e622b"}
EVAL = {**{k: v for k, v in BASIS.items() if k not in (
    "task", "Q_req", "Q_arch", "Q_code", "frs_total", "frs_met", "attempts", "failed_attempts",
    "git_sha")}, "q_kind": "eval", "role": "implementer", "profile": "lokal", "pass_at_1": 0.5,
    "pass_all": 0.25, "holdout_Q": 0.7}


def test_tc01_valid_instance_passes():
    """Valide Instanz besteht Schema-Validierung (CON-0222)."""
    assert errors("bench-record", BASIS) == []
    assert errors("bench-record", EVAL) == []


@pytest.mark.parametrize("record", [
    {**BASIS, "outcome": "abgebrochen"},
    {k: v for k, v in BASIS.items() if k != "Q_req"},
    {k: v for k, v in EVAL.items() if k != "pass_all"},
    {**BASIS, "q_kind": "gemischt"},
])
def test_tc02_invalid_instance_rejected(record):
    """Invalide Instanz wird abgelehnt (CON-0222)."""
    assert errors("bench-record", record)


def _bindung(provider="openai-compat") -> RoleBinding:
    return RoleBinding("implementer", provider, "q", "http://h/v1", "geheim", {}, "profile:x")


class _Provider:
    def __init__(self, usage):
        self.usage = usage

    def complete(self, prompt, **kw):
        return CompletionResult(text="x" * 400, usage=self.usage)


def test_geschaetzt_ohne_usage():
    """INV-03: ohne Usage geschätzt (Zeichen/4), estimated; Reasoning 0."""
    meter = Meter()
    p = meter.wrap(_Provider(UsageMetadata.unavailable()), _bindung(), "implementer")
    p.complete("y" * 800, system_prompt="z" * 200)
    t = meter.tokens["implementer"]
    assert (t.input, t.output, t.reasoning, t.estimated) == (250, 100, 0, True)


def test_gemeldet_und_claude_anteil():
    meter = Meter()
    usage = UsageMetadata(input_tokens=30, output_tokens=10, reasoning_tokens=4,
                          model="c", source="reported", server_model="claude-x")
    meter.wrap(_Provider(usage), _bindung("claude-cli"), "supervisor").complete("p")
    assert meter.claude_tokens == 40 and meter.server_models["supervisor"] == "claude-x"
    assert meter.tokens["supervisor"].reasoning == 4 and not meter.tokens["supervisor"].estimated


def test_budget_verweigert_weitere_aufrufe():
    """INV-05 (CON-0223): nach überschrittenem Budget keine Aufrufe mehr."""
    meter = Meter(max_tokens=100)
    usage = UsageMetadata(input_tokens=90, output_tokens=20, model="q", source="reported")
    p = meter.wrap(_Provider(usage), _bindung(), "implementer")
    p.complete("p")
    assert meter.exceeded
    with pytest.raises(BudgetExceeded):
        p.complete("p")


def test_keine_geheimnisse_im_record(tmp_path):
    """INV-04: Bindungsinfo ohne API-Key."""
    from sdd_cli.bench.suites import _binding_info
    from sdd_cli.config import SddConfig

    raw = {"llm": {"profiles": {"lokal": {"provider": "openai-compat", "base_url": "http://h/v1",
                                          "model": "q", "api_key": "sk-geheim"}},
                   "roles": {"implementer": {"profile": "lokal"}}}}
    info = _binding_info(SddConfig(root=tmp_path, raw=raw, raw_basis=raw), "implementer",
                         "lokal")
    assert "sk-geheim" not in str(info) and info["endpoint"] == "http://h/v1"
