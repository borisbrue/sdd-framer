import unittest

from release.version import bump


class BumpTest(unittest.TestCase):
    # FR-01
    def test_fr01_major_resets_minor_and_patch(self):
        self.assertEqual(bump("1.4.2", "major"), "2.0.0")

    def test_fr01_minor_resets_patch(self):
        self.assertEqual(bump("1.4.2", "minor"), "1.5.0")
        self.assertEqual(bump("1.9.3", "minor"), "1.10.0")

    def test_fr01_patch(self):
        self.assertEqual(bump("1.4.2", "patch"), "1.4.3")
        self.assertEqual(bump("0.0.9", "patch"), "0.0.10")

    def test_fr01_whitespace(self):
        self.assertEqual(bump(" 1.0.0\n", "patch"), "1.0.1")

    # FR-02
    def test_fr02_prerelease_patch_releases(self):
        self.assertEqual(bump("1.2.3-rc.1", "patch"), "1.2.3")

    def test_fr02_prerelease_minor_major(self):
        self.assertEqual(bump("1.2.3-rc.1", "minor"), "1.3.0")
        self.assertEqual(bump("1.2.3-beta", "major"), "2.0.0")

    # FR-03
    def test_fr03_invalid_versions(self):
        for v in ("1.2", "1.2.3.4", "v1.2.3", "01.2.3", "1.-2.3", "1..3", "", "a.b.c"):
            with self.subTest(v=v), self.assertRaises(ValueError):
                bump(v, "patch")

    def test_fr03_unknown_part(self):
        with self.assertRaises(ValueError):
            bump("1.2.3", "build")


if __name__ == "__main__":
    unittest.main()
