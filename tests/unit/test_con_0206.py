"""TST-0235 – CON-0206: token_usage 2.0 (Zeilenschema und Aufrufkontext).

Spec: SPEC-0060 · Contract: CON-0206
"""
from __future__ import annotations

import json

from tests.support.quality_project import SCHEMAS, schema_validator
from tests.support.usage_support import requires_usage_capture

SCHEMAS.setdefault("token_usage", SCHEMAS["report"].parent /
                   "token-usage-2-0-zeilenschema-und-aufrufkontext.schema.json")

ALT = {"id": 1, "timestamp": "2026-06-01T10:00:00Z", "spec_id": None,
       "component": "review-contract", "model": "qwen", "input_tokens": 10, "output_tokens": 5,
       "cache_read_tokens": 0, "cache_write_tokens": 0, "duration_ms": 0, "calibrated": 0,
       "task_id": None, "task_label": None, "agent_type": None}
NEU = {**ALT, "id": 2, "reasoning_tokens": 40, "finish_reason": "end_turn",
       "server_model": "claude-opus-5-5", "source": "reported",
       "run_id": "SPEC-0900-20260925T101500-a1",
       "context_json": json.dumps({"role": "implementer", "attempt": 1, "call_id": "c-7"})}


def _fehler(instanz):
    return [e.message for e in schema_validator("token_usage").iter_errors(instanz)]


def test_tc01_valid_instance_passes():
    """Alte und neue Zeilen sind gültig (CON-0206)."""
    assert _fehler(ALT) == [] and _fehler(NEU) == []


def test_tc02_invalid_instance_rejected():
    """Beispiel aus dem Contract: negative Tokens, unbekannte source, Prompttext."""
    assert _fehler({**NEU, "input_tokens": -1, "source": "guess", "prompt": "…"})


def test_inv01_keine_zweite_zeitspalte():
    assert _fehler({**NEU, "latency_ms": 5})


def test_inv02_source_geschlossen():
    assert _fehler({**NEU, "source": "guess"})
    assert _fehler({**ALT, "source": None}) == []


def test_inv05_reasoning_null_heisst_nicht_gemeldet():
    assert _fehler({**NEU, "reasoning_tokens": None}) == []
    assert _fehler({**NEU, "reasoning_tokens": -1})


def test_spec_id_praefix_ist_projektabhaengig():
    """CON-0041 kennt kein festes Muster; Präfixe sind konfigurierbar."""
    assert _fehler({**NEU, "spec_id": "FEAT-0001"}) == []


def test_inv07_model_nicht_leer_bei_agent_type():
    assert _fehler({**NEU, "model": "", "agent_type": "cloud"})
    assert _fehler({**ALT, "model": ""}) == []


def test_inv08_task_id_verlangt_task_label():
    assert _fehler({**NEU, "task_id": "T1", "task_label": None})
    assert _fehler({**NEU, "task_id": "T1", "task_label": ""})
    assert _fehler({**NEU, "task_id": "T1", "task_label": "Parser"}) == []


@requires_usage_capture
def test_inv03_sqlite_senke_schreibt_kontext_als_objekt(tmp_path):
    import sqlite3

    from sdd_cli.config import load_config
    from sdd_cli.init import init_project
    from sdd_cli.llm.base import UsageMetadata
    from sdd_cli.llm.usage import SqliteUsageSink, UsageRecord

    init_project(tmp_path, title="U")
    senke = SqliteUsageSink(load_config(tmp_path))
    senke.record(UsageRecord(component="completion", model="m",
                             usage=UsageMetadata(input_tokens=3, output_tokens=2, source="reported"),
                             duration_ms=5,
                             context={"spec_id": "SPEC-0900", "run_id": "r1", "role": "x",
                                      "task_id": "T1", "task_label": "Parser",
                                      "agent_type": "local"}))
    with sqlite3.connect(tmp_path / ".sdd/evaluations.db") as con:
        con.row_factory = sqlite3.Row
        [zeile] = [dict(r) for r in con.execute("SELECT * FROM token_usage")]
    assert json.loads(zeile["context_json"]) == {"role": "x"}
    assert zeile["spec_id"] == "SPEC-0900" and zeile["run_id"] == "r1"
    assert (zeile["task_id"], zeile["task_label"], zeile["agent_type"]) == ("T1", "Parser", "local")
    assert _fehler(zeile) == []
