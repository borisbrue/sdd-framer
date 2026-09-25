"""SPEC-0054 FR-14: Konverter des Python-Presets liefern gültige Austauschformate."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from sdd_cli.quality.parsers import parse_output

PRESET = Path(__file__).resolve().parents[2] / "tool/sdd_cli/blueprint/presets/quality/python"


def _konvertiere(skript, eingabe, tmp_path, *args):
    proc = subprocess.run([sys.executable, str(PRESET / skript), *args], input=eingabe,
                          capture_output=True, text=True, cwd=tmp_path)
    assert proc.returncode == 0, proc.stderr
    out = tmp_path / "out"
    out.write_text(proc.stdout)
    return out


def test_mypy_json_zu_sarif(tmp_path):
    zeilen = "\n".join(json.dumps(d) for d in [
        {"file": "src/a.py", "line": 3, "column": 4, "message": "Incompatible", "code": "assignment",
         "severity": "error"},
        {"file": "src/a.py", "line": 3, "column": 4, "message": "See docs", "code": None,
         "severity": "note"}])
    out = _konvertiere("mypy_to_sarif.py", zeilen + "\n", tmp_path)
    befunde = parse_output("sarif", out, tmp_path).findings
    assert [(f.rule, f.file, f.line, f.severity) for f in befunde] == [
        ("assignment", "src/a.py", 3, "error"), ("mypy", "src/a.py", 3, "note")]


def test_mypy_ohne_befunde(tmp_path):
    out = _konvertiere("mypy_to_sarif.py", "", tmp_path)
    assert parse_output("sarif", out, tmp_path).findings == []


def test_lizard_csv_zu_metriken(tmp_path):
    csv = ("5,2,30,1,6,\"f@1-6@a.py\",\"a.py\",\"f\",\"f()\",1,6\n"
           "70,12,400,2,80,\"g@10-90@a.py\",\"a.py\",\"g\",\"g(x)\",10,90\n"
           "8,4,50,0,9,\"h@1-9@b.py\",\"b.py\",\"h\",\"h()\",1,9\n")
    out = _konvertiere("lizard_to_metrics.py", csv, tmp_path)
    werte = {m.name: m.value for m in parse_output("sdd-metrics", out, tmp_path).metrics}
    assert werte["complexity_mean"] == pytest.approx(6.0)
    assert werte["complexity_max"] == 12
    assert werte["complex_function_share"] == pytest.approx(1 / 3)
    assert werte["long_function_share"] == pytest.approx(1 / 3)
