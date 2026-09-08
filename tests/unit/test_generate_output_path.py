"""`sdd test generate` muss den Zielpfad aus dem Test-Dokument beziehen.

test_generator schrieb fest nach .sdd/tests/contract/test_<con>.py. Damit
entstand die unter `artifact:` deklarierte Datei nie, und der erzeugten Datei
war kein Test-Dokument zugeordnet — die Traceability Spec → Contract → Test →
Code riss genau dort, wo sie in Code uebergehen soll. Zusaetzlich lag der
Zielordner immer auf contract/, unabhaengig vom `level:` des Dokuments.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tool"))

# Aliasen: pytest wuerde die Klasse sonst als Testklasse sammeln.
from sdd_cli.test_generator import TestGenerator as Generator

_FEATURE = """Feature: Beispiel
  Scenario: Happy Path
    Given etwas
    When ich handle
    Then passiert etwas
"""


def _contract(root: Path, con_id: str, fmt: str = "gherkin", typ: str = "behavior") -> None:
    d = root / ".sdd" / "contracts" / typ
    d.mkdir(parents=True, exist_ok=True)
    artifact = f"contracts/{typ}/{con_id.lower()}.feature"
    (root / artifact).parent.mkdir(parents=True, exist_ok=True)
    (root / artifact).write_text(_FEATURE, encoding="utf-8")
    (d / f"{con_id}-x.md").write_text(
        f"---\nid: {con_id}\ntitle: T\ntype: {typ}\nformat: {fmt}\n"
        f"spec: SPEC-0001\nartifact: \"{artifact}\"\n---\n\n# C\n", encoding="utf-8")


def _test_doc(root: Path, tst_id: str, con_id: str, level: str,
              artifact: str | None) -> None:
    d = root / ".sdd" / "tests" / level
    d.mkdir(parents=True, exist_ok=True)
    art_line = f'artifact: "{artifact}"\n' if artifact else ""
    (d / f"{tst_id}-x.md").write_text(
        f"---\nid: {tst_id}\ntitle: T\nlevel: {level}\nspec: SPEC-0001\n"
        f"contract: {con_id}\n{art_line}---\n\n# T\n", encoding="utf-8")


class TestDeclaredArtifactWins:
    def test_generates_into_the_declared_file(self, tmp_path):
        _contract(tmp_path, "CON-0001")
        _test_doc(tmp_path, "TST-0001", "CON-0001", "contract",
                  "tests/contract/test_registry_api.py")

        Generator(repo_root=tmp_path).generate("SPEC-0001", ["CON-0001"])

        assert (tmp_path / "tests" / "contract" / "test_registry_api.py").exists()

    def test_old_hardcoded_path_is_no_longer_used(self, tmp_path):
        _contract(tmp_path, "CON-0001")
        _test_doc(tmp_path, "TST-0001", "CON-0001", "unit",
                  "tests/unit/test_datenmodell.py")

        Generator(repo_root=tmp_path).generate("SPEC-0001", ["CON-0001"])

        assert not (tmp_path / ".sdd" / "tests" / "contract" / "test_con-0001.py").exists()

    def test_result_reports_the_declared_path(self, tmp_path):
        _contract(tmp_path, "CON-0001")
        _test_doc(tmp_path, "TST-0001", "CON-0001", "unit",
                  "tests/unit/test_datenmodell.py")

        result = Generator(repo_root=tmp_path).generate("SPEC-0001", ["CON-0001"])

        assert result.generated_files[0]["path"] == "tests/unit/test_datenmodell.py"


class TestLevelFallback:
    def test_level_decides_when_no_artifact_declared(self, tmp_path):
        _contract(tmp_path, "CON-0001")
        _test_doc(tmp_path, "TST-0001", "CON-0001", "acceptance", artifact=None)

        Generator(repo_root=tmp_path).generate("SPEC-0001", ["CON-0001"])

        assert (tmp_path / "tests" / "acceptance" / "test_con-0001.py").exists()

    def test_placeholder_artifact_falls_back_to_level(self, tmp_path):
        """`sdd new test` schreibt tests/<level>/ als Platzhalter – kein Pfad."""
        _contract(tmp_path, "CON-0001")
        _test_doc(tmp_path, "TST-0001", "CON-0001", "unit", "tests/<level>/")

        Generator(repo_root=tmp_path).generate("SPEC-0001", ["CON-0001"])

        assert (tmp_path / "tests" / "unit" / "test_con-0001.py").exists()


class TestFormatTableFallback:
    """Ohne TST-Dokument gilt die Format-Tabelle aus CON-0028."""

    def test_gherkin_goes_to_behavior(self, tmp_path):
        _contract(tmp_path, "CON-0001", fmt="gherkin", typ="behavior")
        Generator(repo_root=tmp_path).generate("SPEC-0001", ["CON-0001"])
        assert (tmp_path / "tests" / "behavior" / "test_con-0001.py").exists()

    def test_openapi_goes_to_api(self, tmp_path):
        _contract(tmp_path, "CON-0001", fmt="openapi", typ="api")
        Generator(repo_root=tmp_path).generate("SPEC-0001", ["CON-0001"])
        assert (tmp_path / "tests" / "api" / "test_con-0001.py").exists()

    def test_nothing_lands_under_sdd(self, tmp_path):
        """.sdd/ haelt die SDD-Dokumente, nicht den ausfuehrbaren Testcode."""
        _contract(tmp_path, "CON-0001", fmt="openapi", typ="api")
        Generator(repo_root=tmp_path).generate("SPEC-0001", ["CON-0001"])
        assert not list((tmp_path / ".sdd" / "tests").rglob("*.py"))
