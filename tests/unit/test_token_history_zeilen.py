"""token_history liest die Aufgaben-Zuordnung aus der Datenbank (#112).

Die Zeilen kommen als sqlite3.Row. `"task_id" in row` prueft dort die WERTE,
nicht die Spaltennamen — nur `in row.keys()` ist korrekt. ruff meldet das als
SIM118 ("in dict.keys()"), weil es ein dict vermutet; sein unsicherer Fix haette
task_id, task_label und agent_type in jeder Historienzeile still auf None gesetzt.
"""
from __future__ import annotations

from pathlib import Path


def _config(tmp_path: Path):
    from sdd_cli.config import SddConfig

    (tmp_path / ".sdd").mkdir(exist_ok=True)
    return SddConfig(root=tmp_path, raw={})


def test_aufgaben_zuordnung_kommt_aus_der_datenbank_zurueck(tmp_path):
    from sdd_cli.estimation import persist_token_usage, token_history

    cfg = _config(tmp_path)
    persist_token_usage(
        cfg, component="task-exec", model="m", input_tokens=10, output_tokens=5,
        spec_id="SPEC-0007", task_id="T-001", task_label="Treiber anbinden", agent_type="local",
    )
    [zeile] = token_history(cfg, "SPEC-0007")
    assert zeile.task_id == "T-001"
    assert zeile.task_label == "Treiber anbinden"
    assert zeile.agent_type == "local"


def test_ohne_zuordnung_bleibt_es_none(tmp_path):
    from sdd_cli.estimation import persist_token_usage, token_history

    cfg = _config(tmp_path)
    persist_token_usage(cfg, component="review", model="m", input_tokens=1, output_tokens=1,
                        spec_id="SPEC-0007")
    [zeile] = token_history(cfg, "SPEC-0007")
    assert zeile.task_id is None
