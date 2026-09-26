"""Versteckte Tests zu SPEC-0101 (FR-01 bis FR-04)."""
import unittest

from sddlib.fr_ids import extract_fr_ids


class HiddenFrIdsTest(unittest.TestCase):
    def test_fr01_h3_ohne_nummer(self):
        body = "# T\n\n### Funktionale Anforderungen\n\n- **FR-01:** a\n- **FR-02:** b\n"
        self.assertEqual(extract_fr_ids(body), ["FR-01", "FR-02"])

    def test_fr01_gross_kleinschreibung(self):
        body = "## 2. FUNKTIONALE ANFORDERUNGEN\n\n- FR-07: x\n"
        self.assertEqual(extract_fr_ids(body), ["FR-07"])

    def test_fr01_h1_zaehlt_nicht(self):
        body = "# Funktionale Anforderungen\n\n- FR-01: x\n"
        self.assertEqual(extract_fr_ids(body), [])

    def test_fr02_h3_unterabschnitte_beenden_h2_nicht(self):
        body = ("## 4. Funktionale Anforderungen\n\n### Import\n\n- **FR-01:** a\n\n"
                "### Export\n\n- **FR-02:** b\n\n## 5. Akzeptanz\n\n- **FR-09:** nein\n")
        self.assertEqual(extract_fr_ids(body), ["FR-01", "FR-02"])

    def test_fr02_h3_abschnitt_endet_an_h3(self):
        body = ("## Anforderungen\n\n### Funktionale Anforderungen\n\n- FR-01: a\n\n"
                "### Nicht-funktionale Anforderungen\n\n- FR-02: b\n")
        self.assertEqual(extract_fr_ids(body), ["FR-01"])

    def test_fr02_fr_vor_dem_abschnitt_zaehlt_nicht(self):
        body = "## Kontext\n\n- FR-99: alt\n\n## Funktionale Anforderungen\n\n- FR-01: neu\n"
        self.assertEqual(extract_fr_ids(body), ["FR-01"])

    def test_fr03_schreibweisen(self):
        body = ("## Funktionale Anforderungen\n\n"
                "- **FR-01:** a\n**FR-02** b\n- **FR-03** c\n- **FR-04: d\n- FR-05: e\n"
                "* FR-06: f\n+ FR-07: g\n  - FR-08: eingerueckt\n- [ ] FR-09: offen\n"
                "- [x] **FR-10:** erledigt\n")
        self.assertEqual(extract_fr_ids(body), [f"FR-{i:02d}" for i in range(1, 11)])

    def test_fr03_querverweise_im_fliesstext(self):
        body = ("## 4. Funktionale Anforderungen\n\n"
                "- **FR-01:** Nutzt `Ctx` aus SPEC-0016 (FR-18–FR-20) als Kanal.\n"
                "Siehe auch FR-30 in SPEC-0002.\n- **FR-02:** b\n")
        self.assertEqual(extract_fr_ids(body), ["FR-01", "FR-02"])

    def test_fr03_mehrstellige_ids(self):
        body = "## Funktionale Anforderungen\n\n- **FR-123:** x\n- FR-1: y\n"
        self.assertEqual(extract_fr_ids(body), ["FR-123", "FR-1"])

    def test_fr04_duplikate_reihenfolgestabil(self):
        body = ("## Funktionale Anforderungen\n\n- FR-03: a\n- FR-01: b\n"
                "- FR-03: nochmal\n- FR-02: c\n")
        self.assertEqual(extract_fr_ids(body), ["FR-03", "FR-01", "FR-02"])

    def test_fr01_leerer_body(self):
        self.assertEqual(extract_fr_ids(""), [])


if __name__ == "__main__":
    unittest.main()
