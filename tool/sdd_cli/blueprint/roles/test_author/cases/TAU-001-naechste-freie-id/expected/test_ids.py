"""Tests für sddlib.ids.next_id (SPEC-0101 FR-01, FR-02, FR-03)."""
import unittest

from sddlib.ids import next_id


class NextIdTest(unittest.TestCase):
    # FR-01
    def test_fr01_erste_id_ist_eins(self):
        self.assertEqual(next_id([], "SPEC"), "SPEC-0001")

    def test_fr01_maximum_plus_eins(self):
        self.assertEqual(next_id(["SPEC-0001", "SPEC-0002"], "SPEC"), "SPEC-0003")

    def test_fr01_luecken_werden_nicht_wiederverwendet(self):
        self.assertEqual(next_id(["SPEC-0001", "SPEC-0007", "SPEC-0003"], "SPEC"),
                         "SPEC-0008")

    # FR-02
    def test_fr02_fremde_praefixe_zaehlen_nicht(self):
        ids = ["SPEC-0002", "CON-0200", "TST-0150"]
        self.assertEqual(next_id(ids, "SPEC"), "SPEC-0003")
        self.assertEqual(next_id(ids, "CON"), "CON-0201")
        self.assertEqual(next_id(ids, "ADR"), "ADR-0001")

    def test_fr02_abweichende_eintraege_werden_ignoriert(self):
        ids = ["SPEC-0002", "SPEC-0099-entwurf", "SPEC-XY", "XSPEC-0050"]
        self.assertEqual(next_id(ids, "SPEC"), "SPEC-0003")

    def test_fr02_numerischer_vergleich_bei_alt_ids(self):
        self.assertEqual(next_id(["SPEC-9", "SPEC-12", "SPEC-0010"], "SPEC"), "SPEC-0013")

    # FR-03
    def test_fr03_padding(self):
        self.assertEqual(next_id(["TST-7"], "TST", padding=2), "TST-08")
        self.assertEqual(next_id([], "ADR", padding=1), "ADR-1")

    def test_fr03_lange_nummer_wird_nicht_gekuerzt(self):
        self.assertEqual(next_id(["SPEC-9999"], "SPEC"), "SPEC-10000")

    def test_fr03_padding_kleiner_eins_ist_fehler(self):
        with self.assertRaises(ValueError):
            next_id(["SPEC-0001"], "SPEC", padding=0)


if __name__ == "__main__":
    unittest.main()
