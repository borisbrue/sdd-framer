# AUTO-GENERATED from CON-0217 via sdd test generate — do not delete
"""TST-0246 – CON-0217: Golden Case case.yaml und die Fälle im Blueprint.

Spec: SPEC-0055 · Contract: CON-0217
Der Blueprint-Teil prüft jeden Fall wie `sdd validate` und führt die ausführungsbasierten Checks mit
der Referenzlösung aus (grün) und ohne sie (rot). Meldungen zu Holdout-Fällen nennen nie ID oder
Inhalt (CON-0219 INV-09).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from sdd_cli.pipeline.checks import CheckEnv, CheckResult, overlay, run_check
from sdd_cli.pipeline.evals.cases import (
    BLUEPRINT,
    MIN_HOLDOUT,
    Case,
    RoleHome,
    case_problems,
    list_cases,
)
from sdd_cli.pipeline.evals.runner import case_score
from sdd_cli.pipeline.schemas import errors

ROLLEN = ("decomposer", "test_author", "implementer", "reviewer", "supervisor")
MIN_FAELLE = 8

GUELTIG = {"id": "DEC-001", "role": "decomposer", "origin": "blueprint",
           "expect": {"checks": [{"fr_coverage": {"min": 1.0}}, {"task_count": {"min": 4}}],
                      "rubric": [{"id": "granularity", "question": "Einzeln testbar?"}]},
           "weights": {"checks": 0.8, "rubric": 0.2}}


def _fall(tmp_path: Path, daten: dict, *, teile=(), holdout=False) -> Case:
    ordner = tmp_path / f"{daten['id']}-probe"
    (ordner / "input").mkdir(parents=True)
    for teil in teile:
        (ordner / teil).mkdir()
    (ordner / "case.yaml").write_text(yaml.safe_dump(daten), encoding="utf-8")
    return Case(daten["id"], daten["role"], ordner, holdout, daten)


def test_tc01_valid_instance_passes(tmp_path):
    """Valide Instanz besteht Schema-Validierung (CON-0217)."""
    assert errors("role-case", GUELTIG) == []
    assert case_problems(_fall(tmp_path, GUELTIG)) == []


@pytest.mark.parametrize("aenderung, erwartet", [
    ({"id": "X-1"}, "id"),
    ({"holdout": True}, "holdout"),
    ({"expect": {"checks": []}}, "checks"),
    ({"weights": {"checks": 0.5, "rubric": 0.2}}, "weights"),
])
def test_tc02_invalid_instance_rejected(tmp_path, aenderung, erwartet):
    """Invalide Instanz wird abgelehnt (CON-0217)."""
    daten = {**GUELTIG, **aenderung}
    probleme = errors("role-case", daten) or case_problems(_fall(tmp_path, daten))
    assert probleme and any(erwartet in p for p in probleme), probleme


def test_ausfuehrende_checks_brauchen_test_command_und_teile(tmp_path):
    """INV-03/04: hidden_tests_pass ohne test_command und ohne hidden/ ist ungültig."""
    daten = {"id": "IMP-001", "role": "implementer", "origin": "manual",
             "expect": {"checks": [{"hidden_tests_pass": {}}]}}
    probleme = case_problems(_fall(tmp_path, daten))
    assert any("test_command" in p for p in probleme)
    assert any("hidden/" in p for p in probleme)
    ok = {**daten, "test_command": "true"}
    assert case_problems(_fall(tmp_path / "b", ok, teile=("hidden",))) == []


def test_unbekannter_check_und_fehlender_parameter(tmp_path):
    daten = {**GUELTIG, "expect": {"checks": [{"gibtsnicht": {}}, {"ordered_before": {}}]}}
    probleme = case_problems(_fall(tmp_path, daten))
    assert any("gibtsnicht" in p for p in probleme)
    assert any("first" in p for p in probleme)


def test_ort_bestimmt_holdout(tmp_path):
    """INV-01: Holdout ist, was unter holdout_dir liegt."""
    home = RoleHome("decomposer", tmp_path / "decomposer.md", tmp_path / "cases",
                    tmp_path / "holdout")
    for ort, cid in ((home.cases_dir, "DEC-001"), (home.holdout_dir, "DEC-002")):
        d = ort / f"{cid}-x"
        (d / "input").mkdir(parents=True)
        (d / "case.yaml").write_text(yaml.safe_dump({**GUELTIG, "id": cid}), encoding="utf-8")
    faelle = {f.id: f.holdout for f in list_cases(home)}
    assert faelle == {"DEC-001": False, "DEC-002": True}


def test_score_formel_und_entwurf(tmp_path):
    """INV-05/06: Score-Formel; Entwurfsfälle zählen nicht."""
    fall = _fall(tmp_path, GUELTIG)
    checks = [CheckResult("pass", 1.0), CheckResult("fail", 0.5), CheckResult("n/a", None)]
    assert case_score(fall, checks, {"granularity": 5}) == pytest.approx(0.8 * 0.75 + 0.2 * 1.0)
    assert case_score(fall, checks, {}) == pytest.approx(0.75)
    home = RoleHome("decomposer", tmp_path / "d.md", tmp_path / "cases", tmp_path / "h")
    d = home.cases_dir / "DEC-003-x"
    (d / "input").mkdir(parents=True)
    (d / "case.yaml").write_text(yaml.safe_dump({**GUELTIG, "id": "DEC-003", "draft": True}))
    assert list_cases(home) == [] and len(list_cases(home, include_drafts=True)) == 1


# ── Blueprint-Fälle (FR-02) ──────────────────────────────────────────────────

def _home(rolle: str) -> RoleHome:
    return RoleHome(rolle, BLUEPRINT / "roles" / f"{rolle}.md",
                    BLUEPRINT / "roles" / rolle / "cases", BLUEPRINT / "holdout" / "roles" / rolle)


def _name(fall: Case) -> str:
    return f"{fall.role}: Holdout-Fall" if fall.holdout else fall.id


@pytest.mark.parametrize("rolle", ROLLEN)
def test_blueprint_hat_genug_faelle(rolle):
    faelle = list_cases(_home(rolle))
    holdout = [f for f in faelle if f.holdout]
    assert len(faelle) >= MIN_FAELLE, f"{rolle}: {len(faelle)} Fälle"
    assert len(holdout) >= MIN_HOLDOUT, f"{rolle}: {len(holdout)} Holdout-Fälle"
    assert all(f.data.get("origin") == "blueprint" and not f.draft for f in faelle)


@pytest.mark.parametrize("rolle", ROLLEN)
def test_blueprint_faelle_sind_gueltig(rolle):
    ungueltig = [_name(f) for f in list_cases(_home(rolle), include_drafts=True)
                 if case_problems(f)]
    assert ungueltig == [], f"ungültig (Details: sdd validate): {ungueltig}"


def _env(fall: Case, output, *, workspace: Path | None = None) -> CheckEnv:
    task = {}
    if (fall.dir / "input/task.json").is_file():
        task = json.loads((fall.dir / "input/task.json").read_text(encoding="utf-8"))
    return CheckEnv(output=output, ctx={"task": task}, case_dir=fall.dir, workspace=workspace,
                    test_command=fall.test_command, timeout=fall.timeout)


def _params(fall: Case, name: str) -> dict:
    return next((p for n, p in fall.checks if n == name), {})


def test_blueprint_test_author_referenz():
    """Der Referenztest ist gegen den Stub rot, gegen die Referenz grün und tötet die Mutanten."""
    fehler = []
    for fall in list_cases(_home("test_author")):
        task = json.loads((fall.dir / "input/task.json").read_text(encoding="utf-8"))
        referenzen = [p for p in (fall.dir / "expected").iterdir() if p.name.startswith("test")]
        if len(referenzen) != 1:
            fehler.append(f"{_name(fall)}: expected/ braucht genau einen Referenztest")
            continue
        output = {"test_file": task["test_file"],
                  "content": referenzen[0].read_text(encoding="utf-8"), "fr_ids": task["fr_ids"]}
        for name, params in fall.checks:
            if name == "json_schema":
                continue
            env = _env(fall, output)
            env.params = params
            if run_check(name, env).status != "pass":
                fehler.append(f"{_name(fall)} {name}")
    assert fehler == []


def test_blueprint_implementer_referenz(tmp_path):
    """Versteckte Tests: mit Referenzlösung grün, ohne rot."""
    fehler = []
    for i, fall in enumerate(list_cases(_home("implementer"))):
        for mit_referenz in (True, False):
            ws = tmp_path / f"{i}-{mit_referenz}"
            ws.mkdir()
            if (fall.dir / "input/repo").is_dir():
                overlay(fall.dir / "input/repo", ws)
            if mit_referenz:
                overlay(fall.dir / "reference", ws)
            status = run_check("hidden_tests_pass",
                               _env(fall, {"files": []}, workspace=ws)).status
            if status != ("pass" if mit_referenz else "fail"):
                fehler.append(f"{_name(fall)} {'mit' if mit_referenz else 'ohne'} Referenz")
    assert fehler == []


def test_blueprint_reviewer_und_supervisor_erwartungen():
    """Jeder Reviewer-/Supervisor-Fall trägt die Erwartung, die seine Checks brauchen."""
    fehler = []
    for rolle, datei in (("reviewer", "findings.json"), ("supervisor", "decision.json")):
        for fall in list_cases(_home(rolle)):
            namen = {n for n, _ in fall.checks}
            braucht = namen & {"seeded_bug_recall", "decision_matches"}
            pfad = fall.dir / "expected" / datei
            if braucht and not pfad.is_file():
                fehler.append(f"{_name(fall)}: expected/{datei} fehlt")
            elif braucht:
                json.loads(pfad.read_text(encoding="utf-8"))
    assert fehler == []
