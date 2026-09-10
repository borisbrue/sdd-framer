"""Erzeugte Test-Ruempfe muessen lintbar sein (#99).

`ruff check .` meldete 7 Fehler in einem sonst sauberen Projekt — in Dateien,
die das Werkzeug selbst geschrieben hatte. Drei Ursachen: eine statt zwei
Leerzeilen nach dem Importblock (I001, in *jeder* Datei), sowie tote Importe
von json/jsonschema und httpx (F401).

Der Test schickt die Ausgabe jedes Formats durch ruff. Ohne ruff im PATH bleibt
die AST-Pruefung, die dieselben Fehlerklassen ohne Werkzeug findet.
"""
from __future__ import annotations

import ast
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]

FEATURE = textwrap.dedent("""\
    Feature: Drucker
      Scenario: Anlegen geht
        Given a
      Scenario: Fehler wird gemeldet
        Given b
    """)

OPENAPI = textwrap.dedent("""\
    openapi: 3.0.0
    paths:
      /api/drucker:
        get: {}
      /api/jobs/{id}:
        post: {}
    """)

# Ein Fall je Zweig von _render_template, plus die Rueckfaelle.
FAELLE = {
    "gherkin":      ({"format": "gherkin", "artifact": "c.feature"}, FEATURE),
    "gherkin_leer": ({"format": "gherkin"}, None),
    "openapi":      ({"format": "openapi", "artifact": "c.openapi.yaml"}, OPENAPI),
    "openapi_leer": ({"format": "openapi"}, None),
    "json-schema":  ({"format": "json-schema"}, None),
    "markdown":     ({"format": "markdown"}, None),
}


def _erzeugen(tmp_path: Path, fall: str) -> str:
    from sdd_cli.test_generator import TestGenerator, _pep8_leerzeilen

    con, artefakt = FAELLE[fall]
    if artefakt is not None:
        (tmp_path / con["artifact"]).write_text(artefakt, encoding="utf-8")
    contract = {
        "id": "CON-0001", "title": "Drucker", "spec": "SPEC-0001", **con,
    }
    return _pep8_leerzeilen(TestGenerator(tmp_path)._render_template(contract))


# ── ruff ─────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("fall", sorted(FAELLE))
def test_ruff_ist_zufrieden(tmp_path, fall):
    ruff = shutil.which("ruff") or shutil.which("ruff", path=str(Path(sys.executable).parent))
    if not ruff:
        pytest.skip("ruff nicht im PATH")

    datei = tmp_path / f"test_{fall.replace('-', '_')}.py"
    datei.write_text(_erzeugen(tmp_path, fall), encoding="utf-8")
    ergebnis = subprocess.run(
        [ruff, "check", "--no-cache", "--config", str(_ROOT / "pyproject.toml"),
         "--output-format", "concise", str(datei)],
        capture_output=True, text=True,
    )
    assert ergebnis.returncode == 0, (
        f"ruff meldet Fehler im erzeugten Rumpf ({fall}):\n{ergebnis.stdout}"
    )


# ── ohne Werkzeug ────────────────────────────────────────────────────────────

def _unbenutzte_importe(quelle: str) -> list[str]:
    """Importierte Namen, die im Rest der Datei nicht vorkommen (F401)."""
    baum = ast.parse(quelle)
    benutzt = {
        k.id for k in ast.walk(baum) if isinstance(k, ast.Name)
    } | {
        k.attr for k in ast.walk(baum) if isinstance(k, ast.Attribute)
    } | {
        k.value.id for k in ast.walk(baum)
        if isinstance(k, ast.Attribute) and isinstance(k.value, ast.Name)
    }
    tot = []
    for knoten in ast.walk(baum):
        if isinstance(knoten, ast.Import):
            for alias in knoten.names:
                name = alias.asname or alias.name.split(".")[0]
                if name not in benutzt:
                    tot.append(name)
        elif isinstance(knoten, ast.ImportFrom):
            if knoten.module == "__future__":
                continue
            for alias in knoten.names:
                name = alias.asname or alias.name
                if name not in benutzt:
                    tot.append(name)
    return tot


@pytest.mark.parametrize("fall", sorted(FAELLE))
def test_keine_toten_importe(tmp_path, fall):
    """`import httpx` in jeder Testfunktion, `import json` auf Modulebene —
    als Hinweis gemeint, als Lint-Fehler bezahlt."""
    tot = _unbenutzte_importe(_erzeugen(tmp_path, fall))
    assert not tot, f"unbenutzte Importe im Rumpf ({fall}): {tot}"


@pytest.mark.parametrize("fall", sorted(FAELLE))
def test_zwei_leerzeilen_vor_jeder_definition(tmp_path, fall):
    quelle = _erzeugen(tmp_path, fall)
    zeilen = quelle.splitlines()
    for baum_knoten in ast.parse(quelle).body:
        if not isinstance(baum_knoten, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        start = min(
            [baum_knoten.lineno] + [d.lineno for d in baum_knoten.decorator_list]
        )
        if start <= 3:
            continue
        davor = zeilen[start - 3 : start - 1]
        assert davor == ["", ""], (
            f"{fall}: vor {baum_knoten.name} stehen {davor!r} statt zwei Leerzeilen"
        )


@pytest.mark.parametrize("fall", sorted(FAELLE))
def test_datei_endet_mit_genau_einem_zeilenumbruch(tmp_path, fall):
    quelle = _erzeugen(tmp_path, fall)
    assert quelle.endswith("\n") and not quelle.endswith("\n\n")


class TestNachbereitungIstFormatunabhaengig:
    """Die Regel gilt zentral, damit sie auch fuer spaetere Formate greift."""

    def test_eine_leerzeile_wird_zu_zwei(self):
        from sdd_cli.test_generator import _pep8_leerzeilen

        ergebnis = _pep8_leerzeilen("import pytest\n\ndef test_a():\n    pass\n")
        assert ergebnis == "import pytest\n\n\ndef test_a():\n    pass\n"

    def test_gar_keine_leerzeile_wird_zu_zwei(self):
        from sdd_cli.test_generator import _pep8_leerzeilen

        ergebnis = _pep8_leerzeilen("import pytest\ndef test_a():\n    pass\n")
        assert ergebnis == "import pytest\n\n\ndef test_a():\n    pass\n"

    def test_drei_leerzeilen_werden_zu_zwei(self):
        from sdd_cli.test_generator import _pep8_leerzeilen

        ergebnis = _pep8_leerzeilen("import pytest\n\n\n\n\ndef test_a():\n    pass\n")
        assert ergebnis == "import pytest\n\n\ndef test_a():\n    pass\n"

    def test_dekorator_zaehlt_als_beginn_der_definition(self):
        from sdd_cli.test_generator import _pep8_leerzeilen

        ergebnis = _pep8_leerzeilen(
            "import pytest\n\n@pytest.mark.slow\ndef test_a():\n    pass\n"
        )
        assert ergebnis == "import pytest\n\n\n@pytest.mark.slow\ndef test_a():\n    pass\n"

    def test_einrueckung_bleibt_unberuehrt(self):
        """Eine Methode in einer Klasse ist keine Definition auf Modulebene."""
        from sdd_cli.test_generator import _pep8_leerzeilen

        quelle = "import pytest\n\n\nclass TestX:\n    def test_a(self):\n        pass\n"
        assert _pep8_leerzeilen(quelle) == quelle

    def test_mehrzeiliger_dekorator_bleibt_an_seiner_funktion(self):
        """Der Grund fuer ast statt Zeilenmuster.

        Vor `def` steht hier `)` — ein Muster, das nur auf `def` am
        Zeilenanfang schaut, haette dazwischen zwei Leerzeilen geschoben und
        die Datei zerbrochen.
        """
        from sdd_cli.test_generator import _pep8_leerzeilen

        quelle = (
            "import pytest\n\n\n"
            "@pytest.mark.parametrize(\n"
            '    "x",\n'
            "    [1, 2],\n"
            ")\n"
            "def test_a(x):\n"
            "    pass\n"
        )
        ergebnis = _pep8_leerzeilen(quelle)
        assert ergebnis == quelle
        ast.parse(ergebnis)

    def test_gestapelte_dekoratoren(self):
        from sdd_cli.test_generator import _pep8_leerzeilen

        quelle = (
            "import pytest\n"
            "@pytest.mark.slow\n"
            "@pytest.mark.parametrize('x', [1])\n"
            "def test_a(x):\n"
            "    pass\n"
        )
        ergebnis = _pep8_leerzeilen(quelle)
        assert ergebnis == (
            "import pytest\n\n\n"
            "@pytest.mark.slow\n"
            "@pytest.mark.parametrize('x', [1])\n"
            "def test_a(x):\n"
            "    pass\n"
        )

    def test_unparsebarer_text_bleibt_unveraendert(self):
        """Nichts anfassen, was sich nicht lesen laesst — dieselbe Regel wie
        beim Schreiben vorhandener Dateien (#92)."""
        from sdd_cli.test_generator import _pep8_leerzeilen

        kaputt = "def test_a(\n    x, y\n\ndef test_b():\n    pass\n"
        assert _pep8_leerzeilen(kaputt) == kaputt
