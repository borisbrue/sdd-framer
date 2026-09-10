"""Umlaute duerfen Namen nicht zerloechern, und Modulnamen brauchen Unterstriche.

`_SLUGIFY_RE` verwarf alles ausserhalb [a-z0-9]: aus „Auslieferung der
Oberfläche" wurde `oberfl_che`. Fuer den Pfad `/` entstand ein leerer
Namensteil und damit `def test_tc01_():`.

Dazu bildete der Rueckfall des Zielpfads `test_con-0014.py` — ein Modulname mit
Bindestrich ist nicht importierbar.
"""
from __future__ import annotations

import keyword
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tool"))

# Lazy, damit die Verhaltenstests auch gegen einen Stand ohne _module_name
# laufen und der RED-Nachweis nicht auf einen Collection-Error zusammenfaellt.
from sdd_cli.test_generator import _slug


def _module_name(con_id: str) -> str:
    from sdd_cli.test_generator import _module_name as _impl
    return _impl(con_id)


class TestTransliteration:
    @pytest.mark.parametrize("text,erwartet", [
        ("Auslieferung der Oberfläche", "auslieferung_der_oberflaeche"),
        ("Verhalten der Oberfläche", "verhalten_der_oberflaeche"),
        ("Größe", "groesse"),
        ("Maß", "mass"),
        ("Übersicht", "uebersicht"),
        ("Café", "cafe"),
    ])
    def test_umlaute_bleiben_lesbar(self, text, erwartet):
        assert _slug(text) == erwartet

    def test_ohne_umlaut_unveraendert(self):
        assert _slug("Upload-API") == "upload_api"


class TestNieLeer:
    def test_pfad_wurzel(self):
        """`/` ergab `def test_tc01_():`."""
        assert _slug("/") == "root"

    def test_leerer_text(self):
        assert _slug("") == "root"

    def test_nur_sonderzeichen(self):
        assert _slug("*/#") == "root"

    def test_eigener_rueckfall(self):
        assert _slug("/", fallback="index") == "index"


class TestErgebnisIstEinBezeichner:
    @pytest.mark.parametrize("text", [
        "Auslieferung der Oberfläche", "/", "Größe & Maß", "123 Start", "",
    ])
    def test_als_funktionsname_verwendbar(self, text):
        name = f"test_tc01_{_slug(text)}"
        assert name.isidentifier() and not keyword.iskeyword(name)


class TestModulname:
    def test_bindestrich_wird_unterstrich(self):
        assert _module_name("CON-0014") == "con_0014"

    def test_ergebnis_ist_importierbar(self):
        assert f"test_{_module_name('CON-0014')}".isidentifier()

    def test_rueckfallpfad_nutzt_ihn(self):
        import inspect

        from sdd_cli.test_generator import TestGenerator
        src = inspect.getsource(TestGenerator._output_path)
        assert "_module_name(con_id)" in src
        assert "con_id.lower()}.py" not in src
