"""SPEC-0054 FR-14: AST-Abhängigkeitsextraktor des Python-Presets (Kanten import, call, write)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from sdd_cli.quality.parsers import parse_output

PRESET = Path(__file__).resolve().parents[2] / "tool/sdd_cli/blueprint/stacks/python-cli/files/.sdd/quality"


def _projekt(root: Path) -> list[str]:
    dateien = {
        "tool/pkg/__init__.py": "",
        "tool/pkg/core.py": "WERT = 1\n",
        "tool/pkg/web/__init__.py": "",
        "tool/pkg/web/routes.py": (
            "import subprocess\n"
            "import yaml\n"
            "from pathlib import Path\n"
            "from ..core import WERT\n"
            "from pkg import core\n"
            "SPECS = '.sdd/specs'\n\n"
            "def f(name):\n"
            "    from . import helper\n"
            "    subprocess.run(['claude', '--print'])\n"
            "    Path('.sdd/specs/SPEC-0001.md').write_text('x')\n"
            "    open(SPECS + '/b.md', 'w')\n"
            "    open('liest.txt')\n"
            "    Path(name).write_text('y')\n"
            "    __import__(name)\n"),
        "tool/pkg/web/helper.py": "",
    }
    for rel, inhalt in dateien.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(inhalt)
    return [r for r in dateien if r.endswith(".py")]


def test_kanten(tmp_path):
    dateien = _projekt(tmp_path)
    proc = subprocess.run([sys.executable, str(PRESET / "extract_deps.py"), *dateien],
                          cwd=tmp_path, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    out = tmp_path / "deps.json"
    out.write_text(proc.stdout)
    g = parse_output("sdd-deps", out, tmp_path)
    assert g.kinds == frozenset({"import", "call", "write"})
    von = [e for e in g.edges if e.source == "tool/pkg/web/routes.py"]
    imports = {(e.target, e.symbol) for e in von if e.kind == "import"}
    assert ("tool/pkg/core.py", "WERT") in imports
    assert ("tool/pkg/core.py", "core") in imports
    assert ("tool/pkg/web/helper.py", "helper") in imports
    assert not any(e.symbol == "yaml" for e in von)
    calls = {(e.symbol, e.args) for e in von if e.kind == "call"}
    assert ("subprocess.run", ("claude", "--print")) in calls
    writes = {(e.target, e.symbol) for e in von if e.kind == "write"}
    assert (".sdd/specs/SPEC-0001.md", "pathlib.Path.write_text") in writes
    assert (".sdd/specs/b.md", "open") in writes
    assert not any(t == "liest.txt" for t, _ in writes)
    unaufgeloest = [e for e in von if e.unresolved]
    assert {e.kind for e in unaufgeloest} >= {"import", "write"}
