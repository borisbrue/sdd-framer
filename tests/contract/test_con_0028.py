# AUTO-GENERATED from CON-0028 via sdd test generate — do not delete
"""Contract-Tests für Auto Test Generation – Verhalten (CON-0028).

Spec: SPEC-0014 · Contract: CON-0028
Prüft: Generierungsstrategie pro Format, Header-Kommentar, pytest dry-run,
       Re-Run-Verhalten (kein Überschreiben manueller Ergänzungen).
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tool"))

FEATURE_CONTENT = """\
Feature: Beispiel

  Scenario: Erster Fall
    Given eine Bedingung
    When eine Aktion
    Then ein Ergebnis

  Scenario: Zweiter Fall
    Given eine andere Bedingung
    When eine andere Aktion
    Then ein anderes Ergebnis

  Scenario: Fehlerfall
    Given eine ungültige Eingabe
    When eine Aktion
    Then ein Fehler
"""


# ─── Fixtures ────────────────────────────────────────────────────────────────

def _write_gherkin_contract(tmp_path: Path, con_id: str, feature: str) -> Path:
    md = tmp_path / ".sdd" / "contracts" / "behavior" / f"{con_id}.md"
    md.parent.mkdir(parents=True, exist_ok=True)
    md.write_text(
        f"---\nid: {con_id}\ntitle: T\ntype: behavior\nformat: gherkin\n"
        f"spec: SPEC-0014\nversion: 0.1.0\nstatus: draft\n"
        f"artifact: .sdd/contracts/behavior/{con_id}.feature\ntests: []\n---\n",
        encoding="utf-8",
    )
    feature_file = tmp_path / ".sdd" / "contracts" / "behavior" / f"{con_id}.feature"
    feature_file.write_text(feature, encoding="utf-8")
    return feature_file


def _write_openapi_contract(tmp_path: Path, con_id: str) -> Path:
    md = tmp_path / ".sdd" / "contracts" / "api" / f"{con_id}.md"
    md.parent.mkdir(parents=True, exist_ok=True)
    md.write_text(
        f"---\nid: {con_id}\ntitle: T\ntype: api\nformat: openapi\n"
        f"spec: SPEC-0014\nversion: 0.1.0\nstatus: draft\n"
        f"artifact: .sdd/contracts/api/{con_id}.openapi.yaml\ntests: []\n---\n",
        encoding="utf-8",
    )
    yaml_file = tmp_path / ".sdd" / "contracts" / "api" / f"{con_id}.openapi.yaml"
    yaml_file.write_text("openapi: '3.1.0'\ninfo:\n  title: T\n  version: '0.1.0'\npaths: {}\n",
                         encoding="utf-8")
    return yaml_file


# ─── TC-01: Gherkin-Contract erzeugt pytest-bdd Testdatei ────────────────────

def test_tc01_gherkin_generates_pytest_file(tmp_path):
    """Gherkin-Contract → tests/behavior/test_con_xxxx.py (CON-0028, Format-Tabelle)."""
    _write_gherkin_contract(tmp_path, "CON-XXXX", FEATURE_CONTENT)

    from sdd_cli.test_generator import TestGenerator
    gen = TestGenerator(repo_root=tmp_path)
    result = gen.generate("SPEC-0014", contracts=["CON-XXXX"])

    out = tmp_path / "tests" / "behavior" / "test_con_xxxx.py"
    assert out.exists()
    assert len(result.generated_files) >= 1


def test_tc01b_generated_file_has_auto_header(tmp_path):
    """Erste Zeile ist AUTO-GENERATED Header (CON-0028 INV-04)."""
    _write_gherkin_contract(tmp_path, "CON-XXXX", FEATURE_CONTENT)

    from sdd_cli.test_generator import TestGenerator
    gen = TestGenerator(repo_root=tmp_path)
    gen.generate("SPEC-0014", contracts=["CON-XXXX"])

    out = tmp_path / "tests" / "behavior" / "test_con_xxxx.py"
    first_line = out.read_text(encoding="utf-8").splitlines()[0]
    assert "AUTO-GENERATED" in first_line
    assert "CON-XXXX" in first_line


# ─── TC-02: Alle 3 Scenarios werden als Tests erzeugt ────────────────────────

def test_tc02_all_scenarios_have_test_functions(tmp_path):
    """Jedes Gherkin-Scenario → mindestens 1 Testfunktion (CON-0028 INV-01)."""
    _write_gherkin_contract(tmp_path, "CON-XXXX", FEATURE_CONTENT)

    from sdd_cli.test_generator import TestGenerator
    gen = TestGenerator(repo_root=tmp_path)
    gen.generate("SPEC-0014", contracts=["CON-XXXX"])

    content = (tmp_path / "tests" / "behavior" / "test_con_xxxx.py").read_text(encoding="utf-8")
    test_funcs = [l for l in content.splitlines() if l.startswith("def test_")]
    assert len(test_funcs) >= 3


# ─── TC-03: Error-Case-Scenario erzeugt Fehlerfall-Test ──────────────────────

def test_tc03_error_scenario_generates_error_test(tmp_path):
    """Scenarios mit 'Fehler' im Text → Test prüft Fehlverhalten (CON-0028 INV-02)."""
    _write_gherkin_contract(tmp_path, "CON-XXXX", FEATURE_CONTENT)

    from sdd_cli.test_generator import TestGenerator
    gen = TestGenerator(repo_root=tmp_path)
    gen.generate("SPEC-0014", contracts=["CON-XXXX"])

    content = (tmp_path / "tests" / "behavior" / "test_con_xxxx.py").read_text(encoding="utf-8")
    assert "fehler" in content.lower() or "error" in content.lower() or "raises" in content.lower()


# ─── TC-04: Generierte Tests sind syntaktisch valide ─────────────────────────

def test_tc04_generated_file_is_syntactically_valid(tmp_path):
    """pytest --collect-only läuft ohne SyntaxError (CON-0028 INV-06)."""
    import subprocess
    _write_gherkin_contract(tmp_path, "CON-XXXX", FEATURE_CONTENT)

    from sdd_cli.test_generator import TestGenerator
    gen = TestGenerator(repo_root=tmp_path)
    gen.generate("SPEC-0014", contracts=["CON-XXXX"])

    out = tmp_path / "tests" / "behavior" / "test_con_xxxx.py"
    result = subprocess.run(
        [sys.executable, "-m", "py_compile", str(out)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"SyntaxError: {result.stderr}"


# ─── TC-05: Re-Run überschreibt keine manuellen Ergänzungen ──────────────────

def test_tc05_rerun_preserves_manual_additions(tmp_path):
    """Manuell ergänzte Funktion bleibt nach Re-Run erhalten (CON-0028 INV-05)."""
    _write_gherkin_contract(tmp_path, "CON-XXXX", FEATURE_CONTENT)

    from sdd_cli.test_generator import TestGenerator
    gen = TestGenerator(repo_root=tmp_path)
    gen.generate("SPEC-0014", contracts=["CON-XXXX"])

    out = tmp_path / "tests" / "behavior" / "test_con_xxxx.py"
    original = out.read_text(encoding="utf-8")
    out.write_text(original + "\ndef test_custom_manual():\n    assert True\n", encoding="utf-8")

    gen.generate("SPEC-0014", contracts=["CON-XXXX"])

    final = out.read_text(encoding="utf-8")
    assert "test_custom_manual" in final


# ─── TC-06: Phase 6 blockiert bei SyntaxError im generierten Test ─────────────

def test_tc06_phase6_blocked_on_syntax_error(tmp_path):
    """Wenn generierte Datei SyntaxError hat → Phase 6 result=failed (CON-0028)."""
    _write_gherkin_contract(tmp_path, "CON-XXXX", FEATURE_CONTENT)

    from sdd_cli.test_generator import TestGenerator
    gen = TestGenerator(repo_root=tmp_path)

    with patch.object(gen, "_render_template", return_value="def broken(:\n    pass\n"):
        result = gen.generate("SPEC-0014", contracts=["CON-XXXX"])

    assert result.success is False
    assert result.syntax_errors


# ─── TC-07: OpenAPI-Contract erzeugt httpx-Testdatei ─────────────────────────

def test_tc07_openapi_generates_httpx_test(tmp_path):
    """openapi-Contract → tests/contract/test_con_xxxx.py mit httpx (CON-0028)."""
    _write_openapi_contract(tmp_path, "CON-XXXX")

    from sdd_cli.test_generator import TestGenerator
    gen = TestGenerator(repo_root=tmp_path)
    gen.generate("SPEC-0014", contracts=["CON-XXXX"])

    out = tmp_path / "tests" / "api" / "test_con_xxxx.py"
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "httpx" in content or "TestClient" in content or "client" in content.lower()
