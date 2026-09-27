# AUTO-GENERATED from CON-0226 via sdd test generate — do not delete
"""TST-0255 – CON-0226: Suite e2e, Fixture und Ausgänge im Report.

Spec: SPEC-0063 · Contract: CON-0226
Ein Mini-Fixture (Pipeline-Testprojekt mit Shell-Tests) läuft über echte `sdd pipeline run`-Prozesse
gegen den Fake-LLM-Server. Der Fixture-Test prüft `todo-service` aus dem Blueprint.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from sdd_cli.bench.suites import fr_status
from tests.support.fake_llm import FakeLLM, prompt_text
from tests.support.pipeline_project import (
    abnahme,
    command,
    implementierung,
    make_pipeline_project,
    review,
    rot_test,
    task,
)

REPO = Path(__file__).resolve().parents[2]
TODO = REPO / "tool/sdd_cli/blueprint/bench/fixtures/todo-service"
T1 = task("Start", ["FR-01"], "src/start.sh")
ROLLEN = ("decomposer", "test_author", "implementer", "reviewer", "supervisor")


@pytest.fixture()
def llm():
    fake = FakeLLM().start()
    yield fake
    fake.stop()


@pytest.fixture()
def projekt(tmp_path, monkeypatch, llm):
    from sdd_cli.init import init_project

    fixture = tmp_path / "bench/fixtures/mini"
    make_pipeline_project(fixture / "project", monkeypatch, llm, frs=("FR-01",))
    (fixture / "hidden/tests").mkdir(parents=True)
    (fixture / "hidden/tests/acc_fr01.test.sh").write_text(
        '# GEHEIM-E2E: nur im versteckten Test\n[ "$(sh src/start.sh)" = "ok" ]\n')
    init_project(tmp_path, title="Bench e2e")
    pfad = tmp_path / ".sdd/config.yaml"
    daten = yaml.safe_load(pfad.read_text(encoding="utf-8"))
    basis = {"provider": "openai-compat", "base_url": llm.base_url, "api_key": "fake"}
    daten["llm"]["profiles"] = {f"p-{r}": {**basis, "model": f"fake-{r}"} for r in ROLLEN}
    pfad.write_text(yaml.safe_dump(daten, sort_keys=False), encoding="utf-8")
    (tmp_path / "bench/suites").mkdir(parents=True)
    _suite(tmp_path)
    _matrix(tmp_path)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _suite(root: Path, **extra) -> None:
    (root / "bench/suites/e2e.yaml").write_text(yaml.safe_dump({
        "name": "e2e", "kind": "e2e", "fixture": "bench/fixtures/mini", "specs": ["SPEC-0900"],
        "test_command": "sh .sdd/quality/run_tests.sh > {junit}", **extra}))


def _matrix(root: Path, **extra) -> None:
    (root / "bench/matrix.yaml").write_text(yaml.safe_dump({
        "suites": ["e2e"], "repetitions": 1,
        "assignments": [{"name": "fake", "roles": {r: f"p-{r}" for r in ROLLEN}}], **extra}))


def _cli(*args: str):
    from sdd_cli.main import cli

    return CliRunner().invoke(cli, list(args))


def _voll(llm) -> None:
    llm.antworte("decomposer", {"tasks": [{k: v for k, v in T1.items()}]})
    llm.antworte("supervisor", command("S1", "approve"), abnahme(FR_01="erfüllt"))
    llm.antworte("test_author", rot_test(T1))
    llm.antworte("implementer", implementierung(T1))
    llm.antworte("reviewer", review())


def _records(root: Path) -> list[dict]:
    [ordner] = (root / "bench/results").iterdir()
    return [json.loads(z) for z in (ordner / "results.jsonl").read_text().splitlines()]


def _stand(root: Path) -> dict[str, str]:
    ignoriert = ("bench/results", ".sdd/evaluations.db")
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file()
            and not str(p.relative_to(root)).startswith(ignoriert)}


def test_tc01_ganze_spec_auf_einem_fixture(projekt, llm):
    """Scenario: Ganze Spec auf einem Fixture (CON-0226)."""
    _voll(llm)
    vorher = _stand(projekt)
    ergebnis = _cli("bench", "run", "--suite", "e2e")
    assert ergebnis.exit_code == 0, ergebnis.output
    [record] = _records(projekt)
    assert record["q_kind"] == "quality" and record["outcome"] == "completed", record
    assert record["frs_total"] == 1 and record["frs_met"] == 1 and record["Q_req"] == 1.0
    assert record["tokens"]["implementer"]["input"] == 100
    assert set(record["tokens"]) == set(ROLLEN)
    assert record["git_sha"] and record["attempts"] == 1 and record["failed_attempts"] == 0
    assert _stand(projekt) == vorher


def test_tc02_versteckte_tests_bleiben_verborgen(projekt, llm):
    """Scenario: Versteckte Tests bleiben verborgen (CON-0226)."""
    _voll(llm)
    assert _cli("bench", "run", "--suite", "e2e").exit_code == 0
    assert llm.anfragen and not any("GEHEIM-E2E" in prompt_text(a) for a in llm.anfragen)


def test_tc03_budget_im_e2e_lauf(projekt, llm):
    """Scenario: Budget im e2e-Lauf (CON-0226)."""
    _matrix(projekt, budget={"max_tokens": 100})
    _voll(llm)
    assert _cli("bench", "run", "--suite", "e2e").exit_code == 0
    [record] = _records(projekt)
    assert record["outcome"] == "halted: budget"
    assert record["T_in"] + record["T_out"] == 150 and record["frs_total"] == 1
    assert llm.aufrufe("supervisor") == []


def test_tc04_unbekannte_isolation(projekt, llm):
    """Scenario: Unbekannte Isolation (CON-0226)."""
    _suite(projekt, isolation="container")
    assert _cli("bench", "run", "--suite", "e2e").exit_code == 2
    assert llm.anfragen == []


def _spec_frs(pfad: Path) -> int:
    return len(set(re.findall(r"^- \*\*(FR-\d+)", pfad.read_text(encoding="utf-8"), re.M)))


def _hidden_run(tmp_path: Path, *, mit_referenz: bool) -> tuple[int, int]:
    ws = tmp_path / ("mit" if mit_referenz else "ohne")
    shutil.copytree(TODO / "project", ws)
    if mit_referenz:
        shutil.copytree(TODO / "reference", ws, dirs_exist_ok=True)
    shutil.copytree(TODO / "hidden", ws, dirs_exist_ok=True)
    suite = yaml.safe_load((REPO / "tool/sdd_cli/blueprint/bench/suites/e2e.yaml").read_text())
    junit = ws / "junit.xml"
    befehl = suite["test_command"].format(python=sys.executable, junit=str(junit))
    subprocess.run(befehl, shell=True, cwd=ws, capture_output=True, timeout=600)
    return fr_status(junit)


def test_tc05_fixture_todo_service(tmp_path):
    """Scenario: Fixture todo-service (CON-0226)."""
    specs = sorted((TODO / "project/.sdd/specs").glob("SPEC-*.md"))
    assert [_spec_frs(s) for s in specs] == [3, 6, 10]
    for s in specs:
        fm = yaml.safe_load(s.read_text(encoding="utf-8").split("---", 2)[1])
        assert fm["status"] == "approved"
        gate = json.loads((TODO / "project/.sdd/pipeline" / f"{fm['id']}-gate.json").read_text())
        assert gate["pipeline_phase"] == "execute-unlocked"
    assert _hidden_run(tmp_path, mit_referenz=True) == (19, 19)
    assert _hidden_run(tmp_path, mit_referenz=False)[0] == 0


def test_tc06_ausgaenge_im_report(tmp_path):
    """Scenario: Ausgänge im Report (CON-0226)."""
    from sdd_cli.bench.report import markdown

    basis = {"kind": "bench-record", "suite": "e2e", "suite_kind": "e2e", "q_kind": "quality",
             "assignment": "a", "roles": {}, "repetition": 1, "tokens": {}, "T_in": 10,
             "T_out": 5, "T_reason": 0, "T_claude": 0, "duration_ms": 1, "sdd_version": "0",
             "created_at": "2026-09-27T10:00:00Z", "artifacts": "x", "task": "SPEC-0001",
             "Q_req": 1.0, "Q_arch": None, "Q_code": None, "frs_total": 1, "frs_met": 1,
             "attempts": 1, "failed_attempts": 0, "git_sha": "abc1234", "Q": 1.0}
    records = [{**basis, "run_id": "1", "outcome": "completed"},
               {**basis, "run_id": "2", "outcome": "halted: budget", "repetition": 2}]
    md = markdown(tmp_path, records)
    assert "1× completed, 1× halted: budget" in md
