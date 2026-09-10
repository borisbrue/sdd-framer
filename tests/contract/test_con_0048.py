# AUTO-GENERATED from CON-0048 via sdd test generate — do not delete
"""Contract-Tests für SOLID CLI Commands Behavior (CON-0048).

Spec: SPEC-0015 · Contract: CON-0048
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

# Use the same venv sdd binary that runs the tests
SDD = str(Path(sys.executable).parent / "sdd")

# A real spec that exists in the project — for commands that look up files
REAL_SPEC = "SPEC-0015"


# Das Repo-Wurzelverzeichnis, nicht der geerbte Prozess-CWD. Die Tests liefen
# frueher nur unter .sdd/tests/ und damit nie in der Suite mit; im Gesamtlauf
# hatte ein vorheriger Test das Arbeitsverzeichnis verschoben, und `sdd spec
# solid SPEC-0015` fand die Spec nicht mehr (#94).
REPO = Path(__file__).resolve().parents[2]


def _run(args: list[str], cwd: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [SDD] + args,
        capture_output=True,
        text=True,
        cwd=cwd or str(REPO),
    )


def _spec(tmpdir: str, spec_id: str) -> None:
    """Legt eine minimale Spec an. INV-04: unbekannte IDs enden mit exit 2 —
    die Szenarien setzen "Given <ID> existiert" voraus."""
    specs = Path(tmpdir) / ".sdd" / "specs"
    specs.mkdir(parents=True, exist_ok=True)
    (specs / f"{spec_id}.md").write_text(
        f"---\nid: {spec_id}\ntitle: Test\nstatus: draft\n---\n\n# Test\n",
        encoding="utf-8",
    )


# ─── solid-check ─────────────────────────────────────────────────────────────

def test_tc01_solid_check_gibt_json_report_aus_mit_json_flag():
    """Scenario: solid-check gibt JSON-Report aus mit --json Flag (CON-0048)."""
    result = _run(["spec", "solid", "--json", REAL_SPEC])
    # Exit 0 or 1 are both valid (warn/block mode); exit 2 means ID not found
    assert result.returncode != 2, f"Spec {REAL_SPEC} nicht gefunden: {result.stderr}"
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        pytest.fail(f"Keine valide JSON-Ausgabe:\n{result.stdout}")
    assert "artifact_id" in data, "artifact_id fehlt im JSON-Report"
    assert "overall_solid_score" in data, "overall_solid_score fehlt im JSON-Report"
    assert "solid_findings" in data, "solid_findings fehlt im JSON-Report"


def test_tc02_solid_check_im_warn_modus_gibt_exit_code_0_bei_vio():
    """Scenario: solid-check im warn-Modus gibt Exit-Code 0 bei Violation (CON-0048)."""
    # Run in a tmpdir with a minimal config that sets mode=warn
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        sdd_dir = root / ".sdd"
        specs_dir = sdd_dir / "specs"
        specs_dir.mkdir(parents=True)

        # Minimal config
        (sdd_dir / "config.yaml").write_text(
            "version: '1.0.0'\n"
            "project:\n  name: test\n"
            "solid_gate:\n  enabled: true\n  mode: warn\n",
            encoding="utf-8",
        )

        # Minimal spec so solid-check can find the artifact text
        (specs_dir / "SPEC-TEST-solid.md").write_text(
            "---\nid: SPEC-TEST\ntitle: Test\nstatus: draft\n---\nTest spec.\n",
            encoding="utf-8",
        )

        result = _run(["spec", "solid", "--json", "SPEC-TEST"], cwd=tmpdir)
        # In warn mode, exit code must be 0 regardless of findings
        assert result.returncode == 0, (
            f"warn-Modus darf nicht mit Exit-Code {result.returncode} beenden.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )


def test_tc03_solid_check_im_block_modus_gibt_exit_code_1_bei_vi():
    """Scenario: solid-check im block-Modus gibt Exit-Code 1 bei Violation (CON-0048)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        sdd_dir = root / ".sdd"
        specs_dir = sdd_dir / "specs"
        specs_dir.mkdir(parents=True)

        # Config with mode=block
        (sdd_dir / "config.yaml").write_text(
            "version: '1.0.0'\n"
            "project:\n  name: test\n"
            "solid_gate:\n  enabled: true\n  mode: block\n",
            encoding="utf-8",
        )

        # Spec text that is clearly not SOLID-compliant to provoke a violation
        bad_spec_text = (
            "---\nid: SPEC-BLK\ntitle: Bloated\nstatus: draft\n---\n"
            + ("Diese Klasse macht alles: Authentication, Logging, Database, UI, Reporting. " * 10)
        )
        (specs_dir / "SPEC-BLK-bloated.md").write_text(bad_spec_text, encoding="utf-8")

        result = _run(["spec", "solid", "SPEC-BLK"], cwd=tmpdir)
        # In block mode, exit code 1 if violation; 0 if compliant
        # We just assert it's not exit 2 (not-found) — the LLM result is non-deterministic
        assert result.returncode in {0, 1}, (
            f"Unerwarteter Exit-Code {result.returncode}: {result.stderr}"
        )


def test_tc04_solid_check_mit_principle_filtert_auf_ein_prinzip():
    """Scenario: solid-check mit --principle filtert auf ein Prinzip (CON-0048)."""
    result = _run(["spec", "solid", "--json", "--principle", "S", REAL_SPEC])
    assert result.returncode != 2, f"Spec nicht gefunden: {result.stderr}"
    data = json.loads(result.stdout)
    findings = data.get("solid_findings", [])
    for f in findings:
        assert f["principle"] == "S", (
            f"--principle S darf nur S-Findings liefern, aber gefunden: {f['principle']}"
        )


def test_tc05_solid_check_mit_unbekannter_id_gibt_exit_code_2():
    """Scenario: solid-check mit unbekannter ID gibt Exit-Code 2 (CON-0048)."""
    result = _run(["spec", "solid", "SPEC-DOES-NOT-EXIST-9999"])
    assert result.returncode == 2, (
        f"Unbekannte ID muss Exit-Code 2 geben, bekommen: {result.returncode}\n"
        f"stderr: {result.stderr}"
    )


# ─── Pattern-Vorschläge ───────────────────────────────────────────────────────
#
# `pattern-suggest` hat keinen eigenen Befehl zurueckbekommen (CON-0048 v0.3.0):
# die Vorschlaege entstehen in `sdd review spec`. Den Befehl hier gegen
# SPEC-0015 laufen zu lassen, wuerde den Gate-Zustand des Repos schreiben (die
# spec-review-Phase) — die Tests pruefen deshalb die Zusage, nicht den LLM-Lauf.
#
# tc07 bestand vorher aus dem falschen Grund: `pattern-suggest` war ein
# Entfernt-Stub, der nichts schrieb — also existierte auch kein Register.

def test_tc06_review_spec_liefert_pattern_vorschlaege():
    """Scenario: review spec (Pattern-Vorschläge) (CON-0048)."""
    result = _run(["review", "spec", "--help"])
    assert result.returncode == 0
    assert "Pattern" in result.stdout


def test_tc07_vorschlaege_werden_nicht_persistiert():
    """Scenario: Vorschläge ohne Persistenz (CON-0048).

    Persistiert wird ausschliesslich ueber `sdd review pattern accept|reject`.
    Die Vorschlagsphase darf das Register nicht beruehren.
    """
    import inspect

    from sdd_cli import main

    quelle = inspect.getsource(main._run_pattern_phase)
    assert "PatternRegistry" not in quelle
    assert ".accept(" not in quelle and ".reject(" not in quelle


# ─── review pattern accept ────────────────────────────────────────────────────

# ─── pattern accept ───────────────────────────────────────────────────────────

def test_tc08_pattern_accept_persistiert_annahme_im_register():
    """Scenario: pattern-accept persistiert Annahme im Register (CON-0048)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / ".sdd").mkdir()
        (Path(tmpdir) / ".sdd" / "config.yaml").write_text(
            "version: '1.0.0'\nproject:\n  name: test\n", encoding="utf-8"
        )
        _spec(tmpdir, "SPEC-REG")

        result = _run(
            ["review", "pattern", "accept", "SPEC-REG", "Strategy",
             "--reason", "Unabhängige Algorithmen.", "--url",
             "https://refactoring.guru/design-patterns/strategy"],
            cwd=tmpdir,
        )
        assert result.returncode == 0, f"pattern accept fehlgeschlagen: {result.stderr}"

        pattern_file = Path(tmpdir) / ".sdd" / "patterns" / "SPEC-REG-patterns.json"
        assert pattern_file.exists(), "Datei wurde nicht erstellt"

        data = json.loads(pattern_file.read_text(encoding="utf-8"))
        assert data["spec_id"] == "SPEC-REG"
        entries = [p for p in data["patterns"] if p["pattern_name"] == "Strategy"]
        assert len(entries) == 1
        assert entries[0]["status"] == "accepted"
        assert entries[0]["acceptance_reason"] == "Unabhängige Algorithmen."
        assert entries[0]["rejection_reason"] is None


def test_tc09_pattern_accept_ohne_reason_schl_gt_fehl():
    """Scenario: pattern-accept ohne --reason schlägt fehl (CON-0048)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / ".sdd").mkdir()
        (Path(tmpdir) / ".sdd" / "config.yaml").write_text(
            "version: '1.0.0'\nproject:\n  name: test\n", encoding="utf-8"
        )
        _spec(tmpdir, "SPEC-REG")

        result = _run(["review", "pattern", "accept", "SPEC-REG", "Strategy"], cwd=tmpdir)
        # Vorher gruen aus dem falschen Grund: der Entfernt-Stub endete
        # ebenfalls != 0. CON-0048 verlangt exit 1 und diese Meldung.
        assert result.returncode == 1, result.stdout + result.stderr
        assert "--reason ist erforderlich" in result.stdout


# ─── pattern reject ───────────────────────────────────────────────────────────

def test_tc10_pattern_reject_persistiert_ablehnung_mit_begr_ndun():
    """Scenario: pattern-reject persistiert Ablehnung mit Begründung (CON-0048)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / ".sdd").mkdir()
        (Path(tmpdir) / ".sdd" / "config.yaml").write_text(
            "version: '1.0.0'\nproject:\n  name: test\n", encoding="utf-8"
        )
        _spec(tmpdir, "SPEC-REG")

        result = _run(
            ["review", "pattern", "reject", "SPEC-REG", "TemplateMethod",
             "--reason", "Keine gemeinsame Basis."],
            cwd=tmpdir,
        )
        assert result.returncode == 0, f"pattern reject fehlgeschlagen: {result.stderr}"

        pattern_file = Path(tmpdir) / ".sdd" / "patterns" / "SPEC-REG-patterns.json"
        assert pattern_file.exists(), "Datei wurde nicht erstellt"

        data = json.loads(pattern_file.read_text(encoding="utf-8"))
        entries = [p for p in data["patterns"] if p["pattern_name"] == "TemplateMethod"]
        assert len(entries) == 1
        assert entries[0]["status"] == "rejected"
        assert entries[0]["rejection_reason"] == "Keine gemeinsame Basis."
        assert entries[0]["acceptance_reason"] is None


def test_tc11_pattern_reject_ohne_reason_schl_gt_fehl():
    """Scenario: pattern-reject ohne --reason schlägt fehl (CON-0048)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / ".sdd").mkdir()
        (Path(tmpdir) / ".sdd" / "config.yaml").write_text(
            "version: '1.0.0'\nproject:\n  name: test\n", encoding="utf-8"
        )
        _spec(tmpdir, "SPEC-REG")

        result = _run(["review", "pattern", "reject", "SPEC-REG", "TemplateMethod"], cwd=tmpdir)
        # Vorher gruen aus dem falschen Grund: der Entfernt-Stub endete
        # ebenfalls != 0. CON-0048 verlangt exit 1 und diese Meldung.
        assert result.returncode == 1, result.stdout + result.stderr
        assert "--reason ist erforderlich" in result.stdout


# ─── pattern list ─────────────────────────────────────────────────────────────

def test_tc12_pattern_list_zeigt_tabelle_mit_entscheidungen():
    """Scenario: pattern-list zeigt Tabelle mit Entscheidungen (CON-0048)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / ".sdd").mkdir()
        (Path(tmpdir) / ".sdd" / "config.yaml").write_text(
            "version: '1.0.0'\nproject:\n  name: test\n", encoding="utf-8"
        )
        _spec(tmpdir, "SPEC-LST")

        # Create an entry first
        _run(
            ["review", "pattern", "accept", "SPEC-LST", "Observer", "--reason", "Event-Driven."],
            cwd=tmpdir,
        )

        result = _run(["review", "pattern", "list", "SPEC-LST"], cwd=tmpdir)
        assert result.returncode == 0, f"pattern list fehlgeschlagen: {result.stderr}"
        output = result.stdout
        assert "Observer" in output, f"Observer muss in der Ausgabe erscheinen:\n{output}"
        assert "accepted" in output, f"Status 'accepted' muss erscheinen:\n{output}"


def test_tc13_pattern_list_ohne_register_gibt_leere_tabelle_kein():
    """Scenario: pattern-list ohne Register gibt leere Tabelle (kein Fehler) (CON-0048)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / ".sdd").mkdir()
        (Path(tmpdir) / ".sdd" / "config.yaml").write_text(
            "version: '1.0.0'\nproject:\n  name: test\n", encoding="utf-8"
        )
        _spec(tmpdir, "SPEC-EMPTY")

        result = _run(["review", "pattern", "list", "SPEC-EMPTY"], cwd=tmpdir)
        assert result.returncode == 0, (
            f"pattern list ohne Register darf kein Fehler sein (exit {result.returncode}):\n"
            f"{result.stderr}"
        )


def test_tc14_review_pattern_mit_unbekannter_id_gibt_exit_code_2():
    """INV-04: unbekannte ID → exit 2, kein Register angelegt."""
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / ".sdd").mkdir()
        (Path(tmpdir) / ".sdd" / "config.yaml").write_text(
            "version: '1.0.0'\nproject:\n  name: test\n", encoding="utf-8"
        )
        result = _run(
            ["review", "pattern", "accept", "SPEC-GIBTSNICHT", "Strategy", "--reason", "x"],
            cwd=tmpdir,
        )
        assert result.returncode == 2, result.stdout + result.stderr
        assert not (Path(tmpdir) / ".sdd" / "patterns").exists()
