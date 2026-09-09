"""Querverweise auf fremde FRs sind keine eigenen Anforderungen.

`_extract_fr_ids` suchte mit \\bFR-\\d+\\b im gesamten FR-Abschnitt und zaehlte
jede Nennung als Anforderung. `sdd spec approve SPEC-0003` brach daran ab:

    ✗ FR-24 hat keinen zugeordneten Test

SPEC-0003 hatte 23 Anforderungen; die FR-24 stammte aus dem Satz „Seit
SPEC-0002 FR-24 gibt es zwei Intervalle." im Fliesstext. Damit wurde jeder
Verweis auf eine fremde Spec zum Fehler — obwohl genau solche Verweise das
sind, was der Regression-Check einfordert.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tool"))

from sdd_cli.compliance import _extract_fr_ids

_ROOT = Path(__file__).resolve().parents[2]


def _abschnitt(inhalt: str) -> str:
    return f"## 4. Funktionale Anforderungen\n\n{inhalt}\n\n## 5. Weiteres\n"


class TestDeklarationenWerdenErkannt:
    """Fuenf Schreibweisen kommen im Bestand vor — alle muessen zaehlen."""

    @pytest.mark.parametrize("zeile", [
        "- **FR-01:** Aussage",
        "**FR-01** Aussage",
        "- **FR-01** Aussage",
        "- **FR-01: Aussage",
        "- FR-01: Aussage",
        "  - **FR-01:** eingerueckt",
    ])
    def test_form_wird_erkannt(self, zeile):
        assert _extract_fr_ids(_abschnitt(zeile)) == ["FR-01"]

    def test_mehrere_in_reihenfolge(self):
        text = _abschnitt("- **FR-01:** A\n- **FR-02:** B\n- **FR-03:** C")
        assert _extract_fr_ids(text) == ["FR-01", "FR-02", "FR-03"]

    def test_dedupliziert(self):
        text = _abschnitt("- **FR-01:** A\n- **FR-01:** nochmal")
        assert _extract_fr_ids(text) == ["FR-01"]


class TestQuerverweiseZaehlenNicht:
    def test_der_gemeldete_fall(self):
        """„Seit SPEC-0002 FR-24 gibt es zwei Intervalle." ist keine FR-24."""
        text = _abschnitt(
            "- **FR-01:** Aussage\n"
            "\n"
            "Seit SPEC-0002 FR-24 gibt es zwei Intervalle."
        )
        assert _extract_fr_ids(text) == ["FR-01"]

    def test_bereichsverweis_zaehlt_nicht(self):
        """Aus SPEC-0032: `… aus SPEC-0016 (FR-18–FR-20) als In-App-Kanal`."""
        text = _abschnitt(
            "- **FR-01:** Aussage\n"
            "  `NotificationContext` aus SPEC-0016 (FR-18–FR-20) als In-App-Kanal"
        )
        assert _extract_fr_ids(text) == ["FR-01"]

    def test_verweis_mitten_in_der_zeile(self):
        text = _abschnitt("- **FR-01:** verfeinert FR-99 aus SPEC-0002")
        assert _extract_fr_ids(text) == ["FR-01"]

    def test_nur_verweise_ergeben_nichts(self):
        assert _extract_fr_ids(_abschnitt("Vergleiche FR-07 und FR-08.")) == []


class TestAbschnittsgrenzeGiltWeiterhin:
    def test_ausserhalb_des_abschnitts_zaehlt_nicht(self):
        text = ("## 3. Kontext\n\n- **FR-99:** falsch platziert\n\n"
                "## 4. Funktionale Anforderungen\n\n- **FR-01:** A\n")
        assert _extract_fr_ids(text) == ["FR-01"]

    def test_ohne_abschnitt_leer(self):
        assert _extract_fr_ids("# Spec\n\n- **FR-01:** A\n") == []


class TestBestandBleibtStabil:
    """Ueber alle Specs des Repos darf nur das Phantom verschwinden.

    Verglichen wird gegen die alte Regel, nicht gegen "nicht leer": SPEC-0028
    schreibt `### Funktionale Anforderungen` ohne Nummer und wird schon von der
    Abschnitts-Regex nicht erfasst — das ist ein eigener Befund und aelter als
    diese Aenderung.
    """

    _ALT = re.compile(r"\bFR-\d+\b")

    def _paare(self):
        from sdd_cli.compliance import _FR_SECTION_RE
        from sdd_cli.frontmatter import parse_safe

        for md in sorted((_ROOT / ".sdd" / "specs").rglob("SPEC-*.md")):
            doc = parse_safe(md)
            if not doc:
                continue
            m = _FR_SECTION_RE.search(doc.body or "")
            if not m:
                continue
            alt = list(dict.fromkeys(self._ALT.findall(m.group(1))))
            yield md.name, alt, _extract_fr_ids(doc.body)

    def test_nichts_kommt_hinzu(self):
        for name, alt, neu in self._paare():
            assert set(neu) <= set(alt), f"{name}: {set(neu) - set(alt)}"

    def test_keine_spec_verliert_alle_deklarationen(self):
        leer = [n for n, alt, neu in self._paare() if alt and not neu]
        assert not leer, f"Specs, die alle FR verlieren: {leer}"

    def test_genau_das_phantom_entfaellt(self):
        """SPEC-0032 nennt `SPEC-0016 (FR-18–FR-20)` im Fliesstext."""
        entfallen = {n: [x for x in alt if x not in neu]
                     for n, alt, neu in self._paare() if alt != neu}
        assert entfallen == {
            "SPEC-0032-mobile-agentic-workflow.md": ["FR-18", "FR-20"]
        }, entfallen
