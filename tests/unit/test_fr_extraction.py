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

    # Die urspruengliche Abschnittsregel: fest h2 mit Nummer, Ende bei der
    # naechsten h2. So sah der Bestand vor beiden Aenderungen aus.
    _ALT_SECTION = re.compile(
        r"##\s+\d+\.\s+Funktionale Anforderungen\b(.*?)(?=\n##\s|\Z)",
        re.DOTALL | re.IGNORECASE,
    )

    def _paare(self):
        from sdd_cli.frontmatter import parse_safe

        for md in sorted((_ROOT / ".sdd" / "specs").rglob("SPEC-*.md")):
            doc = parse_safe(md)
            if not doc:
                continue
            m = self._ALT_SECTION.search(doc.body or "")
            if not m:
                continue
            alt = list(dict.fromkeys(self._ALT.findall(m.group(1))))
            yield md.name, alt, _extract_fr_ids(doc.body)

    def test_keine_spec_verliert_alle_deklarationen(self):
        leer = [n for n, alt, neu in self._paare() if alt and not neu]
        assert not leer, f"Specs, die alle FR verlieren: {leer}"

    def test_nichts_geht_verloren(self):
        """Die Erkennung darf nur zulegen, nie eine Deklaration verlieren."""
        verloren = {n: sorted(set(alt) - set(neu))
                    for n, alt, neu in self._paare() if set(alt) - set(neu)}
        # SPEC-0032 verliert genau die beiden Phantome aus dem Querverweis
        # `aus SPEC-0016 (FR-18–FR-20)`.
        assert verloren == {
            "SPEC-0032-mobile-agentic-workflow.md": ["FR-18", "FR-20"]
        }, verloren


class TestUeberschriftenformen:
    """SPEC-0028 schreibt `### Funktionale Anforderungen` ohne Nummer.

    Die Regex erwartete fest h2 mit Nummer — der Abschnitt wurde gar nicht
    gefunden, die Spec galt als anforderungsfrei und passierte die
    Compliance-Kette ungeprueft.
    """

    def test_h2_mit_nummer(self):
        text = "## 4. Funktionale Anforderungen\n\n- **FR-01:** A\n"
        assert _extract_fr_ids(text) == ["FR-01"]

    def test_h3_ohne_nummer(self):
        text = "### Funktionale Anforderungen\n\n- **FR-01:** A\n"
        assert _extract_fr_ids(text) == ["FR-01"]

    def test_h2_ohne_nummer(self):
        text = "## Funktionale Anforderungen\n\n- **FR-01:** A\n"
        assert _extract_fr_ids(text) == ["FR-01"]

    def test_checkbox_listen_zaehlen(self):
        """SPEC-0028: `- [ ] **FR-01:** …`"""
        text = "### Funktionale Anforderungen\n\n- [ ] **FR-01:** A\n- [x] **FR-02:** B\n"
        assert _extract_fr_ids(text) == ["FR-01", "FR-02"]


class TestAbschnittsendeFolgtDerEbene:
    """Eine h2-Sektion endet erst bei der naechsten h1/h2."""

    def test_h3_unterueberschrift_bleibt_drin(self):
        """SPEC-0009 gliedert ihre FRs unter `### Export`."""
        text = ("## 4. Funktionale Anforderungen\n\n"
                "### Export\n\n- **FR-01:** A\n\n"
                "### Import\n\n- **FR-02:** B\n\n"
                "## 5. Weiteres\n\n- **FR-99:** falsch\n")
        assert _extract_fr_ids(text) == ["FR-01", "FR-02"]

    def test_h3_sektion_endet_bei_der_naechsten_h3(self):
        text = ("### Funktionale Anforderungen\n\n- **FR-01:** A\n\n"
                "### Nicht-Ziele\n\n- **FR-99:** falsch\n")
        assert _extract_fr_ids(text) == ["FR-01"]

    def test_h3_sektion_endet_auch_bei_h2(self):
        text = ("### Funktionale Anforderungen\n\n- **FR-01:** A\n\n"
                "## 5. Weiteres\n\n- **FR-99:** falsch\n")
        assert _extract_fr_ids(text) == ["FR-01"]

    def test_ohne_folgeueberschrift_bis_zum_ende(self):
        text = "## Funktionale Anforderungen\n\n- **FR-01:** A\n- **FR-02:** B\n"
        assert _extract_fr_ids(text) == ["FR-01", "FR-02"]


class TestKeineSpecBleibtUngeprueft:
    def test_jede_spec_mit_abschnitt_liefert_fr(self):
        from sdd_cli.frontmatter import parse_safe

        leer = []
        for md in sorted((_ROOT / ".sdd" / "specs").rglob("SPEC-*.md")):
            doc = parse_safe(md)
            if not doc or "Funktionale Anforderungen" not in (doc.body or ""):
                continue
            if not _extract_fr_ids(doc.body):
                leer.append(md.name)
        assert not leer, f"Specs, die ungeprueft durchgehen: {leer}"
