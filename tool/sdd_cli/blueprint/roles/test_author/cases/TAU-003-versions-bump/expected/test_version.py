"""Tests für sddlib.version.bump_version (SPEC-0103 FR-01, FR-02)."""
import unittest

from sddlib.version import bump_version


class BumpVersionTest(unittest.TestCase):
    # FR-01
    def test_fr01_major_setzt_minor_und_patch_zurueck(self):
        self.assertEqual(bump_version("1.4.2", "major"), "2.0.0")

    def test_fr01_minor_setzt_patch_zurueck(self):
        self.assertEqual(bump_version("1.4.2", "minor"), "1.5.0")

    def test_fr01_patch(self):
        self.assertEqual(bump_version("1.4.2", "patch"), "1.4.3")

    def test_fr01_stellen_sind_zahlen(self):
        self.assertEqual(bump_version("1.9.9", "minor"), "1.10.0")
        self.assertEqual(bump_version("0.0.9", "patch"), "0.0.10")
        self.assertEqual(bump_version("0.0.0", "major"), "1.0.0")

    # FR-02
    def test_fr02_ungueltige_versionen(self):
        for version in ("1.2", "1.2.3.4", "v1.2.3", "1.2.3-rc1", "1.x.0", "", "01.2.3",
                        "1.02.3", "1.2.03", "-1.2.3"):
            with self.subTest(version=version), self.assertRaises(ValueError):
                bump_version(version, "patch")

    def test_fr02_unbekannter_teil(self):
        for part in ("build", "MAJOR", ""):
            with self.subTest(part=part), self.assertRaises(ValueError):
                bump_version("1.2.3", part)


if __name__ == "__main__":
    unittest.main()
