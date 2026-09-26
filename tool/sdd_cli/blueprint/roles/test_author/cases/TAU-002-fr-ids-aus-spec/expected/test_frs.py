"""Tests für sddlib.frs.extract_fr_ids (SPEC-0102 FR-01, FR-02, FR-03)."""
import textwrap
import unittest

from sddlib.frs import extract_fr_ids


def body(text: str) -> str:
    return textwrap.dedent(text).lstrip("\n")


class ExtractFrIdsTest(unittest.TestCase):
    # FR-01
    def test_fr01_nummerierte_h2_ueberschrift(self):
        b = body("""
            # SPEC-0001
            ## 4. Funktionale Anforderungen
            - **FR-01:** Eins
            - **FR-02:** Zwei
            ## 5. Nicht-Ziele
            - **FR-99:** gehört nicht dazu
            """)
        self.assertEqual(extract_fr_ids(b), ["FR-01", "FR-02"])

    def test_fr01_h3_ohne_nummer_und_kleinschreibung(self):
        b = body("""
            # SPEC-0028
            ### funktionale anforderungen
            - FR-01: Eins
            ### Akzeptanz
            - FR-07: nicht mehr im Abschnitt
            """)
        self.assertEqual(extract_fr_ids(b), ["FR-01"])

    def test_fr01_ohne_abschnitt_leer(self):
        b = body("""
            # SPEC-0003
            ## Kontext
            - **FR-01:** steht im falschen Abschnitt
            """)
        self.assertEqual(extract_fr_ids(b), [])

    # FR-02
    def test_fr02_unterueberschriften_gehoeren_dazu(self):
        b = body("""
            ## 4. Funktionale Anforderungen
            ### Import
            - **FR-01:** Import
            ### Export
            - **FR-02:** Export
            ## 5. Nicht-Ziele
            - **FR-03:** nein
            """)
        self.assertEqual(extract_fr_ids(b), ["FR-01", "FR-02"])

    # FR-03
    def test_fr03_schreibweisen_am_zeilenanfang(self):
        b = body("""
            ## Funktionale Anforderungen
            - **FR-01:** fett mit Doppelpunkt
            **FR-02** ohne Listenmarker
            * **FR-03** Stern
              + FR-04: eingerückt mit Plus
            - [ ] **FR-05:** offene Checkbox
            - [x] FR-06: erledigte Checkbox
            """)
        self.assertEqual(extract_fr_ids(b),
                         ["FR-01", "FR-02", "FR-03", "FR-04", "FR-05", "FR-06"])

    def test_fr03_querverweise_im_fliesstext_zaehlen_nicht(self):
        b = body("""
            ## 4. Funktionale Anforderungen
            - **FR-01:** Kanal wie in SPEC-0016 (FR-18–FR-20) beschrieben.
            - **FR-02:** Ergänzt FR-01 um Wiederholungen; siehe auch FR-24.
            """)
        self.assertEqual(extract_fr_ids(b), ["FR-01", "FR-02"])

    def test_fr03_duplikate_einmal_in_reihenfolge(self):
        b = body("""
            ## 4. Funktionale Anforderungen
            - **FR-03:** zuerst
            - **FR-01:** dann
            - **FR-03:** nochmals (Tippfehler im Dokument)
            """)
        self.assertEqual(extract_fr_ids(b), ["FR-03", "FR-01"])


if __name__ == "__main__":
    unittest.main()
