"""HF-0018: Die Testsonde des Fixtures todo-service ordnet Importfehler der Testdatei zu.

Scheitert ein Testmodul beim Import (z. B. weil die zu testende Klasse noch fehlt), meldet
unittest einen `unittest.loader._FailedTest`. Die Sonde schrieb als Datei `unittest/loader.py`;
das RED-Gate fand den neuen Test nie („Testsonde meldet den neuen Test nicht“), die Task
eskalierte nach drei Versuchen (Testlauf mittwald, SPEC-0001 bis SPEC-0003 des Fixtures).
"""
from __future__ import annotations

import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

SONDE = (Path(__file__).resolve().parents[2] / "tool/sdd_cli/blueprint/bench/fixtures/"
         "todo-service/project/.sdd/quality/run_tests.py")


def _lauf(tmp_path: Path, dateien: dict[str, str]) -> list[ET.Element]:
    for rel, text in dateien.items():
        pfad = tmp_path / rel
        pfad.parent.mkdir(parents=True, exist_ok=True)
        pfad.write_text(text, encoding="utf-8")
    subprocess.run([sys.executable, str(SONDE), "--start", "tests", "--junit", "out.xml"],
                   cwd=tmp_path, capture_output=True, text=True, timeout=60)
    return list(ET.parse(tmp_path / "out.xml").getroot().iter("testcase"))


def test_importfehler_gehoert_zur_testdatei(tmp_path):
    [fall] = _lauf(tmp_path, {
        "tests/__init__.py": "",
        "tests/unit/__init__.py": "",
        "tests/unit/test_rename.py": "from todo.service import fehlt\n\n\n"
                                     "def test_fr01_x():\n    pass\n",
    })
    assert fall.get("file") == "tests/unit/test_rename.py"
    assert fall.find("error") is not None
    assert "unittest" not in (fall.get("file") or "")


def test_normale_tests_behalten_ihre_datei(tmp_path):
    faelle = _lauf(tmp_path, {
        "tests/__init__.py": "",
        "tests/test_ok.py": "import unittest\n\n\nclass T(unittest.TestCase):\n"
                            "    def test_fr01_ok(self):\n        self.assertTrue(True)\n",
    })
    assert [f.get("file") for f in faelle] == ["tests/test_ok.py"]


def test_paket_ohne_modul_datei_bleibt_ohne_falsche_zuordnung(tmp_path):
    [fall] = _lauf(tmp_path, {
        "tests/__init__.py": "",
        "tests/kaputt/__init__.py": "import gibt_es_nicht\n",
        "tests/kaputt/test_a.py": "def test_x():\n    pass\n",
    })
    assert "unittest" not in (fall.get("file") or "")
