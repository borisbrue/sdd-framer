# AUTO-GENERATED from CON-0229 via sdd test generate — do not delete
"""Contract-Tests für stack apply, extract, init --stack und Preset-Verweis (CON-0229).

Spec: SPEC-0057 · Contract: CON-0229
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys

import pytest
import yaml
from click.testing import CliRunner
from jsonschema import Draft202012Validator

from tests.support.quality_project import QualityProject
from tests.support.stack_project import (
    BLUEPRINT_STACKS,
    STACK_SCHEMA,
    config,
    demo_stack,
    git_init,
    make_stack_project,
    make_stacks_home,
    snapshot,
    use_reference_toolchain,
    write_stack,
)

SHA = re.compile(r"^sha256:[0-9a-f]{64}$")


@pytest.fixture()
def stacks_home(tmp_path, monkeypatch):
    return make_stacks_home(tmp_path, monkeypatch)


@pytest.fixture()
def sproject(tmp_path, monkeypatch, stacks_home):
    return make_stack_project(tmp_path, monkeypatch)


def _schema_errors(definition: str, instance: object) -> list[str]:
    schema = json.loads(STACK_SCHEMA.read_text(encoding="utf-8"))
    sub = {"$ref": f"#/$defs/{definition}", "$defs": schema["$defs"]}
    return [e.message for e in Draft202012Validator(sub).iter_errors(instance)]


def _init(tmp_path, monkeypatch, *args: str):
    from sdd_cli.main import cli

    ziel = tmp_path / "neu"
    ziel.mkdir()
    git_init(ziel)
    monkeypatch.chdir(tmp_path)
    return ziel, CliRunner().invoke(cli, ["init", "--path", str(ziel), *args])


def test_tc01_neues_projekt_mit_vorlage(tmp_path, monkeypatch, stacks_home):
    """Scenario: Neues Projekt mit Vorlage (CON-0229)."""
    ziel, ergebnis = _init(tmp_path, monkeypatch, "--name", "Demo", "--stack", "python-cli")
    assert ergebnis.exit_code == 0, ergebnis.output
    for rel in (".sdd/quality.yaml", ".sdd/architecture.yaml", "tests/test_skeleton.py",
                "app/__main__.py", "docs/adr/ADR-0001-schichten-domain-service-persistence-cli.md"):
        assert (ziel / rel).is_file(), rel
    eintraege = config(ziel)["stack"]
    assert _schema_errors("entry", eintraege[0]) == []
    assert [e["name"] for e in eintraege] == ["python-cli"]
    assert eintraege[0]["version"] == "1.0.0" and eintraege[0]["source"] == "blueprint"
    assert eintraege[0]["values"] == {"project_name": "Demo", "package_name": "app"}
    assert all(SHA.match(h) for h in eintraege[0]["files"].values())
    assert '"""Demo."""' in (ziel / "app/__init__.py").read_text()
    assert "{{" not in (ziel / "tests/test_skeleton.py").read_text()


def test_inv06_unbekannte_vorlage_vor_dem_anlegen(tmp_path, monkeypatch, stacks_home):
    ziel, ergebnis = _init(tmp_path, monkeypatch, "--name", "Demo", "--stack", "gibtsnicht")
    assert ergebnis.exit_code == 2
    assert not (ziel / ".sdd").exists()


def test_tc02_projekt_hat_die_vorlage_weiterentwickelt(sproject: QualityProject):
    """Scenario: Projekt hat die Vorlage weiterentwickelt (CON-0229)."""
    assert sproject.run("stack", "apply", "python-cli", "--yes").exit_code == 0
    pfad = sproject.root / ".sdd/quality.yaml"
    daten = yaml.safe_load(pfad.read_text())
    daten["probes"]["coverage"] = {"command": "true > {out}", "format": "sdd-metrics"}
    eigen = yaml.safe_dump(daten, sort_keys=False)
    pfad.write_text(eigen)
    ergebnis = sproject.run("stack", "apply", "python-cli", "--yes")
    assert ergebnis.exit_code == 0, ergebnis.output
    assert pfad.read_text() == eigen
    neu = sproject.root / ".sdd/quality.yaml.new"
    assert neu.is_file() and "coverage" not in neu.read_text()
    assert "@@" in ergebnis.output and "coverage" in ergebnis.output


def test_tc03_idempotent(sproject: QualityProject):
    """Scenario: Idempotent (CON-0229)."""
    assert sproject.run("stack", "apply", "python-cli", "--yes").exit_code == 0
    vorher = snapshot(sproject.root)
    ergebnis = sproject.run("stack", "apply", "python-cli", "--yes")
    assert ergebnis.exit_code == 0, ergebnis.output
    assert snapshot(sproject.root) == vorher


def test_inv01_eintrag_derselben_vorlage_wird_ersetzt(sproject: QualityProject, stacks_home):
    demo_stack(stacks_home)
    assert sproject.run("stack", "apply", "demo", "--yes").exit_code == 0
    assert sproject.run("stack", "apply", "python-cli", "--only", "quality", "--yes").exit_code == 0
    stack_yaml = stacks_home / "demo/stack.yaml"
    stack_yaml.write_text(stack_yaml.read_text().replace("1.0.0", "1.1.0"))
    assert sproject.run("stack", "apply", "demo", "--yes").exit_code == 0
    eintraege = config(sproject.root)["stack"]
    assert [(e["name"], e["version"]) for e in eintraege] == [("demo", "1.1.0"),
                                                             ("python-cli", "1.0.0")]


def test_memento_behaelt_kommentare_der_config(sproject: QualityProject):
    pfad = sproject.root / ".sdd/config.yaml"
    pfad.write_text("# Kopfkommentar bleibt\n" + pfad.read_text())
    assert sproject.run("stack", "apply", "python-cli", "--yes").exit_code == 0
    assert pfad.read_text().startswith("# Kopfkommentar bleibt\n")
    assert sproject.run("config", "validate").exit_code == 0


def test_tc04_agents_md_abschnitte(sproject: QualityProject):
    """Scenario: AGENTS.md-Abschnitte (CON-0229)."""
    agents = sproject.root / "AGENTS.md"
    eigen = agents.read_text() + "\n## Eigenes\n\nBleibt genau so.\n"
    agents.write_text(eigen)
    assert sproject.run("stack", "apply", "python-cli", "--yes").exit_code == 0
    text = agents.read_text()
    assert text.startswith(eigen)
    assert text.count("<!-- sdd-stack:python-cli:stack -->") == 1
    assert text.count("<!-- /sdd-stack:python-cli:stack -->") == 1
    teile = text.split("<!-- sdd-stack:python-cli:stack -->")
    geaendert = teile[0] + "<!-- sdd-stack:python-cli:stack -->\nALT\n" + \
        teile[1][teile[1].index("<!-- /sdd-stack"):]
    agents.write_text(geaendert)
    assert sproject.run("stack", "apply", "python-cli", "--yes").exit_code == 0
    assert agents.read_text() == text


def test_inv02_agents_md_fehlt(sproject: QualityProject, stacks_home):
    demo_stack(stacks_home)
    (sproject.root / "AGENTS.md").unlink()
    assert sproject.run("stack", "apply", "demo", "--yes").exit_code == 0
    assert (sproject.root / "AGENTS.md").read_text() == (
        "<!-- sdd-stack:demo:stack -->\n## Stack: demo\n\nPaket `kern`.\n"
        "<!-- /sdd-stack:demo:stack -->\n")


def test_tc05_nutzervorlage_mit_vorschau(sproject: QualityProject, stacks_home):
    """Scenario: Nutzervorlage mit Vorschau (CON-0229) – nicht interaktiv ohne --yes."""
    demo_stack(stacks_home)
    vorher = snapshot(sproject.root)
    ergebnis = sproject.run("stack", "apply", "demo")
    assert ergebnis.exit_code == 1
    assert "+ .sdd/quality.yaml" in ergebnis.output and "+ src/kern.txt" in ergebnis.output
    assert "Nicht angewendet" in ergebnis.output
    assert snapshot(sproject.root) == vorher


def test_tc05_interaktiv_abgelehnt(sproject: QualityProject, stacks_home, monkeypatch, capsys):
    from sdd_cli import stack_cli

    demo_stack(stacks_home)
    vorher = snapshot(sproject.root)
    monkeypatch.setattr(stack_cli.click, "confirm", lambda *a, **k: False)
    code = stack_cli.run_apply(sproject.root, "demo", sets={}, interactive=True)
    assert code == 1
    assert "+ src/kern.txt" in capsys.readouterr().out
    assert snapshot(sproject.root) == vorher


def test_dry_run_schreibt_nie(sproject: QualityProject):
    vorher = snapshot(sproject.root)
    ergebnis = sproject.run("stack", "apply", "python-cli", "--dry-run")
    assert ergebnis.exit_code == 0
    assert "+ .sdd/quality.yaml" in ergebnis.output
    assert snapshot(sproject.root) == vorher


def test_inv04_kein_befehl_beim_anwenden(sproject: QualityProject, stacks_home):
    demo_stack(stacks_home, requires=[
        {"tool": "fehlt", "version_command": "gibtsnicht-sdd --version",
         "install_hint": "apt install gibtsnicht-sdd"},
        {"tool": "marker", "version_command": "touch requires.ran"}],
        verify=[{"name": "v", "command": "touch verify.ran"}])
    ergebnis = sproject.run("stack", "apply", "demo", "--yes")
    assert ergebnis.exit_code == 0
    assert "Werkzeug fehlt: fehlt" in ergebnis.output and "apt install" in ergebnis.output
    assert not (sproject.root / "requires.ran").exists()
    assert not (sproject.root / "verify.ran").exists()


def test_tc06_fehlender_platzhalter(sproject: QualityProject, stacks_home):
    """Scenario: Fehlender Platzhalter (CON-0229)."""
    write_stack(stacks_home, "demo", {"a/{{modul}}.txt": "x"}, placeholders=[{"name": "modul"}])
    vorher = snapshot(sproject.root)
    ergebnis = sproject.run("stack", "apply", "demo", "--yes")
    assert ergebnis.exit_code == 2 and "modul" in ergebnis.output
    assert snapshot(sproject.root) == vorher
    ergebnis = sproject.run("stack", "apply", "demo", "--yes", "--set", "modul=kern")
    assert ergebnis.exit_code == 0
    assert (sproject.root / "a/kern.txt").is_file()


def test_inv03_reihenfolge_der_werte(sproject: QualityProject, stacks_home):
    demo_stack(stacks_home)
    assert sproject.run("stack", "apply", "demo", "--yes", "--set", "package_name=erst").exit_code == 0
    assert sproject.run("stack", "apply", "demo", "--yes").exit_code == 0
    werte = config(sproject.root)["stack"][0]["values"]
    assert werte == {"project_name": "Qualitaetsprojekt", "package_name": "erst"}
    assert (sproject.root / "src/erst.txt").read_text() == "Paket erst von Qualitaetsprojekt\n"


def test_tc07_nur_qualitaet(sproject: QualityProject):
    """Scenario: Nur Qualität (CON-0229)."""
    vorher = snapshot(sproject.root)
    ergebnis = sproject.run("stack", "apply", "python-cli", "--only", "quality", "--yes")
    assert ergebnis.exit_code == 0, ergebnis.output
    nachher = snapshot(sproject.root)
    geaendert = {rel for rel in nachher if nachher[rel] != vorher.get(rel)}
    assert geaendert - {".sdd/config.yaml"} == {
        ".sdd/quality.yaml", ".sdd/quality/extract_deps.py", ".sdd/quality/lizard_to_metrics.py",
        ".sdd/quality/mypy_to_sarif.py", ".sdd/quality/sdd_fr_marker.py"}
    assert set(config(sproject.root)["stack"][0]["files"]) == geaendert - {".sdd/config.yaml"}


def test_tc08_vorlage_aus_dem_projekt_extrahieren(sproject: QualityProject, tmp_path,
                                                   monkeypatch):
    """Scenario: Vorlage aus dem Projekt extrahieren (CON-0229)."""
    from tests.support.stack_project import make_stack_project as neues_projekt

    assert sproject.run("stack", "apply", "python-cli", "--yes",
                        "--set", "package_name=rechner").exit_code == 0
    pfad = sproject.root / ".sdd/quality.yaml"
    daten = yaml.safe_load(pfad.read_text())
    daten["probes"]["eigen"] = {"command": "true > {out}", "format": "sdd-metrics"}
    pfad.write_text(yaml.safe_dump(daten, sort_keys=False))
    ergebnis = sproject.run("stack", "extract", "mein-stack", "--to", "project")
    assert ergebnis.exit_code == 0, ergebnis.output
    ordner = sproject.root / ".sdd/stacks/mein-stack"
    stack = yaml.safe_load((ordner / "stack.yaml").read_text())
    assert _schema_errors("stack", stack) == []
    assert stack["version"] == "0.1.0"
    assert {p["name"] for p in stack["placeholders"]} == {"project_name", "package_name"}
    assert (ordner / "files/{{package_name}}/__main__.py").is_file()
    assert "eigen" in (ordner / "files/.sdd/quality.yaml").read_text()
    assert (ordner / "agents-md/stack.md").is_file()
    assert "results.append" in (ordner / "files/.sdd/quality/mypy_to_sarif.py").read_text()
    assert sproject.run("stack", "extract", "mein-stack", "--to", "project").exit_code == 2

    anderes = neues_projekt(tmp_path / "zweites", monkeypatch)
    shutil.copytree(ordner, anderes.root / ".sdd/stacks/mein-stack")
    ergebnis = anderes.run("stack", "apply", "mein-stack", "--yes", "--set", "package_name=zwei")
    assert ergebnis.exit_code == 0, ergebnis.output
    assert (anderes.root / "zwei/__main__.py").is_file()
    assert "eigen" in (anderes.root / ".sdd/quality.yaml").read_text()


def test_tc09_preset_verweis(sproject: QualityProject):
    """Scenario: Preset-Verweis (CON-0229)."""
    vorher = snapshot(sproject.root)
    ergebnis = sproject.run("quality", "init", "--preset", "python")
    assert ergebnis.exit_code == 1
    assert "sdd stack apply python-cli --only quality" in ergebnis.output
    assert snapshot(sproject.root) == vorher
    assert not (BLUEPRINT_STACKS.parent / "presets").exists()


@pytest.mark.parametrize("name,module", [("python-cli", ()), ("python-fastapi",
                                                             ("fastapi", "httpx"))])
def test_inv09_blueprint_vorlagen_sind_gruen(tmp_path, monkeypatch, stacks_home, name, module):
    """INV-09: ein frisch initialisiertes Projekt hat einen grünen, FR-markierten Skeleton-Test."""
    for m in module:
        pytest.importorskip(m)
    use_reference_toolchain(monkeypatch)
    ziel, ergebnis = _init(tmp_path, monkeypatch, "--name", "Demo", "--stack", name)
    assert ergebnis.exit_code == 0, ergebnis.output
    junit = tmp_path / "junit.xml"
    env = {**os.environ, "PYTHONPATH": ".sdd/quality"}
    proc = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "sdd_fr_marker",
                           "-p", "no:cacheprovider", f"--junitxml={junit}"],
                          cwd=ziel, capture_output=True, text=True, env=env, timeout=300)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert '<property name="fr" value="FR-01"' in junit.read_text()
