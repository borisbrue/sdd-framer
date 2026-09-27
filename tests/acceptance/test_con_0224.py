# AUTO-GENERATED from CON-0224 via sdd test generate — do not delete
"""TST-0253 – CON-0224: Bench-Report, Vergleich und config apply-roles.

Spec: SPEC-0056 · Contract: CON-0224
Grundlage sind Fixture-Records (CON-0222); kein LLM.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from sdd_cli.bench.report import group, pareto


def _rec(assignment: str, q: float, t_in: int, *, q_kind="quality", profile=None, role=None,
         rep=1, claude=0, estimated=False, server_model=None, params=None) -> dict:
    profile = profile or assignment
    rolle = role or "implementer"
    r = {"kind": "bench-record", "run_id": f"{assignment}-{rep}", "suite": "s",
         "suite_kind": "regen" if q_kind == "quality" else "roles", "q_kind": q_kind,
         "assignment": assignment,
         "roles": {rolle: {"profile": profile, "provider": "openai-compat", "model": "m",
                           "params": params or {}, "server_model": server_model,
                           "endpoint": "http://h", "role_version": "1.0.0"}},
         "repetition": rep, "outcome": "completed", "Q": q,
         "tokens": {rolle: {"input": t_in, "output": 100, "reasoning": 50, "calls": 1,
                            "estimated": estimated}},
         "T_in": t_in, "T_out": 100, "T_reason": 50, "T_claude": claude, "estimated": estimated,
         "duration_ms": 1, "sdd_version": "0", "created_at": "2026-09-27T10:00:00Z",
         "artifacts": "runs/x"}
    if q_kind == "quality":
        r.update(task="pkg/m.py", Q_req=q, Q_arch=1.0, Q_code=1.0, frs_total=4, frs_met=2,
                 attempts=1, failed_attempts=0, git_sha="abc1234")
    else:
        r.update(role=rolle, profile=profile, pass_at_1=1.0, pass_all=1.0, holdout_Q=0.5)
    return r


def _ordner(tmp_path: Path, records: list[dict], name="20260927T100000") -> Path:
    ordner = tmp_path / "bench/results" / name
    ordner.mkdir(parents=True)
    (ordner / "results.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records))
    return ordner


def _cli(*args: str, **kw):
    from sdd_cli.main import cli

    return CliRunner().invoke(cli, list(args), **kw)


@pytest.fixture()
def projekt(tmp_path, monkeypatch):
    from sdd_cli.init import init_project

    init_project(tmp_path, title="Bench")
    pfad = tmp_path / ".sdd/config.yaml"
    text = pfad.read_text(encoding="utf-8")
    daten = yaml.safe_load(text)
    daten["llm"]["profiles"] = {
        "qwen": {"provider": "openai-compat", "base_url": "http://h/v1", "model": "q"},
        "gpt": {"provider": "openai-compat", "base_url": "http://h/v1", "model": "g"}}
    pfad.write_text("# Kopfkommentar bleibt\n" + yaml.safe_dump(daten, sort_keys=False),
                    encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_tc01_report_je_rolle_mit_pareto_front(projekt):
    """Scenario: Report je Rolle mit Pareto-Front (CON-0224)."""
    records = [_rec("sweep-a", 0.9, 5000, profile="a"), _rec("sweep-b", 0.7, 1000, profile="b"),
               _rec("sweep-c", 0.6, 4000, profile="c")]
    ordner = _ordner(projekt, records)
    ergebnis = _cli("bench", "report", str(ordner), "--by", "role", "--html")
    assert ergebnis.exit_code == 0, ergebnis.output
    md = (ordner / "report.md").read_text(encoding="utf-8")
    assert "### implementer" in md and "T_reason" in md
    zeilen = {z.split("|")[1].strip(): z for z in md.splitlines() if z.startswith("| ")
              and z.split("|")[1].strip() in ("a", "b", "c")}
    assert "alle T" in zeilen["a"] and "alle T" in zeilen["b"] and "alle T" not in zeilen["c"]
    assert (ordner / "report.html").is_file()
    assert sorted(p.name for p in ordner.iterdir()) == ["report.html", "report.md",
                                                        "results.jsonl"]


def test_pareto_mit_und_ohne_claude():
    """INV-02: getrennte Fronten mit und ohne Claude-Tokens."""
    records = [_rec("x", 0.8, 1000, claude=900), _rec("y", 0.7, 500)]
    [[x, y]] = [list(v) for v in group(records)["quality"].values()]
    assert {e.key for e in (x, y) if e.pareto_all} == {"x", "y"}
    assert {e.key for e in (x, y) if e.pareto_local} == {"x"}
    assert pareto([], lambda e: 0) == set()


def test_tc02_nicht_unterscheidbar(projekt):
    """Scenario: Nicht unterscheidbar (CON-0224)."""
    records = [_rec("a", 0.75, 1000, rep=1), _rec("a", 0.85, 1000, rep=2),
               _rec("b", 0.77, 1000, rep=1), _rec("b", 0.87, 1000, rep=2)]
    [eintraege] = group(records)["quality"].values()
    assert all(e.indistinct for e in eintraege)
    ordner = _ordner(projekt, records)
    assert "nicht unterscheidbar" in _cli("bench", "report", str(ordner)).output


def test_tc03_getrennte_q_kind(projekt):
    """Scenario: Getrennte q_kind (CON-0224)."""
    records = [_rec("a", 0.9, 1000), _rec("implementer:a", 0.8, 500, q_kind="eval", profile="a")]
    ordner = _ordner(projekt, records)
    md = _cli("bench", "report", str(ordner)).output
    assert "q_kind quality" in md and "q_kind eval" in md


def test_tc04_geschaetzte_tokens(projekt):
    """Scenario: Geschätzte Tokens (CON-0224)."""
    ordner = _ordner(projekt, [_rec("a", 0.9, 1000, estimated=True)])
    assert "1 000*" in _cli("bench", "report", str(ordner)).output


def test_kennzahlen():
    """INV-01: Effizienz, Tokens je erfülltem FR, --exclude-reasoning."""
    [[e]] = [list(v) for v in group([_rec("a", 0.5, 900)])["quality"].values()]
    assert e.efficiency() == pytest.approx(0.5 / (1000 / 1e5))
    assert e.efficiency(exclude_reasoning=True) == pytest.approx(0.5 / (950 / 1e5))
    assert e.tokens_per_fr == 500


def test_tc05_vergleich_mit_getauschtem_modell(projekt):
    """Scenario: Vergleich mit getauschtem Modell (CON-0224)."""
    a = _ordner(projekt, [_rec("lokal", 0.8, 1000, server_model="q-4bit")], "a")
    b = _ordner(projekt, [_rec("lokal", 0.9, 800, server_model="q-8bit")], "b")
    ergebnis = _cli("bench", "compare", str(a), str(b), "--json")
    assert ergebnis.exit_code == 0, ergebnis.output
    daten = json.loads(ergebnis.output)
    [zeile] = daten["rows"]
    assert zeile["delta_Q"] == pytest.approx(0.1) and zeile["delta_T"] == -200
    assert daten["warnings"] and "q-8bit" in daten["warnings"][0]


def test_tc06_belegung_uebernehmen(projekt):
    """Scenario: Belegung übernehmen (CON-0224)."""
    rec = _rec("mix", 0.9, 1000, profile="qwen")
    rec["roles"]["reviewer"] = {**rec["roles"]["implementer"], "profile": "gpt@think",
                                "params": {"thinking": True}}
    ordner = _ordner(projekt, [rec])
    ergebnis = _cli("config", "apply-roles", "--from", str(ordner), "--assignment", "mix",
                    "--yes")
    assert ergebnis.exit_code == 0, ergebnis.output
    text = (projekt / ".sdd/config.yaml").read_text(encoding="utf-8")
    daten = yaml.safe_load(text)
    assert daten["llm"]["roles"]["implementer"] == {"profile": "qwen"}
    assert daten["llm"]["roles"]["reviewer"] == {"profile": "gpt-think"}
    assert daten["llm"]["profiles"]["gpt-think"]["thinking"] is True
    assert text.startswith("# Kopfkommentar bleibt\n")
    from sdd_cli.config import load_config
    from sdd_cli.pipeline.facade import role_config_issues

    assert [i for i in role_config_issues(load_config(projekt)) if i[0] == "error"] == []


def test_tc07_uebernahme_ohne_bestaetigung(projekt):
    """Scenario: Übernahme ohne Bestätigung (CON-0224)."""
    ordner = _ordner(projekt, [_rec("mix", 0.9, 1000, profile="qwen")])
    vorher = (projekt / ".sdd/config.yaml").read_bytes()
    ergebnis = _cli("config", "apply-roles", "--from", str(ordner), "--assignment", "mix",
                    input="n\n")
    assert ergebnis.exit_code == 0 and "Nichts geändert" in ergebnis.output
    assert (projekt / ".sdd/config.yaml").read_bytes() == vorher
    assert _cli("config", "apply-roles", "--from", str(ordner), "--assignment", "fehlt",
                "--yes").exit_code == 2
