# AUTO-GENERATED from CON-0215 via sdd test generate — do not delete
"""TST-0244 – CON-0215: Verweise, Entfernen, Config-Migration und ARCH-05.

Spec: SPEC-0062 · Contract: CON-0215
Verweise und Migration laufen in einem Projekt aus `sdd init`; ARCH-05 wird auf einer Kopie des
Repos mit eingebautem Verstoß und auf dem Repo-Stand geprüft.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

REPO = Path(__file__).resolve().parents[2]
PAKET = REPO / "tool/sdd_cli"
LOCAL_LLM = {"provider": "openai-compat", "model": "m", "base_url": "http://h/v1",
             "api_key": "k", "enable_thinking": False}
KOPIE_IGNORIEREN = shutil.ignore_patterns("node_modules", "dist", "__pycache__", ".venv",
                                          "*.egg-info", "holdout", "runs", "evaluations.db")


@pytest.fixture()
def projekt(tmp_path, monkeypatch):
    from sdd_cli.init import init_project

    init_project(tmp_path, title="Ablösung")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _cli(*args: str):
    from sdd_cli.main import cli

    return CliRunner().invoke(cli, list(args))


def _config(root: Path) -> Path:
    return root / ".sdd/config.yaml"


def _mit(root: Path, *, routing: dict | None = None, local_llm: dict | None = None,
         extra_llm: dict | None = None) -> None:
    pfad = _config(root)
    daten = yaml.safe_load(pfad.read_text(encoding="utf-8"))
    llm = daten.setdefault("llm", {})
    if local_llm is not None:
        llm["local_llm"] = local_llm
    llm.update(extra_llm or {})
    if routing is not None:
        daten["task_routing"] = routing
    pfad.write_text(yaml.safe_dump(daten, sort_keys=False, allow_unicode=True), encoding="utf-8")


def _stand(root: Path) -> dict[str, str]:
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file()}


@pytest.mark.parametrize("aufruf, ersatz", [
    (["task-route", "SPEC-0900", "T01"], "sdd pipeline run SPEC-0900 --task T01"),
    (["task-exec", "SPEC-0900", "T01"], "sdd pipeline run SPEC-0900 --task T01"),
    (["task-loop", "SPEC-0900"], "sdd pipeline run SPEC-0900"),
    (["orchestrate", "SPEC-0900"], "sdd pipeline run SPEC-0900 --auto"),
    (["orchestrate", "--spec", "SPEC-0900", "--max-retries", "3"],
     "sdd pipeline run SPEC-0900 --auto"),
    (["task-exec", "SPEC-0900", "T01", "--iteration", "2", "--error-context", "x"],
     "sdd pipeline run SPEC-0900 --task T01"),
])
def test_tc01_abgeloester_befehl_verweist_auf_die_pipeline(projekt, monkeypatch, aufruf, ersatz):
    """Scenario Outline: Abgelöster Befehl verweist auf die Pipeline (CON-0215)."""
    import sdd_cli.llm.factory as factory

    def verboten(*a, **k):
        raise AssertionError(f"Verweis darf nichts ausführen: {a}")

    monkeypatch.setattr(subprocess, "run", verboten)
    monkeypatch.setattr(subprocess, "Popen", verboten)
    monkeypatch.setattr(factory, "get_completion_provider", verboten)
    monkeypatch.setattr(factory, "get_role_provider", verboten)
    vorher = _stand(projekt)
    ergebnis = _cli(*aufruf)
    assert ergebnis.exit_code == 1, ergebnis.output
    assert ersatz in " ".join(ergebnis.output.split())
    assert _stand(projekt) == vorher


def test_tc02_verweise_erscheinen_nicht_in_der_hilfe():
    """Scenario: Verweise erscheinen nicht in der Hilfe (CON-0215)."""
    ausgabe = _cli("--help").output
    for befehl in ("task-route", "task-exec", "task-loop", "orchestrate"):
        assert not re.search(rf"^\s+{befehl}\b", ausgabe, re.MULTILINE), befehl


def test_tc03_entfernte_module_sind_weg():
    """Scenario: Entfernte Module sind weg (CON-0215)."""
    assert not (PAKET / "task_routing").exists()
    assert not (PAKET / "orchestrator.py").exists()
    assert not (PAKET / "llm_probe.py").exists()
    symbole = re.compile(r"\b(CodeGenProvider|CodeGenResult|RecordingCodeGenProvider|"
                         r"ClaudeCliCodeGenProvider|OpenAICompatCodeGenProvider|"
                         r"get_code_gen_provider)\b")
    treffer = [str(p.relative_to(REPO)) for p in PAKET.rglob("*.py")
               if symbole.search(p.read_text(encoding="utf-8"))]
    assert treffer == []


def test_tc04_config_migration_mit_routing(projekt):
    """Scenario: Config-Migration mit Routing (CON-0215)."""
    _mit(projekt, routing={"enabled": True, "complexity_threshold": 50, "max_retries": 3},
         local_llm=LOCAL_LLM)
    vorher = yaml.safe_load(_config(projekt).read_text(encoding="utf-8"))
    ergebnis = _cli("upgrade")
    assert ergebnis.exit_code == 0, ergebnis.output
    text = _config(projekt).read_text(encoding="utf-8")
    daten = yaml.safe_load(text)
    assert daten["llm"]["profiles"]["lokal"] == {"provider": "openai-compat", "model": "m",
                                                 "base_url": "http://h/v1", "api_key": "k",
                                                 "thinking": False}
    assert daten["llm"]["roles"]["implementer"]["by_complexity"] == {"low": "lokal",
                                                                     "medium": "lokal"}
    assert "task_routing" not in daten and "local_llm" not in daten["llm"]
    assert "# [SPEC-0062] task_routing:" in text
    assert "# [SPEC-0062]   local_llm:" in text
    ausgabe = " ".join(ergebnis.output.split())
    assert "llm.profiles.lokal" in ausgabe and "by_complexity" in ausgabe
    assert "task_routing auskommentiert" in ausgabe and "llm.local_llm auskommentiert" in ausgabe
    # llm.orchestrator und der Abschnitt orchestrator bleiben (INV-06).
    assert daten["orchestrator"] == vorher["orchestrator"]
    assert daten["llm"]["orchestrator"] == vorher["llm"]["orchestrator"]


def test_tc05_routing_war_abgeschaltet(projekt):
    """Scenario: Routing war abgeschaltet (CON-0215)."""
    _mit(projekt, routing={"enabled": False, "complexity_threshold": 80}, local_llm=LOCAL_LLM)
    assert _cli("upgrade").exit_code == 0
    daten = yaml.safe_load(_config(projekt).read_text(encoding="utf-8"))
    assert "lokal" in daten["llm"]["profiles"]
    assert "by_complexity" not in (daten["llm"].get("roles") or {}).get("implementer", {})
    assert "task_routing" not in daten and "local_llm" not in daten["llm"]


def test_tc06_routing_ohne_lokales_modell(projekt):
    """Scenario: Routing ohne lokales Modell (CON-0215)."""
    _mit(projekt, routing={"enabled": True})
    ergebnis = _cli("upgrade")
    daten = yaml.safe_load(_config(projekt).read_text(encoding="utf-8"))
    assert "task_routing" not in daten
    assert "profiles" not in daten["llm"]
    assert "ohne llm.local_llm" in " ".join(ergebnis.output.split())


def test_tc07_bestehende_rollen_werden_nicht_ueberschrieben(projekt):
    """Scenario: Bestehende Rollen werden nicht überschrieben (CON-0215)."""
    _mit(projekt, routing={"enabled": True}, local_llm=LOCAL_LLM,
         extra_llm={"profiles": {"lokal": {"provider": "claude-cli"}}})
    vorher = _config(projekt).read_bytes()
    ergebnis = _cli("upgrade")
    assert _config(projekt).read_bytes() == vorher
    assert b"[SPEC-0062]" not in vorher
    assert "llm.profiles.lokal existiert bereits" in " ".join(ergebnis.output.split())


def test_tc08_migration_ist_idempotent(projekt):
    """Scenario: Migration ist idempotent (CON-0215)."""
    _mit(projekt, routing={"enabled": True, "complexity_threshold": 30}, local_llm=LOCAL_LLM)
    _cli("upgrade")
    vorher = _config(projekt).read_bytes()
    ergebnis = _cli("upgrade")
    assert _config(projekt).read_bytes() == vorher
    assert "SPEC-0062" not in ergebnis.output


def _status(pfad: Path) -> str:
    return yaml.safe_load(pfad.read_text(encoding="utf-8").split("---", 2)[1])["status"]


def test_tc09_abgeloeste_artefakte():
    """Scenario: Abgelöste Artefakte (CON-0215)."""
    [spec] = (REPO / ".sdd/specs").glob("SPEC-0045-*.md")
    fm = yaml.safe_load(spec.read_text(encoding="utf-8").split("---", 2)[1])
    assert fm["status"] == "deprecated" and "SPEC-0061" in str(fm)
    for cid in ("CON-0171", "CON-0172", "CON-0173", "CON-0174", "CON-0012", "CON-0024",
                "CON-0033", "CON-0063", "CON-0113", "CON-0164"):
        [datei] = (REPO / ".sdd/contracts").rglob(f"{cid}-*.md")
        assert _status(datei) == "deprecated", cid


@pytest.fixture()
def kopie(tmp_path):
    shutil.copytree(PAKET, tmp_path / "tool/sdd_cli", ignore=KOPIE_IGNORIEREN)
    (tmp_path / ".sdd").mkdir()
    for name in ("architecture.yaml", "quality.yaml", "config.yaml"):
        shutil.copy(REPO / ".sdd" / name, tmp_path / ".sdd" / name)
    shutil.copytree(REPO / ".sdd/quality", tmp_path / ".sdd/quality", ignore=KOPIE_IGNORIEREN)
    shutil.copytree(REPO / "docs/adr", tmp_path / "docs/adr")
    return tmp_path


def _arch_check(root: Path, monkeypatch) -> tuple[int, str]:
    monkeypatch.chdir(root)
    ergebnis = _cli("arch", "check")
    return ergebnis.exit_code, ergebnis.output


def test_tc10_arch_05_schuetzt_die_interna_der_pipeline(kopie, monkeypatch):
    """Scenario: ARCH-05 schützt die Interna der Pipeline (CON-0215)."""
    neu = kopie / "tool/sdd_cli/web/api/routes/new.py"
    neu.write_text("from sdd_cli.pipeline import mediator\n", encoding="utf-8")
    exit_code, ausgabe = _arch_check(kopie, monkeypatch)
    assert exit_code == 1, ausgabe
    zeile = " ".join(next(z for z in ausgabe.splitlines() if "routes/new.py" in z).split())
    assert "ARCH-05" in zeile and "ADR-0006" in zeile


def test_tc11_repository_ist_regelkonform(monkeypatch):
    """Scenario: Repository ist regelkonform (CON-0215)."""
    exit_code, ausgabe = _arch_check(REPO, monkeypatch)
    assert exit_code == 0, ausgabe
    assert "ARCH-05" not in ausgabe
    baseline = json.loads((REPO / ".sdd/quality/arch-baseline.json").read_text(encoding="utf-8"))
    assert not [e for e in baseline["entries"] if e.get("fixed_by") in ("SPEC-0061", "SPEC-0062")]
    arch = yaml.safe_load((REPO / ".sdd/architecture.yaml").read_text(encoding="utf-8"))
    assert "pipeline" in arch["layers"]
    assert any(r["id"] == "ARCH-05" and r["adr"] == "ADR-0006" for r in arch["rules"])
