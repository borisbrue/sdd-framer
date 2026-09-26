import unittest

from sddlib.path_policy import PathPolicy, normalize

TASK = {"test_file": "tests/test_x.py", "allowed_paths": ["pkg/*.py", "docs/**"]}


class NormalizeTest(unittest.TestCase):
    def test_backslashes(self):
        self.assertEqual(normalize("pkg\\sub\\a.py"), "pkg/sub/a.py")

    def test_absolute_is_none(self):
        self.assertIsNone(normalize("/etc/passwd"))

    def test_escape_is_none(self):
        self.assertIsNone(normalize("../x.py"))
        self.assertIsNone(normalize("pkg/../../x.py"))
        self.assertIsNone(normalize(".."))

    def test_dotdot_inside_root_ok(self):
        self.assertEqual(normalize("pkg/../pkg/a.py"), "pkg/a.py")


class CheckTest(unittest.TestCase):
    def setUp(self):
        self.p = PathPolicy()

    def test_escape_denied_as_protected(self):
        d = self.p.check("implementer", "../x.py", TASK)
        self.assertEqual((d.allowed, d.reason), (False, "geschützter Pfad"))

    def test_escape_checked_before_role(self):
        d = self.p.check("reviewer", "/abs.py", TASK)
        self.assertEqual(d.reason, "geschützter Pfad")

    def test_other_role_denied(self):
        d = self.p.check("reviewer", "pkg/x.py", TASK)
        self.assertEqual((d.allowed, d.reason), (False, "Rolle reviewer schreibt nicht"))

    def test_protected_defaults(self):
        for pfad in (".sdd/config.yaml", "specs/SPEC-1.md", "contracts/a/b.md", ".sdd",
                     "specs", "contracts", "pkg/../.sdd/x"):
            d = self.p.check("implementer", pfad, {"allowed_paths": ["**"]})
            self.assertEqual((d.allowed, d.reason), (False, "geschützter Pfad"), pfad)

    def test_protected_beats_test_file(self):
        task = {"test_file": ".sdd/tests/t.py"}
        d = self.p.check("test_author", ".sdd/tests/t.py", task)
        self.assertEqual((d.allowed, d.reason), (False, "geschützter Pfad"))

    def test_similar_names_not_protected(self):
        d = self.p.check("implementer", "specsheet/a.py", {})
        self.assertTrue(d.allowed)

    def test_implementer_may_not_write_test_file(self):
        task = {"test_file": "tests/test_x.py", "allowed_paths": ["tests/*.py"]}
        d = self.p.check("implementer", "tests/test_x.py", task)
        self.assertEqual((d.allowed, d.reason), (False, "Testdatei des Tasks"))

    def test_test_file_normalized_both_sides(self):
        task = {"test_file": "./tests/test_x.py"}
        d = self.p.check("test_author", "tests\\sub\\..\\test_x.py", task)
        self.assertEqual((d.allowed, d.reason), (True, None))

    def test_test_author_other_file(self):
        d = self.p.check("test_author", "pkg/x.py", TASK)
        self.assertEqual((d.allowed, d.reason), (False, "test_author schreibt nur die Testdatei"))

    def test_test_author_without_test_file(self):
        d = self.p.check("test_author", "tests/test_x.py", {})
        self.assertFalse(d.allowed)
        self.assertEqual(d.reason, "test_author schreibt nur die Testdatei")

    def test_outside_allowed(self):
        d = self.p.check("implementer", "pkg/sub/x.py", TASK)
        self.assertEqual((d.allowed, d.reason), (False, "außerhalb allowed_paths"))

    def test_doublestar_allowed(self):
        self.assertTrue(self.p.check("implementer", "docs/a/b/c.md", TASK).allowed)

    def test_no_or_empty_allowed_paths_allows(self):
        self.assertEqual(self.p.check("implementer", "any/where.py", {}).reason, None)
        self.assertTrue(self.p.check("implementer", "x.py", {"allowed_paths": []}).allowed)


class ConfigTest(unittest.TestCase):
    def test_constructor_extra_patterns(self):
        p = PathPolicy(protected_paths=["vendor/**"])
        d = p.check("implementer", "vendor/lib.py", {})
        self.assertEqual((d.allowed, d.reason), (False, "geschützter Pfad"))
        self.assertEqual(p.check("implementer", "specs/a.md", {}).reason, "geschützter Pfad")

    def test_from_config(self):
        p = PathPolicy.from_config({"pipeline": {"protected_paths": ["*.lock"]}})
        self.assertFalse(p.check("implementer", "poetry.lock", {}).allowed)
        self.assertTrue(p.check("implementer", "sub/poetry.lock", {}).allowed)

    def test_from_config_missing(self):
        for raw in ({}, {"pipeline": None}, {"pipeline": {}}, {"pipeline": {"protected_paths": None}}):
            p = PathPolicy.from_config(raw)
            self.assertTrue(p.check("implementer", "pkg/a.py", {}).allowed)
            self.assertFalse(p.check("implementer", ".sdd/a", {}).allowed)


if __name__ == "__main__":
    unittest.main()
