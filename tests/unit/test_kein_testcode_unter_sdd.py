"""Ausfuehrbarer Testcode gehoert nach tests/, nicht nach .sdd/ (#94).

CON-0028: "Der ausfuehrbare Testcode liegt in allen drei Faellen unter tests/;
.sdd/ haelt ausschliesslich die SDD-Dokumente."

Der Generator folgte dem `artifact:`-Feld des TST-Dokuments ohne Pruefung. Vier
Dokumente zeigten nach `.sdd/tests/contract/`, 27 Tests lagen dort — und die
Suite sammelte sie nie ein. Neun davon waren rot, seit SPEC-0044 die Befehle
umbenannt hat, ohne dass es jemand merkte.
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

_ROOT = Path(__file__).resolve().parents[2]
_SDD = _ROOT / ".sdd"


# Hilfsskripte der Sonden-Presets (SPEC-0054) liegen bewusst unter .sdd/quality/: Sie sind
# Mess-Tooling des Projekts (Konverter, Extraktor, pytest-Plugin), kein Testcode.
_SONDEN_HILFEN = _SDD / "quality"


def test_kein_python_unterhalb_von_sdd():
    treffer = [
        str(p.relative_to(_ROOT))
        for p in _SDD.rglob("*.py")
        if "__pycache__" not in p.parts and not p.is_relative_to(_SONDEN_HILFEN)
    ]
    assert not treffer, "Testcode unter .sdd/: " + ", ".join(treffer)


def _tst_dokumente() -> list[tuple[Path, dict]]:
    docs = []
    for md in sorted((_SDD / "tests").rglob("*.md")):
        m = re.match(r"^---\n(.*?)\n---\n?", md.read_text(encoding="utf-8"), re.DOTALL)
        if not m:
            continue
        fm = yaml.safe_load(m.group(1)) or {}
        if isinstance(fm, dict) and str(fm.get("id", "")).startswith("TST-"):
            docs.append((md, fm))
    return docs


def test_kein_tst_dokument_zeigt_nach_sdd():
    """Das `artifact:`-Feld ist der Weg, auf dem der Code dort landete."""
    falsch = [
        f"{md.relative_to(_ROOT)} -> {fm.get('artifact')}"
        for md, fm in _tst_dokumente()
        if str(fm.get("artifact") or "").strip().strip('"').startswith(".sdd/")
    ]
    assert not falsch, "TST-Dokumente mit Ziel unter .sdd/: " + "; ".join(falsch)


def test_es_gibt_ueberhaupt_tst_dokumente():
    """Absicherung gegen einen Test, der nichts prueft."""
    assert len(_tst_dokumente()) >= 20


class TestGeneratorWeistSddZielAb:
    """Der Generator setzt die Regel durch, egal was das Dokument sagt."""

    def test_artifact_unter_sdd_wird_ignoriert(self, tmp_path):
        from sdd_cli.test_generator import TestGenerator

        doc_dir = tmp_path / ".sdd" / "tests" / "contract"
        doc_dir.mkdir(parents=True)
        (doc_dir / "TST-9001-x.md").write_text(
            "---\n"
            "id: TST-9001\n"
            "contract: CON-9001\n"
            "level: contract\n"
            'artifact: ".sdd/tests/contract/test_con-9001.py"\n'
            "---\n\n# Test\n",
            encoding="utf-8",
        )
        ziel = TestGenerator(tmp_path)._output_path("CON-9001", {"format": "gherkin"})
        # Nur die .sdd-Regel, nicht die Schreibweise des Dateinamens — die
        # haengt an #79 und wird dort geprueft.
        assert ".sdd" not in ziel.parts
        assert ziel.parent == tmp_path / "tests" / "contract"

    def test_artifact_unter_tests_wird_weiter_befolgt(self, tmp_path):
        """Die Regel darf nur .sdd/ treffen, nicht jedes artifact-Feld."""
        from sdd_cli.test_generator import TestGenerator

        doc_dir = tmp_path / ".sdd" / "tests" / "contract"
        doc_dir.mkdir(parents=True)
        (doc_dir / "TST-9002-x.md").write_text(
            "---\n"
            "id: TST-9002\n"
            "contract: CON-9002\n"
            "level: contract\n"
            'artifact: "tests/acceptance/test_eigener_name.py"\n'
            "---\n\n# Test\n",
            encoding="utf-8",
        )
        ziel = TestGenerator(tmp_path)._output_path("CON-9002", {"format": "gherkin"})
        assert ziel == tmp_path / "tests" / "acceptance" / "test_eigener_name.py"
