"""TST-0102: Glob-Muster (SPEC-0102 FR-01, FR-02, FR-04)."""
import unittest

from sddlib.files import glob_match, matches_any


class GlobTest(unittest.TestCase):
    def test_fr01_stern_innerhalb_einer_ebene(self):
        self.assertTrue(glob_match("src/app.py", "src/*.py"))
        self.assertFalse(glob_match("src/sub/app.py", "src/*.py"))

    def test_fr02_doppelstern_ueber_ebenen(self):
        self.assertTrue(glob_match("pkg/sub/test_a.py", "**/test_*.py"))

    def test_fr04_matches_any(self):
        self.assertTrue(matches_any("a.md", ["*.py", "*.md"]))
        self.assertFalse(matches_any("a.txt", ["*.py", "*.md"]))


if __name__ == "__main__":
    unittest.main()
