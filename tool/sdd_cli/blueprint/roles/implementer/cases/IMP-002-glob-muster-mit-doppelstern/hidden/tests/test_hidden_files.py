"""Versteckte Tests zu SPEC-0102 (FR-01 bis FR-05)."""
import tempfile
import unittest
from pathlib import Path

from sddlib.files import collect_files, glob_match, matches_any


class HiddenGlobTest(unittest.TestCase):
    def test_fr01_ganzer_pfad(self):
        self.assertFalse(glob_match("src/app.py.bak", "src/*.py"))
        self.assertFalse(glob_match("x/src/app.py", "src/*.py"))

    def test_fr01_fragezeichen(self):
        self.assertTrue(glob_match("a1.py", "a?.py"))
        self.assertFalse(glob_match("a12.py", "a?.py"))
        self.assertFalse(glob_match("a/.py", "a?.py"))

    def test_fr01_sonderzeichen_literal(self):
        self.assertFalse(glob_match("axpy", "a.py"))
        self.assertTrue(glob_match("c++(x).md", "c++(x).md"))
        self.assertFalse(glob_match("cc(x).md", "c+(x).md"))

    def test_fr01_stern_leer(self):
        self.assertTrue(glob_match("src/.py", "src/*.py"))

    def test_fr02_doppelstern_null_ebenen(self):
        self.assertTrue(glob_match("test_a.py", "**/test_*.py"))
        self.assertTrue(glob_match("src/a.py", "src/**/a.py"))
        self.assertTrue(glob_match("src/x/y/a.py", "src/**/a.py"))
        self.assertFalse(glob_match("srca.py", "src/**/a.py"))

    def test_fr02_doppelstern_ohne_slash(self):
        self.assertTrue(glob_match("docs/a/b.md", "docs**"))
        self.assertTrue(glob_match("a/b/c.txt", "**.txt"))

    def test_fr03_verzeichnis_suffix(self):
        self.assertTrue(glob_match(".sdd/config.yaml", ".sdd/**"))
        self.assertTrue(glob_match(".sdd/specs/SPEC-0001.md", ".sdd/**"))
        self.assertFalse(glob_match(".sdd", ".sdd/**"))
        self.assertFalse(glob_match(".sdd/", ".sdd/**"))
        self.assertFalse(glob_match(".sddrc", ".sdd/**"))

    def test_fr04_leere_liste(self):
        self.assertFalse(matches_any("a.py", []))
        self.assertTrue(matches_any("a.py", ("x", "*.py")))


class HiddenCollectTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        for rel in ("src/b.py", "src/a.py", "src/sub/c.py", "README.md", ".sdd/config.yaml",
                    ".git/HEAD", "build/out.py", "docs/x.md"):
            p = self.root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("x", encoding="utf-8")
        (self.root / "leer").mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def test_fr05_alle_dateien_sortiert_ohne_sdd_git(self):
        self.assertEqual(collect_files(self.root, [], []),
                         ["README.md", "build/out.py", "docs/x.md", "src/a.py", "src/b.py",
                          "src/sub/c.py"])

    def test_fr05_include_und_exclude(self):
        self.assertEqual(collect_files(self.root, ["**/*.py"], ["build/**"]),
                         ["src/a.py", "src/b.py", "src/sub/c.py"])

    def test_fr05_include_kann_sdd_nicht_zurueckholen(self):
        self.assertEqual(collect_files(self.root, [".sdd/**", "*.md"], []), ["README.md"])


if __name__ == "__main__":
    unittest.main()
