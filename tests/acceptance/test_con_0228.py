# AUTO-GENERATED from CON-0228 via sdd test generate — do not delete
"""Contract-Tests für stack list, show, verify und diff (CON-0228).

Spec: SPEC-0057 · Contract: CON-0228
"""
from __future__ import annotations

import pytest

from tests.support.quality_project import QualityProject
from tests.support.stack_project import (
    copy_blueprint,
    demo_stack,
    make_stack_project,
    make_stacks_home,
    snapshot,
    use_reference_toolchain,
    write_stack,
)


@pytest.fixture()
def stacks_home(tmp_path, monkeypatch):
    return make_stacks_home(tmp_path, monkeypatch)


@pytest.fixture()
def sproject(tmp_path, monkeypatch, stacks_home):
    return make_stack_project(tmp_path, monkeypatch)


@pytest.fixture()
def reference_toolchain(monkeypatch):
    use_reference_toolchain(monkeypatch)


def _zeilen(ausgabe: str) -> list[str]:
    return [z.strip() for z in ausgabe.splitlines() if z.strip()]


def test_tc01_vorlagen_aus_allen_quellen(sproject: QualityProject, stacks_home):
    """Scenario: Vorlagen aus allen Quellen (CON-0228)."""
    copy_blueprint("python-cli", stacks_home)
    write_stack(sproject.root / ".sdd/stacks", "eigen", {"a.txt": "x"})
    vorher = snapshot(sproject.root)
    ergebnis = sproject.run("stack", "list")
    assert ergebnis.exit_code == 0, ergebnis.output
    zeilen = _zeilen(ergebnis.output)
    nutzer = [z for z in zeilen if z.startswith("python-cli") and "(Nutzer)" in z]
    blueprint = [z for z in zeilen if z.startswith("python-cli") and "(Blueprint)" in z]
    assert nutzer and "verdeckt" not in nutzer[0]
    assert blueprint and "verdeckt" in blueprint[0]
    assert any(z.startswith("eigen") and "(Projekt)" in z for z in zeilen)
    assert any(z.startswith("python-fastapi") and "verdeckt" not in z for z in zeilen)
    assert snapshot(sproject.root) == vorher


def test_list_meldet_ungueltige_vorlage(sproject: QualityProject, stacks_home):
    write_stack(stacks_home, "kaputt", {"a.txt": "{{fehlt}}"})
    ergebnis = sproject.run("stack", "list")
    assert ergebnis.exit_code == 0
    assert any(z.startswith("✗ kaputt") and "fehlt" in z for z in _zeilen(ergebnis.output))


def test_tc02_vorlage_anzeigen(sproject: QualityProject):
    """Scenario: Vorlage anzeigen (CON-0228)."""
    ergebnis = sproject.run("stack", "show", "python-fastapi")
    assert ergebnis.exit_code == 0, ergebnis.output
    for erwartet in ("1.0.0", "Blueprint", "Sprachen: python", "fastapi", "httpx",
                     "{{package_name}} = app", "tests/test_skeleton.py", ".sdd/quality.yaml",
                     "AGENTS.md: Abschnitt stack"):
        assert erwartet in ergebnis.output, erwartet


def test_tc03_unbekannte_vorlage(sproject: QualityProject):
    """Scenario: Unbekannte Vorlage (CON-0228)."""
    ergebnis = sproject.run("stack", "show", "gibtsnicht")
    assert ergebnis.exit_code == 2
    assert "gibtsnicht" in ergebnis.output


@pytest.mark.usefixtures("reference_toolchain")
def test_tc04_verify_gruen(sproject: QualityProject):
    """Scenario: Verify grün (CON-0228) – Referenz-Toolchain, echte Test-Sonde."""
    assert sproject.run("stack", "apply", "python-cli", "--yes").exit_code == 0
    ergebnis = sproject.run("stack", "verify")
    assert ergebnis.exit_code == 0, ergebnis.output
    zeilen = _zeilen(ergebnis.output)
    for pflicht in ("Werkzeug python3", "Werkzeug pytest", "Sonde tests",
                    "FR-markierter Test", "arch check"):
        assert any(z.startswith(f"✓ {pflicht}") for z in zeilen), pflicht


def test_tc05_verify_mit_fehlendem_werkzeug(sproject: QualityProject, stacks_home):
    """Scenario: Verify mit fehlendem Werkzeug (CON-0228)."""
    demo_stack(stacks_home, requires=[
        {"tool": "gibtsnicht-sdd", "version_command": "gibtsnicht-sdd --version",
         "install_hint": "apt install gibtsnicht-sdd"},
        {"tool": "optional-sdd", "version_command": "optional-sdd --version", "optional": True}])
    assert sproject.run("stack", "apply", "demo", "--yes").exit_code == 0
    ergebnis = sproject.run("stack", "verify")
    assert ergebnis.exit_code == 1
    zeilen = _zeilen(ergebnis.output)
    assert any(z.startswith("✗ Werkzeug gibtsnicht-sdd") and "apt install gibtsnicht-sdd" in z
               for z in zeilen)
    assert any(z.startswith("⚠ Werkzeug optional-sdd") for z in zeilen)
    assert any(z.startswith("✓ FR-markierter Test") for z in zeilen)


def test_nur_optionale_luecken_ergeben_exit_0(sproject: QualityProject, stacks_home):
    demo_stack(stacks_home, requires=[
        {"tool": "optional-sdd", "version_command": "optional-sdd --version", "optional": True}],
        verify=[{"name": "hinweis", "command": "exit 3", "optional": True},
                {"name": "paket", "command": "test -f src/{{package_name}}.txt"}])
    assert sproject.run("stack", "apply", "demo", "--yes").exit_code == 0
    ergebnis = sproject.run("stack", "verify")
    assert ergebnis.exit_code == 0, ergebnis.output
    zeilen = _zeilen(ergebnis.output)
    assert any(z.startswith("⚠ demo: hinweis") for z in zeilen)
    assert any(z.startswith("✓ demo: paket") for z in zeilen)


def test_pflicht_pruefpunkt_scheitert(sproject: QualityProject, stacks_home):
    demo_stack(stacks_home, verify=[{"name": "pflicht", "command": "exit 4"}])
    assert sproject.run("stack", "apply", "demo", "--yes").exit_code == 0
    ergebnis = sproject.run("stack", "verify")
    assert ergebnis.exit_code == 1
    assert any(z.startswith("✗ demo: pflicht") for z in _zeilen(ergebnis.output))


def test_tc06_verify_ohne_fr_markierten_test(sproject: QualityProject, stacks_home):
    """Scenario: Verify ohne FR-markierten Test (CON-0228)."""
    demo_stack(stacks_home, fr=False)
    assert sproject.run("stack", "apply", "demo", "--yes").exit_code == 0
    ergebnis = sproject.run("stack", "verify")
    assert ergebnis.exit_code == 1
    assert any(z.startswith("✗ FR-markierter Test") for z in _zeilen(ergebnis.output))


def test_verify_ohne_angewendete_vorlage(sproject: QualityProject):
    ergebnis = sproject.run("stack", "verify")
    assert ergebnis.exit_code == 2 and "Keine Vorlage" in ergebnis.output


def test_verify_fuehrt_nur_deklariertes_aus(sproject: QualityProject, stacks_home):
    """INV-03: kein Befehl außer requires, Sonden, arch check und verify."""
    demo_stack(stacks_home, requires=[
        {"tool": "marker", "version_command": "touch requires.ran; echo 1.0"}],
        verify=[{"name": "v", "command": "touch verify.ran"}])
    assert sproject.run("stack", "apply", "demo", "--yes").exit_code == 0
    vorher = set(snapshot(sproject.root))
    assert sproject.run("stack", "verify").exit_code == 0
    neu = set(snapshot(sproject.root)) - vorher
    assert neu == {"requires.ran", "verify.ran"}


def test_tc07_diff_nach_weiterentwicklung(sproject: QualityProject):
    """Scenario: Diff nach Weiterentwicklung (CON-0228)."""
    assert sproject.run("stack", "apply", "python-cli", "--yes").exit_code == 0
    quality = sproject.root / ".sdd/quality.yaml"
    quality.write_text(quality.read_text() + "# eigene Anpassung\n")
    (sproject.root / "pytest.ini").unlink()
    vorlage = copy_blueprint("python-cli", sproject.root / ".sdd/stacks")
    skeleton = vorlage / "files/tests/test_skeleton.py"
    skeleton.write_text(skeleton.read_text() + "\n# neuer Stand der Vorlage\n")
    (vorlage / "files/NEU.md").write_text("neu\n")
    vorher = snapshot(sproject.root)
    ergebnis = sproject.run("stack", "diff")
    assert ergebnis.exit_code == 0, ergebnis.output
    abschnitte: dict[str, list[str]] = {}
    aktuell = ""
    for zeile in ergebnis.output.splitlines():
        if zeile.startswith("  ") and not zeile.startswith("    "):
            aktuell = zeile.strip().rstrip(":")
        elif zeile.startswith("    "):
            abschnitte.setdefault(aktuell, []).append(zeile.strip())
    assert abschnitte["vom Projekt geändert"] == [".sdd/quality.yaml"]
    assert sorted(abschnitte["in der Vorlage neu oder geändert"]) == [
        "NEU.md", "tests/test_skeleton.py"]
    assert abschnitte["im Projekt entfernt"] == ["pytest.ini"]
    assert snapshot(sproject.root) == vorher


def test_diff_beides_und_unveraendert(sproject: QualityProject, stacks_home):
    from sdd_cli.stacks.verify import BOTH, UNCHANGED, diff
    from tests.support.stack_project import config

    ordner = demo_stack(stacks_home)
    assert sproject.run("stack", "apply", "demo", "--yes").exit_code == 0
    (sproject.root / "src/kern.txt").write_text("Projektstand\n")
    (ordner / "files/src/{{package_name}}.txt").write_text("Vorlagenstand\n")
    ergebnis = diff(sproject.root, config(sproject.root))["demo"]
    assert ergebnis["src/kern.txt"] == BOTH
    assert ergebnis[".sdd/quality.yaml"] == UNCHANGED


def test_diff_ohne_angewendete_vorlage(sproject: QualityProject):
    ergebnis = sproject.run("stack", "diff")
    assert ergebnis.exit_code == 0 and "Keine Vorlage angewendet" in ergebnis.output
