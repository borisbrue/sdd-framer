"""SPEC-0054 FR-14: pytest-Plugin des Python-Presets schreibt FR-Markierungen als JUnit-Property."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from sdd_cli.quality.parsers import parse_output

PRESET = Path(__file__).resolve().parents[2] / "tool/sdd_cli/blueprint/presets/quality/python"


def test_marker_wird_zur_property(tmp_path):
    (tmp_path / "test_x.py").write_text(
        "import pytest\n\n"
        "@pytest.mark.fr('FR-01', 'FR-03')\n"
        "def test_a():\n    assert True\n\n"
        "def test_b():\n    assert True\n")
    out = tmp_path / "out.xml"
    env = {**os.environ, "PYTHONPATH": str(PRESET)}
    proc = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "sdd_fr_marker",
                           "-p", "no:cacheprovider", f"--junitxml={out}", "test_x.py"],
                          cwd=tmp_path, env=env, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    faelle = {c.name: c.frs for c in parse_output("junit", out, tmp_path,
                                                  fr_marker="property").cases}
    assert faelle == {"test_a": ("FR-01", "FR-03"), "test_b": ()}
    assert "PytestUnknownMarkWarning" not in proc.stdout
