"""Tests für sddlib.run_id (SPEC-0105 FR-01, FR-02, FR-03)."""
import unittest
from datetime import datetime, timedelta, timezone

from sddlib.run_id import new_run_id, parse_run_id

PLUS2 = timezone(timedelta(hours=2))
MINUS5 = timezone(timedelta(hours=-5))


class NewRunIdTest(unittest.TestCase):
    # FR-01
    def test_fr01_beispiel_aus_spec(self):
        when = datetime(2026, 9, 26, 16, 5, 9, tzinfo=PLUS2)
        self.assertEqual(new_run_id("SPEC-0055", when), "SPEC-0055-20260926T140509Z")

    def test_fr01_nachmittag_in_utc_im_24h_format(self):
        when = datetime(2026, 1, 2, 23, 59, 58, tzinfo=timezone.utc)
        self.assertEqual(new_run_id("SPEC-1", when), "SPEC-1-20260102T235958Z")

    def test_fr01_umrechnung_ueber_datumsgrenze(self):
        when = datetime(2026, 12, 31, 21, 30, 0, tzinfo=MINUS5)
        self.assertEqual(new_run_id("CON-0217", when), "CON-0217-20270101T023000Z")

    # FR-02
    def test_fr02_naiver_zeitpunkt_abgelehnt(self):
        with self.assertRaises(ValueError):
            new_run_id("SPEC-0055", datetime(2026, 9, 26, 12, 0, 0))

    def test_fr02_ungueltige_spec_id_abgelehnt(self):
        when = datetime(2026, 9, 26, 12, 0, 0, tzinfo=timezone.utc)
        for spec_id in ("spec-0055", "SPEC_0055", "SPEC-0055-x", "SPEC-", ""):
            with self.subTest(spec_id=spec_id), self.assertRaises(ValueError):
                new_run_id(spec_id, when)


class ParseRunIdTest(unittest.TestCase):
    # FR-03
    def test_fr03_parse_liefert_utc(self):
        spec, when = parse_run_id("SPEC-0055-20260926T140509Z")
        self.assertEqual(spec, "SPEC-0055")
        self.assertEqual(when, datetime(2026, 9, 26, 14, 5, 9, tzinfo=timezone.utc))
        self.assertEqual(when.utcoffset(), timedelta(0))

    def test_fr03_rundreise(self):
        for when in (datetime(2026, 9, 26, 16, 5, 9, tzinfo=PLUS2),
                     datetime(2026, 12, 31, 21, 30, 0, tzinfo=MINUS5),
                     datetime(2026, 3, 1, 13, 0, 1, tzinfo=timezone.utc)):
            with self.subTest(when=when):
                self.assertEqual(parse_run_id(new_run_id("SPEC-0007", when)),
                                 ("SPEC-0007", when))

    def test_fr03_ungueltige_run_id(self):
        for run_id in ("SPEC-0055", "SPEC-0055-20260926T1405Z", "SPEC-0055-20260926140509",
                       "spec-0055-20260926T140509Z", "SPEC-0055-20260926T140509Z-x"):
            with self.subTest(run_id=run_id), self.assertRaises(ValueError):
                parse_run_id(run_id)


if __name__ == "__main__":
    unittest.main()
