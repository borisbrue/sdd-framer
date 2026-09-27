# AUTO-GENERATED from CON-0223 via sdd test generate — do not delete
"""TST-0252 – CON-0223: Bench-Lauf, Isolation, Suiten roles und regen.

Spec: SPEC-0056 · Contract: CON-0223
Die Suite regen läuft auf einem Mini-Git-Projekt im Testverzeichnis; Rollen antworten über den
Fake-LLM-Server.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from tests.support.fake_llm import FakeLLM, prompt_text

MODUL = '''"""Verdoppelt Zahlen für die Probe."""


def doppelt(x):
    # GEHEIM-MARKER: steht nur in der Referenz
    return 2 * x
'''
TEST = '''from pkg.m import doppelt


def test_fr01_doppelt():
    assert doppelt(3) == 6
    assert doppelt(0) == 0
'''
CMD = "{python} -m pytest -q -p no:cacheprovider --junitxml {junit} {tests}"


def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), "-c", "user.email=t@t", "-c", "user.name=T",
                           *args], check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture()
def llm():
    fake = FakeLLM().start()
    yield fake
    fake.stop()


@pytest.fixture()
def projekt(tmp_path, monkeypatch, llm):
    from sdd_cli.init import init_project

    pytest.importorskip("openai")
    init_project(tmp_path, title="Bench")
    for rolle_dir in (tmp_path / ".sdd/roles").iterdir():
        if rolle_dir.is_dir():
            shutil.rmtree(rolle_dir)
    shutil.rmtree(tmp_path / ".sdd/holdout/roles", ignore_errors=True)
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg/__init__.py").write_text("")
    (tmp_path / "pkg/m.py").write_text(MODUL)
    (tmp_path / "tests").mkdir(exist_ok=True)
    (tmp_path / "tests/test_m.py").write_text(TEST)
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", "pkg", "tests")
    _git(tmp_path, "commit", "-q", "-m", "probe")
    sha = _git(tmp_path, "rev-parse", "HEAD")
    pfad = tmp_path / ".sdd/config.yaml"
    daten = yaml.safe_load(pfad.read_text(encoding="utf-8"))
    basis = {"provider": "openai-compat", "base_url": llm.base_url, "api_key": "fake"}
    daten["llm"]["profiles"] = {**{p: {**basis, "model": "fake-implementer"}
                                   for p in ("p1", "p2", "p3", "a", "b")},
                                "pa": {**basis, "model": "fake-decomposer"},
                                "pb": {**basis, "model": "fake-decomposer"}}
    pfad.write_text(yaml.safe_dump(daten, sort_keys=False), encoding="utf-8")
    (tmp_path / "bench/suites").mkdir(parents=True)
    (tmp_path / "bench/suites/regen.yaml").write_text(yaml.safe_dump({
        "name": "regen", "kind": "regen", "commit": sha, "include": ["pkg", "tests"],
        "test_command": CMD, "attempts": 1,
        "tasks": [{"module": "pkg/m.py", "tests": ["tests/test_m.py"]}]}))
    (tmp_path / "bench/suites/roles.yaml").write_text(yaml.safe_dump(
        {"name": "roles", "kind": "roles", "roles": ["decomposer"], "runs": 1}))
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _matrix(root: Path, daten: dict) -> None:
    (root / "bench/matrix.yaml").write_text(yaml.safe_dump(daten), encoding="utf-8")


def _cli(*args: str):
    from sdd_cli.main import cli

    return CliRunner().invoke(cli, list(args))


def _implementer(llm, n: int, **optionen) -> None:
    llm.antworte("implementer", *[{"files": [{"path": "pkg/m.py", "content": MODUL}],
                                   "explanation": "neu"}] * n, **optionen)


def _records(root: Path) -> list[dict]:
    [ordner] = (root / "bench/results").iterdir()
    return [json.loads(z) for z in (ordner / "results.jsonl").read_text().splitlines()]


def _stand(root: Path) -> dict[str, str]:
    ignoriert = ("bench/results", ".sdd/evaluations.db", ".git")
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file()
            and not str(p.relative_to(root)).startswith(ignoriert)}


SWEEP = {"suites": ["regen"], "repetitions": 1,
         "sweep": {"role": "implementer", "profiles": ["p1", "p2", "p3"]}}


def test_tc01_sweep_ueber_drei_profile_in_regen(projekt, llm):
    """Scenario: Sweep über drei Profile in regen (CON-0223)."""
    _matrix(projekt, SWEEP)
    _implementer(llm, 3)
    vorher = _stand(projekt)
    ergebnis = _cli("bench", "run", "--suite", "regen", "--repetitions", "1")
    assert ergebnis.exit_code == 0, ergebnis.output
    records = _records(projekt)
    assert sorted(r["assignment"] for r in records) == ["sweep-p1", "sweep-p2", "sweep-p3"]
    assert all(r["q_kind"] == "quality" and r["outcome"] == "completed" and r["Q"] == 1.0
               and r["frs_met"] == r["frs_total"] == 1 for r in records)
    assert _stand(projekt) == vorher
    assert (projekt / "pkg/m.py").read_text() == MODUL


def test_tc02_versteckte_tests_bleiben_verborgen(projekt, llm):
    """Scenario: Versteckte Tests bleiben verborgen (CON-0223)."""
    _matrix(projekt, {**SWEEP, "sweep": {"role": "implementer", "profiles": ["p1"]}})
    _implementer(llm, 1)
    assert _cli("bench", "run").exit_code == 0
    [anfrage] = llm.aufrufe("implementer")
    text = prompt_text(anfrage)
    assert "GEHEIM-MARKER" not in text and "Verdoppelt Zahlen" in text and "test_fr01" in text


def _decomposer_fall(root: Path) -> None:
    ordner = root / ".sdd/roles/decomposer/cases/DEC-001-probe"
    (ordner / "input").mkdir(parents=True)
    (ordner / "input/spec.md").write_text(
        "# P\n\n## 4. Funktionale Anforderungen\n\n- **FR-01:** A.\n")
    (ordner / "case.yaml").write_text(yaml.safe_dump(
        {"id": "DEC-001", "role": "decomposer", "origin": "manual",
         "expect": {"checks": [{"json_schema": {}}, {"fr_coverage": {"min": 1.0}}]}}))


ZERLEGUNG = {"tasks": [{"title": "A", "description": "d", "type": "code", "complexity": "low",
                        "fr_ids": ["FR-01"], "dependencies": [], "test_file": "tests/t.py",
                        "test_command": "true", "allowed_paths": ["a.py"]}]}


def test_tc03_suite_roles(projekt, llm):
    """Scenario: Suite roles (CON-0223)."""
    _decomposer_fall(projekt)
    _matrix(projekt, {"suites": ["roles"], "repetitions": 1, "profiles": ["pa", "pb"]})
    llm.antworte("decomposer", ZERLEGUNG, ZERLEGUNG)
    ergebnis = _cli("bench", "run", "--suite", "roles")
    assert ergebnis.exit_code == 0, ergebnis.output
    records = _records(projekt)
    assert sorted(r["profile"] for r in records) == ["pa", "pb"]
    assert all(r["q_kind"] == "eval" and r["Q"] == 1.0 for r in records)
    assert all("DEC-" not in json.dumps(r.get("holdout_Q")) for r in records)


def test_tc04_stufenmodell(projekt, llm):
    """Scenario: Stufenmodell (CON-0223)."""
    ordner = projekt / "bench/results/vorher"
    ordner.mkdir(parents=True)
    vorlage = {"kind": "bench-record", "suite": "roles", "suite_kind": "roles", "q_kind": "eval",
               "repetition": 1, "outcome": "completed", "tokens": {}, "T_in": 0, "T_out": 0,
               "T_reason": 0, "T_claude": 0, "duration_ms": 0, "sdd_version": "0",
               "created_at": "2026-09-27T10:00:00Z", "artifacts": "x", "role": "implementer",
               "pass_at_1": 1.0, "pass_all": 1.0}
    records = [{**vorlage, "run_id": f"roles-implementer-{p}-r1", "profile": p, "Q": q,
                "assignment": f"implementer:{p}",
                "roles": {"implementer": {"profile": p, "provider": "openai-compat"}}}
               for p, q in (("a", 0.9), ("b", 0.1))]
    (ordner / "results.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records))
    (projekt / "bench/suites/roles.yaml").write_text(yaml.safe_dump(
        {"name": "roles", "kind": "roles", "roles": ["implementer"], "runs": 1}))
    _matrix(projekt, {"suites": ["roles", "regen"], "repetitions": 1, "top_k": 1,
                      "profiles": ["a", "b"],
                      "sweep": {"role": "implementer", "profiles": ["a", "b"]}})
    _implementer(llm, 1)
    ergebnis = _cli("bench", "run", "--resume", str(ordner))
    assert ergebnis.exit_code == 0, ergebnis.output
    regen = [r for r in _records_in(ordner) if r["suite"] == "regen"]
    assert [r["assignment"] for r in regen] == ["sweep-a"]
    assert json.loads((ordner / "filtered.json").read_text()) == {"regen": ["sweep-b"]}
    report = _cli("bench", "report", str(ordner)).output
    assert "Gefiltert" in report and "sweep-b" in report


def _records_in(ordner: Path) -> list[dict]:
    return [json.loads(z) for z in (ordner / "results.jsonl").read_text().splitlines()]


def test_tc05_budget(projekt, llm):
    """Scenario: Budget (CON-0223)."""
    _matrix(projekt, {**SWEEP, "sweep": {"role": "implementer", "profiles": ["p1"]},
                      "budget": {"max_tokens": 100}})
    _implementer(llm, 1)
    assert _cli("bench", "run").exit_code == 0
    [record] = _records(projekt)
    assert record["outcome"] == "halted: budget"
    assert record["T_in"] + record["T_out"] == 150 and record["Q"] == 1.0


def test_tc06_resume(projekt, llm):
    """Scenario: Resume (CON-0223)."""
    _matrix(projekt, SWEEP)
    _implementer(llm, 3)
    assert _cli("bench", "run").exit_code == 0
    [ordner] = (projekt / "bench/results").iterdir()
    records = _records_in(ordner)
    records[1]["outcome"], records[1]["error"] = "error", "Endpunkt weg"
    behalten = records[:2]
    (ordner / "results.jsonl").write_text("".join(json.dumps(r) + "\n" for r in behalten))
    vorher = len(llm.aufrufe("implementer"))
    _implementer(llm, 2)
    assert _cli("bench", "run", "--resume", str(ordner)).exit_code == 0
    assert len(llm.aufrufe("implementer")) - vorher == 2
    danach = _records_in(ordner)
    assert len(danach) == 3 and all(r["outcome"] == "completed" for r in danach)
    assert len({r["run_id"] for r in danach}) == 3


def test_tc07_probelauf(projekt, llm):
    """Scenario: Probelauf (CON-0223)."""
    _matrix(projekt, SWEEP)
    ergebnis = _cli("bench", "run", "--dry-run")
    assert ergebnis.exit_code == 0 and "3 Läufe" in ergebnis.output
    assert llm.anfragen == [] and not (projekt / "bench/results").exists()


def test_tc08_ungueltige_matrix(projekt):
    """Scenario: Ungültige Matrix (CON-0223)."""
    _matrix(projekt, {**SWEEP, "sweep": {"role": "implementer", "profiles": ["gibtsnicht"]}})
    assert _cli("bench", "run").exit_code == 2


def test_tc09_bench_init(tmp_path, monkeypatch):
    """Scenario: bench init (CON-0223)."""
    from sdd_cli.init import init_project

    init_project(tmp_path, title="Init")
    monkeypatch.chdir(tmp_path)
    assert _cli("bench", "init").exit_code == 0
    matrix = tmp_path / "bench/matrix.yaml"
    assert matrix.is_file() and (tmp_path / "bench/suites/roles.yaml").is_file()
    matrix.write_text("eigene Matrix\n")
    assert _cli("bench", "init").exit_code == 0
    assert matrix.read_text() == "eigene Matrix\n"
    assert "bench/results/" in (tmp_path / ".gitignore").read_text()
