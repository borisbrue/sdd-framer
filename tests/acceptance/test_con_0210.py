# AUTO-GENERATED from CON-0210 via sdd test generate — do not delete
"""TST-0239 – CON-0210: Verweise, Config-Aufräumen und sdd spec deprecate.

Spec: SPEC-0058 · Contract: CON-0210
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

REPO = Path(__file__).resolve().parents[2]
ENTFERNT = ("sub_agent.py", "local_agent.py", "autopilot.py", "dist_orchestrator.py",
            "review_pipeline.py", "llm_pool.py", "dag_command.py", "dag_event.py")
ALTE_BLOECKE = {
    "llm_pool": [{"name": "qwen", "provider": "openai-compat", "model": "qwen"}],
    "local_agent": {"enabled": True, "proxy_url": "http://localhost:4000"},
    "autopilot": {"max_fix_iterations": 3},
}


@pytest.fixture()
def projekt(tmp_path, monkeypatch):
    from sdd_cli.init import init_project

    init_project(tmp_path, title="Rückbau")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _cli(*args: str):
    from sdd_cli.main import cli

    return CliRunner().invoke(cli, list(args))


def _spec(root: Path, sid: str, status: str = "implemented", depends_on=(), contracts=()) -> Path:
    pfad = root / ".sdd/specs" / f"{sid}-probe.md"
    pfad.write_text(
        f"---\nid: {sid}\ntitle: Probe {sid}\ntype: feature\nstatus: {status}\nowner: T\n"
        f"version: 0.1.0\ndepends_on: [{', '.join(depends_on)}]\n"
        f"contracts: [{', '.join(contracts)}]\ntests: []\n---\n\n# Probe\n", encoding="utf-8")
    return pfad


def _contract(root: Path, cid: str, spec: str) -> Path:
    pfad = root / ".sdd/contracts/behavior" / f"{cid}-probe.md"
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(f"---\nid: {cid}\ntitle: Probe\ntype: behavior\nformat: markdown\n"
                    f"spec: {spec}\nversion: 0.1.0\nstatus: approved\n---\n\n# Probe\n",
                    encoding="utf-8")
    return pfad


def _fm(pfad: Path) -> dict:
    return yaml.safe_load(pfad.read_text(encoding="utf-8").split("---", 2)[1])


@pytest.mark.parametrize("args", [["distribute", "SPEC-0900"],
                                  ["distribute", "SPEC-0900", "--dry-run"]])
def test_tc01_abgeloester_befehl_verweist_auf_den_ersatz(projekt, monkeypatch, args):
    """Scenario Outline: Abgelöster Befehl verweist auf den Ersatz (CON-0210)."""
    import sdd_cli.llm.factory as factory

    def verboten(*a, **k):
        raise AssertionError(f"Verweis darf nichts ausführen: {a}")

    monkeypatch.setattr(subprocess, "run", verboten)
    monkeypatch.setattr(subprocess, "Popen", verboten)
    monkeypatch.setattr(factory, "get_completion_provider", verboten)
    monkeypatch.setattr(factory, "get_code_gen_provider", verboten)
    ergebnis = _cli(*args)
    assert ergebnis.exit_code == 1, ergebnis.output
    assert "sdd pipeline run" in ergebnis.output


def test_tc02_verweise_erscheinen_nicht_in_der_hilfe():
    """Scenario: Verweise erscheinen nicht in der Hilfe (CON-0210)."""
    ausgabe = _cli("--help").output
    assert not re.search(r"^\s+distribute\b", ausgabe, re.MULTILINE)


def test_tc03_entfernte_module_sind_weg():
    """Scenario: Entfernte Module sind weg (CON-0210)."""
    paket = REPO / "tool/sdd_cli"
    assert [m for m in ENTFERNT if (paket / m).exists()] == []
    setzen = re.compile(r"""(environ\[\s*["']ANTHROPIC_(API_KEY|BASE_URL)["']\s*\]\s*=|"""
                        r"""["']ANTHROPIC_(API_KEY|BASE_URL)["']\s*:|ANTHROPIC_BASE_URL)""")
    treffer = [f"{p.relative_to(REPO)}" for p in paket.rglob("*.py")
               if setzen.search(p.read_text(encoding="utf-8"))]
    assert treffer == []


def _mit_alten_bloecken(root: Path) -> str:
    pfad = root / ".sdd/config.yaml"
    text = pfad.read_text(encoding="utf-8").rstrip("\n") + "\n" + yaml.safe_dump(
        ALTE_BLOECKE, sort_keys=False)
    pfad.write_text(text, encoding="utf-8")
    return text


def test_tc04_config_aufraeumen_beim_upgrade(projekt):
    """Scenario: Config-Aufräumen beim Upgrade (CON-0210)."""
    vorher = _mit_alten_bloecken(projekt)
    ergebnis = _cli("upgrade")
    assert ergebnis.exit_code == 0, ergebnis.output
    nachher = (projekt / ".sdd/config.yaml").read_text(encoding="utf-8")
    daten = yaml.safe_load(nachher)
    for block in ALTE_BLOECKE:
        assert block not in daten
        assert f"# [SPEC-0058] {block}:" in nachher
        assert block in ergebnis.output
    alt = [z for z in vorher.splitlines() if z and not z.startswith((" ", "-"))
           and z.split(":")[0] not in ALTE_BLOECKE]
    assert [z for z in alt if z not in nachher.splitlines()] == []


def test_tc05_upgrade_ohne_alte_bloecke(projekt):
    """Scenario: Upgrade ohne alte Blöcke (CON-0210)."""
    pfad = projekt / ".sdd/config.yaml"
    _cli("upgrade")
    vorher = pfad.read_bytes()
    _cli("upgrade")
    assert pfad.read_bytes() == vorher
    assert b"[SPEC-0058]" not in vorher


def test_tc06_spec_wird_abgeloest(projekt):
    """Scenario: Spec wird abgelöst (CON-0210)."""
    pfad = _spec(projekt, "SPEC-0900")
    _spec(projekt, "SPEC-0901", status="draft")
    ergebnis = _cli("spec", "deprecate", "SPEC-0900", "--reason", "abgelöst",
                    "--replaced-by", "SPEC-0901")
    assert ergebnis.exit_code == 0, ergebnis.output
    fm = _fm(pfad)
    assert fm["status"] == "deprecated"
    assert fm["deprecated_reason"] == "abgelöst" and fm["replaced_by"] == "SPEC-0901"
    audit = (projekt / ".sdd/audit.log").read_text(encoding="utf-8")
    assert "SPEC-0900 implemented → deprecated" in audit


def test_tc07_deprecate_setzt_die_contracts_der_spec_ab(projekt):
    """Scenario: Deprecate setzt die Contracts der Spec ab (CON-0210)."""
    _spec(projekt, "SPEC-0900", contracts=("CON-0900", "CON-0901"))
    abgeloest, behalten = _contract(projekt, "CON-0900", "SPEC-0900"), \
        _contract(projekt, "CON-0901", "SPEC-0900")
    ergebnis = _cli("spec", "deprecate", "SPEC-0900", "--reason", "abgelöst",
                    "--keep", "CON-0901")
    assert ergebnis.exit_code == 0, ergebnis.output
    assert _fm(abgeloest)["status"] == "deprecated"
    assert _fm(behalten)["status"] == "approved"


def test_tc08_einzelner_contract_wird_abgeloest(projekt):
    """Scenario: Einzelner Contract wird abgelöst (CON-0210)."""
    _spec(projekt, "SPEC-0900", contracts=("CON-0901",))
    pfad = _contract(projekt, "CON-0901", "SPEC-0900")
    ergebnis = _cli("contract", "deprecate", "CON-0901", "--reason", "Schritt entfernt")
    assert ergebnis.exit_code == 0, ergebnis.output
    fm = _fm(pfad)
    assert fm["status"] == "deprecated" and fm["deprecated_reason"] == "Schritt entfernt"


def test_tc09_deprecate_mit_abhaengigen_specs(projekt):
    """Scenario: Deprecate mit abhängigen Specs (CON-0210)."""
    pfad = _spec(projekt, "SPEC-0900")
    _spec(projekt, "SPEC-0902", status="approved", depends_on=("SPEC-0900",))
    ergebnis = _cli("spec", "deprecate", "SPEC-0900", "--reason", "abgelöst")
    assert ergebnis.exit_code == 0, ergebnis.output
    assert _fm(pfad)["status"] == "deprecated"
    assert "SPEC-0902" in ergebnis.output


def test_tc10_deprecate_einer_unbekannten_spec(projekt):
    """Scenario: Deprecate einer unbekannten Spec (CON-0210)."""
    assert _cli("spec", "deprecate", "SPEC-0999", "--reason", "x").exit_code == 2
