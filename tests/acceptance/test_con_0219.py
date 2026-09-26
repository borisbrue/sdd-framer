# AUTO-GENERATED from CON-0219 via sdd test generate — do not delete
"""TST-0248 – CON-0219: Checks, Eval-Ablauf, Holdout-Sicht, capture und Rolle judge.

Spec: SPEC-0055 · Contract: CON-0219
Rollen und Judge laufen gegen den Fake-LLM-Server; Fälle werden je Test angelegt (die vom Blueprint
installierten Fälle werden vorher entfernt).
"""
from __future__ import annotations

import difflib
import hashlib
import json
import shutil
import time
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from sdd_cli.pipeline.checks import CheckEnv, run_check
from tests.support.fake_llm import FakeLLM, prompt_text

SPEC = "# Probe\n\n## 4. Funktionale Anforderungen\n\n- **FR-01:** Anlegen.\n- **FR-02:** Löschen.\n"


def _tasks(*frs: str) -> dict:
    return {"tasks": [{"title": f"Task {fr}", "description": "d", "type": "code",
                       "complexity": "low", "fr_ids": [fr], "dependencies": [],
                       "test_file": f"tests/test_{i}.py", "test_command": "true",
                       "allowed_paths": [f"src/m{i}.py"]} for i, fr in enumerate(frs)]}


@pytest.fixture()
def llm():
    fake = FakeLLM().start()
    yield fake
    fake.stop()


@pytest.fixture()
def projekt(tmp_path, monkeypatch, llm):
    from sdd_cli.init import init_project

    pytest.importorskip("openai")
    init_project(tmp_path, title="Evals")
    for rolle_dir in (tmp_path / ".sdd/roles").iterdir():
        if rolle_dir.is_dir():
            shutil.rmtree(rolle_dir)
    shutil.rmtree(tmp_path / ".sdd/holdout/roles", ignore_errors=True)
    pfad = tmp_path / ".sdd/config.yaml"
    daten = yaml.safe_load(pfad.read_text(encoding="utf-8"))
    profil = {"provider": "openai-compat", "base_url": llm.base_url, "api_key": "fake"}
    daten.setdefault("llm", {})["profiles"] = {
        "lokal": {**profil, "model": "fake-decomposer"},
        "sup": {**profil, "model": "fake-supervisor"}}
    daten["llm"]["roles"] = {"judge": {**profil, "model": "fake-judge"}}
    pfad.write_text(yaml.safe_dump(daten, sort_keys=False), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _cli(*args: str):
    from sdd_cli.main import cli

    return CliRunner().invoke(cli, list(args))


def _fall(root: Path, cid: str, *, holdout=False, checks=None, rubric=None, spec=SPEC,
          role="decomposer") -> Path:
    basis = root / (".sdd/holdout/roles" if holdout else ".sdd/roles") / role
    ordner = (basis if holdout else basis / "cases") / f"{cid}-probe"
    (ordner / "input").mkdir(parents=True)
    (ordner / "input/spec.md").write_text(spec, encoding="utf-8")
    daten = {"id": cid, "role": role, "origin": "manual",
             "expect": {"checks": checks or [{"json_schema": {}}, {"fr_coverage": {"min": 1.0}},
                                            {"task_count": {"min": 2, "max": 4}}]}}
    if rubric:
        daten["expect"]["rubric"] = rubric
    (ordner / "case.yaml").write_text(yaml.safe_dump(daten), encoding="utf-8")
    return ordner


def _stand(root: Path) -> dict[str, str]:
    ignoriert = (".sdd/role-evals", ".sdd/evaluations.db")
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file()
            and not str(p.relative_to(root)).startswith(ignoriert)}


def _decomposer_antwortet(llm, n: int):
    llm.antworte("decomposer", *[_tasks("FR-01", "FR-02")] * n)


def test_tc01_eval_ueber_sichtbare_und_holdout_faelle(projekt, llm):
    """Scenario: Eval über sichtbare und Holdout-Fälle (CON-0219)."""
    for i in range(1, 6):
        _fall(projekt, f"DEC-00{i}")
    for i in range(6, 9):
        _fall(projekt, f"DEC-00{i}", holdout=True)
    _decomposer_antwortet(llm, 8 * 3)
    vorher = _stand(projekt)
    ergebnis = _cli("role", "eval", "decomposer", "--model", "lokal", "--runs", "3", "--json")
    assert ergebnis.exit_code == 0, ergebnis.output
    daten = json.loads(ergebnis.output)
    assert len(daten["visible"]) == 5 and daten["holdout"]["cases"] == 3
    for fall in daten["visible"]:
        assert len(fall["runs"]) == 3 and fall["passed"]
        assert {"input_tokens", "output_tokens", "reasoning_tokens"} <= set(fall["runs"][0]["tokens"])
    assert _stand(projekt) == vorher
    assert list((projekt / ".sdd/role-evals").glob("*-decomposer-lokal.json"))


def test_tc02_holdout_bleibt_verborgen(projekt, llm):
    """Scenario: Holdout bleibt verborgen (CON-0219)."""
    _fall(projekt, "DEC-001")
    _fall(projekt, "DEC-009", holdout=True, spec=SPEC + "\nGEHEIMER-HINWEIS\n")
    _decomposer_antwortet(llm, 2)
    ergebnis = _cli("role", "eval", "decomposer", "--model", "lokal", "--runs", "1")
    assert ergebnis.exit_code == 0, ergebnis.output
    assert "DEC-009" not in ergebnis.output and "GEHEIMER" not in ergebnis.output
    [report] = (projekt / ".sdd/role-evals").glob("*.json")
    assert "DEC-009" not in report.read_text(encoding="utf-8")


def test_tc03_holdout_szenarien_ignorieren_rollen_faelle(projekt):
    """Scenario: Holdout-Szenarien ignorieren Rollen-Fälle (CON-0219)."""
    from sdd_cli.config import load_config
    from sdd_cli.evaluator import _load_holdout_docs
    from sdd_cli.holdout_paths import scenario_files

    ordner = _fall(projekt, "DEC-006", holdout=True)
    (ordner / "input/spec.md").write_text(
        "---\nid: HOL-0999\ntitle: X\nspec: SPEC-0900\ncontract: CON-0900\nstatus: active\n---\n",
        encoding="utf-8")
    hol = projekt / ".sdd/holdout/HOL-0001-echt.md"
    hol.write_text("---\nid: HOL-0001\ntitle: Echt\nspec: SPEC-0900\ncontract: CON-0900\n"
                   "status: active\n---\n\n## Input\nx\n", encoding="utf-8")
    dateien = list(scenario_files(projekt / ".sdd/holdout"))
    assert dateien == [hol]
    ids = [d.frontmatter.get("id") for d in _load_holdout_docs(load_config(projekt))]
    assert "HOL-0999" not in ids


# ── Checks mit Positiv- und Negativfall ──────────────────────────────────────

def _py_fall(tmp_path: Path, *, stub: str, referenz: str, mutant: str | None = None) -> Path:
    fall = tmp_path / "fall"
    (fall / "input/repo/pkg").mkdir(parents=True)
    (fall / "input/repo/pkg/__init__.py").write_text("")
    (fall / "input/repo/tests").mkdir()
    (fall / "input/repo/tests/__init__.py").write_text("")
    (fall / "input/repo/pkg/m.py").write_text(stub)
    (fall / "reference/pkg").mkdir(parents=True)
    (fall / "reference/pkg/m.py").write_text(referenz)
    if mutant is not None:
        diff = difflib.unified_diff(referenz.splitlines(keepends=True),
                                    mutant.splitlines(keepends=True), "a/pkg/m.py", "b/pkg/m.py")
        (fall / "mutants").mkdir()
        (fall / "mutants/01.patch").write_text("".join(diff))
    return fall


REFERENZ = "def doppelt(x):\n    return 2 * x\n"
TEST_GUT = ("import unittest\nfrom pkg.m import doppelt\n\nclass T(unittest.TestCase):\n"
            "    def test_fr01(self):\n        self.assertEqual(doppelt(3), 6)\n"
            "        self.assertEqual(doppelt(0), 0)\n")
TEST_SCHWACH = ("import unittest\nfrom pkg.m import doppelt\n\nclass T(unittest.TestCase):\n"
                "    def test_fr01(self):\n        self.assertEqual(doppelt(0), 0)\n")
CMD = "python3 -m unittest discover -s tests -t ."


def _env(fall: Path, output, **kw) -> CheckEnv:
    return CheckEnv(output=output, case_dir=fall, test_command=CMD, timeout=60, **kw)


def test_tc04_check_mit_positiv_und_negativfall(tmp_path):
    """Scenario Outline: Check mit Positiv- und Negativfall (CON-0219)."""
    zerlegung = _tasks("FR-01", "FR-02")
    zerlegung["tasks"][0]["title"] = "Datenmodell anlegen"
    zerlegung["tasks"][1]["title"] = "API-Endpunkt"
    assert run_check("task_count", CheckEnv(zerlegung, params={"min": 4})).status == "fail"
    assert run_check("ordered_before", CheckEnv(
        zerlegung, params={"first": "Datenmodell", "then": "API"})).status == "pass"
    assert run_check("ordered_before", CheckEnv(
        zerlegung, params={"first": "API", "then": "Datenmodell"})).status == "fail"

    fall = _py_fall(tmp_path, stub="def doppelt(x):\n    return x\n", referenz=REFERENZ,
                    mutant="def doppelt(x):\n    return x + x if x else 1\n")
    gut = {"test_file": "tests/test_m.py", "content": TEST_GUT}
    schwach = {"test_file": "tests/test_m.py", "content": TEST_SCHWACH}
    assert run_check("red_against_stub", _env(fall, gut)).status == "pass"
    assert run_check("red_against_stub", _env(fall, schwach)).status == "fail"
    assert run_check("green_against_reference", _env(fall, gut)).status == "pass"
    assert run_check("mutation_kill_rate", _env(fall, gut)).score == 1.0
    ergebnis = run_check("mutation_kill_rate", _env(fall, {
        "test_file": "tests/test_m.py",
        "content": TEST_SCHWACH.replace("doppelt(0), 0", "doppelt(3), 6")}))
    assert ergebnis.status == "fail" and ergebnis.score == 0.0

    (fall / "hidden/tests").mkdir(parents=True)
    (fall / "hidden/tests/test_h.py").write_text(TEST_GUT)
    for code, erwartet in ((REFERENZ, "pass"), ("def doppelt(x):\n    return x\n", "fail")):
        ws = tmp_path / f"ws-{erwartet}"
        shutil.copytree(fall / "input/repo", ws)
        (ws / "pkg/m.py").write_text(code)
        assert run_check("hidden_tests_pass", _env(fall, {"files": []}, workspace=ws)).status \
            == erwartet

    (fall / "expected").mkdir()
    (fall / "expected/findings.json").write_text(json.dumps(
        {"bugs": [{"file": "pkg/m.py", "line": 2, "keywords": ["Grenzfall"]}]}))
    treffer = {"verdict": "fail", "findings": [
        {"category": "quality", "file": "pkg/m.py", "line": 3, "reason": "falsch"}]}
    daneben = {"verdict": "fail", "findings": [
        {"category": "quality", "file": "pkg/x.py", "line": 2, "reason": "falsch"}]}
    assert run_check("seeded_bug_recall", _env(fall, treffer)).status == "pass"
    assert run_check("seeded_bug_recall", _env(fall, daneben)).status == "fail"
    assert run_check("clean_diff_precision", CheckEnv({"verdict": "pass",
                                                       "findings": []})).status == "pass"
    assert run_check("clean_diff_precision", CheckEnv(treffer)).status == "fail"

    (fall / "expected/decision.json").write_text(json.dumps({"point": "S1", "command": "approve"}))
    assert run_check("decision_matches", _env(fall, {"point": "S1", "command": "revise"})) \
        .status == "fail"
    assert run_check("decision_matches", _env(fall, {"point": "S1", "command": "approve"})) \
        .status == "pass"
    assert run_check("reason_mentions", CheckEnv({"reason": "FR-03 fehlt"},
                                                 params={"terms": ["FR-03"]})).status == "pass"


def test_tc05_zeitueberschreitung_eines_tests(tmp_path):
    """Scenario: Zeitüberschreitung eines Tests (CON-0219)."""
    fall = tmp_path / "fall"
    (fall / "hidden").mkdir(parents=True)
    ws = tmp_path / "ws"
    ws.mkdir()
    ergebnis = run_check("hidden_tests_pass", CheckEnv(
        {"files": []}, case_dir=fall, workspace=ws, test_command="sleep 5", timeout=1))
    assert ergebnis.status == "fail" and "Zeitlimit" in ergebnis.details[0]


def test_tc06_gate_nutzt_nur_gate_faehige_checks(projekt):
    """Scenario: Gate nutzt nur gate-fähige Checks (CON-0219)."""
    rolle = projekt / ".sdd/roles/implementer.md"
    text = rolle.read_text(encoding="utf-8")
    kopf, rest = text.split("checks: [", 1)
    rolle.write_text(kopf + "checks: [hidden_tests_pass, " + rest, encoding="utf-8")
    ergebnis = _cli("validate")
    assert "im Gate nicht nutzbar" in " ".join(ergebnis.output.split())


def _run_mit_entscheidung(root: Path) -> str:
    from sdd_cli.pipeline.store import RunStore

    store = RunStore.create(root, "SPEC-0900")
    anfrage = {"request_id": "req-3", "point": "S1", "created_at": "2026-09-26T10:00:00Z",
               "allowed_commands": ["approve", "revise", "halt"],
               "facts": {"gate_results": [], "tasks": [], "frs": {"FR-02": "ohne Task"}}}
    (store.dir / "requests").mkdir()
    (store.dir / "requests/req-3.json").write_text(json.dumps(anfrage))
    store.write_state({"run_id": store.run_id, "status": "running"})
    store.decision({"request_id": "req-3", "point": "S1", "source": "inline", "valid": True,
                    "command": {"point": "S1", "command": "revise",
                                "reason": "FR-02 fehlt"}})
    return store.run_id


def test_tc07_fall_aus_einem_pipeline_fehlschlag(projekt, llm):
    """Scenario: Fall aus einem Pipeline-Fehlschlag (CON-0219)."""
    run_id = _run_mit_entscheidung(projekt)
    ergebnis = _cli("role", "case", "capture", run_id, "req-3")
    assert ergebnis.exit_code == 0, ergebnis.output
    [ordner] = (projekt / ".sdd/roles/supervisor/cases").iterdir()
    daten = yaml.safe_load((ordner / "case.yaml").read_text(encoding="utf-8"))
    assert daten["id"].startswith("SUP-") and daten["draft"] is True
    assert {"decision_matches": {}} in daten["expect"]["checks"]
    assert json.loads((ordner / "expected/decision.json").read_text()) == {
        "point": "S1", "command": "revise"}
    from sdd_cli.pipeline.evals.cases import list_cases, role_home

    assert list_cases(role_home(projekt, "supervisor")) == []


def test_tc08_capture_mit_unbekannter_id(projekt):
    """Scenario: Capture mit unbekannter ID (CON-0219)."""
    run_id = _run_mit_entscheidung(projekt)
    assert _cli("role", "case", "capture", run_id, "req-999").exit_code == 2
    assert _cli("role", "case", "capture", "SPEC-0900-20260101T000000-abc", "req-3").exit_code == 2


def test_tc09_judge_bewertet_blind(projekt, llm):
    """Scenario: Judge bewertet blind (CON-0219)."""
    _fall(projekt, "DEC-001", rubric=[{"id": "granularity", "question": "Einzeln testbar?"}])
    _decomposer_antwortet(llm, 1)
    llm.antworte("judge", {"scores": {"granularity": 4}, "begruendung": "ok"})
    ergebnis = _cli("role", "eval", "decomposer", "--model", "lokal", "--runs", "1", "--json")
    assert ergebnis.exit_code == 0, ergebnis.output
    [anfrage] = llm.aufrufe("judge")
    text = prompt_text(anfrage)
    assert "lokal" not in text and "fake-decomposer" not in text and "Einzeln testbar?" in text
    daten = json.loads(ergebnis.output)
    assert daten["judge"]["model"] == "fake-judge" and daten["judge"]["rubric_version"]
    assert daten["visible"][0]["runs"][0]["rubric"] == {"granularity": 4}


def test_tc10_sdd_quality_judge_nutzt_die_rolle_judge(projekt):
    """Scenario: sdd quality --judge nutzt die Rolle judge (CON-0219)."""
    from sdd_cli.config import load_config
    from sdd_cli.pipeline.facade import judge_provider

    _, modell = judge_provider(load_config(projekt))
    assert modell == "fake-judge"


def test_rate_limit_je_endpunkt():
    """INV-08: requests_per_minute begrenzt die Aufrufe je Endpunkt."""
    from sdd_cli.pipeline.evals.runner import RateLimiter
    from sdd_cli.pipeline.providers import RoleBinding

    bindung = RoleBinding("decomposer", "openai-compat", "m", "http://h", None,
                          {"requests_per_minute": 600}, "profile:x")
    limiter = RateLimiter()
    start = time.monotonic()
    for _ in range(3):
        limiter.wait(bindung)
    assert time.monotonic() - start >= 0.19
