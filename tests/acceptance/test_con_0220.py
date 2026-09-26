# AUTO-GENERATED from CON-0220 via sdd test generate — do not delete
"""TST-0249 – CON-0220: Ratchet, Übernahme und Skill sdd-role-tune.

Spec: SPEC-0055 · Contract: CON-0220
Reports werden synthetisch erzeugt (Schema CON-0218); kein LLM nötig.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

REPO = Path(__file__).resolve().parents[2]
SKILL_REPO = REPO / ".claude/commands/sdd-role-tune.md"
SKILL_BLUEPRINT = (REPO / "tool/sdd_cli/blueprint/templates/agents-md/providers/claude"
                   / "sdd-role-tune.md")


def _agg(mean, n=2):
    return {"cases": n, "mean": mean, "std": 0.0, "pass_at_1": 1.0, "pass_all": 1.0}


def _report(faelle: dict[str, tuple[float, bool]], *, holdout=0.5, schema="role-outputs#/$defs/"
            "decomposer", prompt_hash="sha256:" + "0" * 64, role_file=None) -> dict:
    sichtbar = [{"id": cid, "score": s, "std": 0.0, "passed": p, "pass_at_1": p, "pass_all": p,
                 "runs": []} for cid, (s, p) in faelle.items()]
    gesamt = sum(s for s, _ in faelle.values()) / len(faelle)
    daten = {"kind": "role-eval-report", "role": "decomposer", "role_version": "1.0.0",
             "prompt_hash": prompt_hash, "output_schema": schema,
             "profile": {"name": "lokal", "provider": "openai-compat", "model": "m"},
             "judge": None, "runs": 3, "sdd_version": "0", "created_at": "2026-09-26T10:00:00Z",
             "visible": sichtbar, "holdout": _agg(holdout, 3), "total": _agg(gesamt, 5),
             "include_holdout": False}
    if role_file:
        daten["role_file"] = str(role_file)
    return daten


def _cli(*args: str):
    from sdd_cli.main import cli

    return CliRunner().invoke(cli, list(args))


def _schreiben(pfad: Path, daten: dict) -> Path:
    pfad.write_text(json.dumps(daten), encoding="utf-8")
    return pfad


@pytest.fixture()
def projekt(tmp_path, monkeypatch):
    from sdd_cli.init import init_project

    init_project(tmp_path, title="Ratchet")
    monkeypatch.chdir(tmp_path)
    return tmp_path


BASE = {"DEC-001": (0.8, True), "DEC-002": (0.6, True), "DEC-003": (0.9, True)}


def test_tc01_verbesserung_wird_angenommen(tmp_path):
    """Scenario: Verbesserung wird angenommen (CON-0220)."""
    a = _schreiben(tmp_path / "a.json", _report(BASE))
    b = _schreiben(tmp_path / "b.json", _report({**BASE, "DEC-002": (0.9, True)}, holdout=0.6))
    ergebnis = _cli("role", "compare", str(a), str(b))
    assert ergebnis.exit_code == 0 and "accept" in ergebnis.output


def test_tc02_ratchet_verhindert_regression(tmp_path):
    """Scenario: Ratchet verhindert Regression (CON-0220)."""
    a = _schreiben(tmp_path / "a.json", _report(BASE))
    b = _schreiben(tmp_path / "b.json", _report(
        {"DEC-001": (1.0, True), "DEC-002": (1.0, True), "DEC-003": (0.45, False)}))
    ergebnis = _cli("role", "compare", str(a), str(b))
    assert ergebnis.exit_code == 1, ergebnis.output
    assert "reject" in ergebnis.output and "DEC-003" in ergebnis.output


def test_tc03_holdout_score_sinkt(tmp_path):
    """Scenario: Holdout-Score sinkt (CON-0220)."""
    a = _schreiben(tmp_path / "a.json", _report(BASE, holdout=0.7))
    b = _schreiben(tmp_path / "b.json", _report(BASE, holdout=0.6))
    ergebnis = _cli("role", "compare", "--json", str(a), str(b))
    assert ergebnis.exit_code == 1
    daten = json.loads(ergebnis.output)
    assert daten["result"] == "reject" and any("Holdout" in g for g in daten["reasons"])
    assert not any(g.startswith("DEC-") for g in daten["reasons"])


def test_tc04_geaendertes_ausgabeschema(tmp_path):
    """Scenario: Geändertes Ausgabeschema (CON-0220)."""
    a = _schreiben(tmp_path / "a.json", _report(BASE))
    b = _schreiben(tmp_path / "b.json", _report(BASE, schema="role-outputs#/$defs/anders"))
    ergebnis = _cli("role", "compare", str(a), str(b))
    assert ergebnis.exit_code == 1 and "output_schema" in ergebnis.output


def _kandidat(root: Path, zusatz: str = "\nZusatzregel: Nicht-Ziele nie als Task.\n") -> tuple[
        Path, str]:
    rolle = root / ".sdd/roles/decomposer.md"
    kandidat = root / ".sdd/roles/decomposer/candidate.md"
    kandidat.parent.mkdir(parents=True, exist_ok=True)
    kandidat.write_text(rolle.read_text(encoding="utf-8").rstrip() + "\n" + zusatz,
                        encoding="utf-8")
    from sdd_cli.pipeline.roles import split_frontmatter

    _, prompt = split_frontmatter(kandidat.read_text(encoding="utf-8"))
    return kandidat, "sha256:" + hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def test_tc05_uebernahme_einer_prompt_aenderung(projekt):
    """Scenario: Übernahme einer Prompt-Änderung (CON-0220)."""
    kandidat, prompt_hash = _kandidat(projekt)
    report = _schreiben(projekt / "k.json", _report(BASE, prompt_hash=prompt_hash,
                                                    role_file=kandidat))
    ergebnis = _cli("role", "accept", "decomposer", "--report", str(report))
    assert ergebnis.exit_code == 0, ergebnis.output
    rolle = (projekt / ".sdd/roles/decomposer.md").read_text(encoding="utf-8")
    kopf = yaml.safe_load(rolle.split("---", 2)[1])
    assert kopf["version"] == "1.1.0" and "Zusatzregel" in rolle
    basis = json.loads((projekt / ".sdd/roles/decomposer/baseline.json").read_text())
    assert basis["role_version"] == "1.1.0" and basis["cases"]["DEC-002"]["score"] == 0.6
    changelog = (projekt / ".sdd/roles/decomposer/CHANGELOG.md").read_text(encoding="utf-8")
    assert "1.0.0 → 1.1.0" in changelog and "→ 0.7666" in changelog


def test_tc06_uebernahme_ohne_accept(projekt):
    """Scenario: Übernahme ohne accept (CON-0220)."""
    kandidat, prompt_hash = _kandidat(projekt)
    _cli("role", "accept", "decomposer", "--report", str(_schreiben(
        projekt / "k.json", _report(BASE, prompt_hash=prompt_hash, role_file=kandidat))))
    rolle_vorher = (projekt / ".sdd/roles/decomposer.md").read_bytes()
    basis_vorher = (projekt / ".sdd/roles/decomposer/baseline.json").read_bytes()
    schlechter = _schreiben(projekt / "s.json", _report(
        {**BASE, "DEC-003": (0.2, False)}, prompt_hash=prompt_hash, role_file=kandidat))
    ergebnis = _cli("role", "accept", "decomposer", "--report", str(schlechter))
    assert ergebnis.exit_code == 1 and "DEC-003" in ergebnis.output
    assert (projekt / ".sdd/roles/decomposer.md").read_bytes() == rolle_vorher
    assert (projekt / ".sdd/roles/decomposer/baseline.json").read_bytes() == basis_vorher


def test_tc07_erzwungene_uebernahme(projekt):
    """Scenario: Erzwungene Übernahme (CON-0220)."""
    kandidat, prompt_hash = _kandidat(projekt)
    _cli("role", "accept", "decomposer", "--report", str(_schreiben(
        projekt / "k.json", _report(BASE, prompt_hash=prompt_hash, role_file=kandidat))))
    schlechter = _schreiben(projekt / "s.json", _report(
        {**BASE, "DEC-003": (0.2, False)}, prompt_hash=prompt_hash, role_file=kandidat))
    assert _cli("role", "accept", "decomposer", "--report", str(schlechter),
                "--force").exit_code == 2
    ergebnis = _cli("role", "accept", "decomposer", "--report", str(schlechter), "--force",
                    "--reason", "Rubrik ersetzt")
    assert ergebnis.exit_code == 0, ergebnis.output
    basis = json.loads((projekt / ".sdd/roles/decomposer/baseline.json").read_text())
    assert basis["forced"] == {"reason": "Rubrik ersetzt"} and basis["role_version"] == "1.1.1"
    assert "Rubrik ersetzt" in (projekt / ".sdd/roles/decomposer/CHANGELOG.md").read_text()


def test_kandidat_passt_nicht_zum_report(projekt):
    """INV-03: Prompt-Hash der Kandidatendatei ≠ Report → Exit 2, nichts geändert."""
    kandidat, _ = _kandidat(projekt)
    report = _schreiben(projekt / "k.json", _report(BASE, role_file=kandidat))
    vorher = (projekt / ".sdd/roles/decomposer.md").read_bytes()
    assert _cli("role", "accept", "decomposer", "--report", str(report)).exit_code == 2
    assert (projekt / ".sdd/roles/decomposer.md").read_bytes() == vorher


def test_ziel_ist_blueprint_im_sdd_framer_repo(tmp_path, monkeypatch):
    """INV-03: Liegt die geladene Rolle im Projekt (Blueprint im Repo), ist sie das Ziel."""
    from sdd_cli.pipeline.evals import cases

    blueprint = tmp_path / "tool/sdd_cli/blueprint"
    (blueprint / "roles").mkdir(parents=True)
    shutil.copy(cases.BLUEPRINT_ROLES / "decomposer.md", blueprint / "roles/decomposer.md")
    monkeypatch.setattr(cases, "BLUEPRINT_ROLES", blueprint / "roles")
    monkeypatch.setattr(cases, "BLUEPRINT", blueprint)
    monkeypatch.setattr("sdd_cli.pipeline.roles.BLUEPRINT_ROLES", blueprint / "roles")
    home = cases.role_home(tmp_path, "decomposer")
    assert home.role_file == (blueprint / "roles/decomposer.md").resolve()
    assert home.holdout_dir == blueprint / "holdout/roles/decomposer"
    fremd = cases.role_home(tmp_path / "anders", "decomposer")
    assert fremd.role_file == tmp_path / "anders/.sdd/roles/decomposer.md"


def test_tc08_skill_sdd_role_tune():
    """Scenario: Skill sdd-role-tune (CON-0220)."""
    text = SKILL_BLUEPRINT.read_text(encoding="utf-8")
    repo = SKILL_REPO.read_text(encoding="utf-8")
    assert repo.startswith("---\nscope: ") and repo.split("---\n", 2)[2] == text
    for teil in ("sdd role eval", "sdd role compare", "sdd role accept", "Hypothese",
                 "Zustimmung"):
        assert teil in text, teil
    assert "--include-holdout" in text and "holdout" in text
    assert "Ändere keine Fälle" in text and "keine Checks" in text
