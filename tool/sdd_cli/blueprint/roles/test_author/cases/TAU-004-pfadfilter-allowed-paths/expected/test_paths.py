"""Tests für sddlib.paths.path_violations (SPEC-0104 FR-01, FR-02, FR-03)."""
import unittest

from sddlib.paths import path_violations


class PathViolationsTest(unittest.TestCase):
    # FR-01
    def test_fr01_erlaubte_pfade_passieren(self):
        self.assertEqual(path_violations(["pkg/x.py", "pkg/sub/y.py"], ["pkg/*"]), [])

    def test_fr01_ein_passendes_muster_genuegt(self):
        self.assertEqual(
            path_violations(["pkg/x.py", "docs/a.md"], ["pkg/*.py", "docs/*.md"]), [])

    def test_fr01_verstoesse_in_eingabereihenfolge(self):
        self.assertEqual(
            path_violations(["z.py", "pkg/x.py", "a.py"], ["pkg/*"]), ["z.py", "a.py"])

    def test_fr01_leere_allowed_verbietet_alles(self):
        self.assertEqual(path_violations(["pkg/x.py"], []), ["pkg/x.py"])

    # FR-02
    def test_fr02_testdatei_ist_verboten(self):
        self.assertEqual(
            path_violations(["pkg/x.py", "tests/test_x.py"], ["pkg/*", "tests/*"],
                            test_file="tests/test_x.py"),
            ["tests/test_x.py"])

    def test_fr02_sdd_verzeichnis_ist_verboten(self):
        self.assertEqual(
            path_violations([".sdd/specs/SPEC-0001.md", ".sddit/config.toml"], ["*"]),
            [".sdd/specs/SPEC-0001.md"])

    # FR-03
    def test_fr03_absolute_pfade_verboten(self):
        self.assertEqual(path_violations(["/etc/passwd", "pkg/x.py"], ["*"]),
                         ["/etc/passwd"])

    def test_fr03_punkt_punkt_segment_verboten(self):
        self.assertEqual(
            path_violations(["pkg/../secrets.py", "pkg/v1..2.txt"], ["pkg/*"]),
            ["pkg/../secrets.py"])


if __name__ == "__main__":
    unittest.main()
