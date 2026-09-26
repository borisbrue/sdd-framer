"""Versteckte Tests zu SPEC-0103 (FR-01 bis FR-06)."""
import dataclasses
import tempfile
import unittest
from pathlib import Path

from sddlib.path_policy import PathPolicy, PolicyDecision, normalize

TASK = {"test_file": "tests/test_x.py", "allowed_paths": ["pkg/**", "README.md"]}


class HiddenNormalizeTest(unittest.TestCase):
    def test_fr01_backslash_und_punkte(self):
        self.assertEqual(normalize("pkg\\sub\\a.py"), "pkg/sub/a.py")
        self.assertEqual(normalize("./pkg/../lib/a.py"), "lib/a.py")

    def test_fr01_flucht(self):
        self.assertIsNone(normalize("/etc/passwd"))
        self.assertIsNone(normalize("\\etc\\passwd"))
        self.assertIsNone(normalize(".."))
        self.assertIsNone(normalize("pkg/../../x"))

    def test_fr01_innen_bleibt(self):
        self.assertEqual(normalize("pkg/../x"), "x")


class HiddenCheckTest(unittest.TestCase):
    def setUp(self):
        self.p = PathPolicy(Path("/projekt"))

    def assertDecision(self, d, allowed, reason):
        self.assertIsInstance(d, PolicyDecision)
        self.assertEqual((d.allowed, d.reason), (allowed, reason))

    def test_fr02_entscheidung_unveraenderlich(self):
        d = self.p.check("implementer", "pkg/a.py", TASK)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            d.__setattr__("allowed", False)

    def test_fr02_regel1_flucht_vor_rolle(self):
        self.assertDecision(self.p.check("reviewer", "../x", TASK), False, "geschützter Pfad")
        self.assertDecision(self.p.check("implementer", "/abs/pkg/a.py", TASK), False,
                            "geschützter Pfad")

    def test_fr02_regel2_nicht_schreibende_rollen(self):
        for rolle in ("decomposer", "reviewer", "supervisor"):
            self.assertDecision(self.p.check(rolle, "pkg/a.py", TASK), False,
                                f"Rolle {rolle} schreibt nicht")

    def test_fr03_geschuetzt_vor_allowed_paths(self):
        task = {"allowed_paths": ["**"]}
        for pfad in (".sdd/config.yaml", "specs/SPEC-0001.md", "contracts/c.md", ".sdd",
                     "specs", "contracts", "pkg/../.sdd/x", ".sdd\\x"):
            self.assertDecision(self.p.check("implementer", pfad, task), False,
                                "geschützter Pfad")

    def test_fr03_aehnliche_namen_nicht_geschuetzt(self):
        self.assertDecision(self.p.check("implementer", ".sddrc", {}), True, None)
        self.assertDecision(self.p.check("implementer", "pkg/specs/a.py", {}), True, None)

    def test_fr02_regel3_test_author_darf_nicht_in_geschuetzte_testdatei(self):
        task = {"test_file": ".sdd/tests/t.py"}
        self.assertDecision(self.p.check("test_author", ".sdd/tests/t.py", task), False,
                            "geschützter Pfad")

    def test_fr02_regel4_testdatei(self):
        self.assertDecision(self.p.check("implementer", "tests/test_x.py", TASK), False,
                            "Testdatei des Tasks")
        self.assertDecision(self.p.check("test_author", "tests/test_x.py", TASK), True, None)
        self.assertDecision(self.p.check("test_author", "./tests//test_x.py", TASK), True, None)

    def test_fr02_regel4_testdatei_auch_wenn_in_allowed_paths(self):
        task = {"test_file": "pkg/test_a.py", "allowed_paths": ["pkg/**"]}
        self.assertDecision(self.p.check("implementer", "pkg/test_a.py", task), False,
                            "Testdatei des Tasks")

    def test_fr02_regel5_test_author_sonst_nichts(self):
        self.assertDecision(self.p.check("test_author", "pkg/a.py", TASK), False,
                            "test_author schreibt nur die Testdatei")
        self.assertDecision(self.p.check("test_author", "pkg/a.py", {}), False,
                            "test_author schreibt nur die Testdatei")

    def test_fr02_regel6_glob(self):
        self.assertDecision(self.p.check("implementer", "pkg/sub/a.py", TASK), True, None)
        self.assertDecision(self.p.check("implementer", "README.md", TASK), True, None)
        self.assertDecision(self.p.check("implementer", "pkg", TASK), False,
                            "außerhalb allowed_paths")

    def test_fr02_regel7_ohne_allowed_paths(self):
        self.assertDecision(self.p.check("implementer", "irgendwo/a.py", {}), True, None)
        self.assertDecision(self.p.check("implementer", "irgendwo/a.py",
                                         {"allowed_paths": []}), True, None)
        self.assertDecision(self.p.check("implementer", "irgendwo/a.py",
                                         {"allowed_paths": None, "test_file": None}), True, None)


class HiddenConfigTest(unittest.TestCase):
    def test_fr04_zusaetzliche_muster_ergaenzen(self):
        p = PathPolicy(Path("/projekt"), protected_paths=["infra/**"])
        self.assertEqual(p.root, Path("/projekt"))
        self.assertEqual(p.check("implementer", "infra/main.tf", {}).reason, "geschützter Pfad")
        self.assertEqual(p.check("implementer", ".sdd/x", {}).reason, "geschützter Pfad")

    def test_fr05_from_config(self):
        p = PathPolicy.from_config(Path("/p"), {"pipeline": {"protected_paths": ["secrets/*"]}})
        self.assertFalse(p.check("implementer", "secrets/key", {}).allowed)
        self.assertTrue(p.check("implementer", "secrets/sub/key", {}).allowed)

    def test_fr05_from_config_ohne_abschnitt(self):
        for cfg in ({}, {"pipeline": None}, {"pipeline": {"protected_paths": None}}):
            p = PathPolicy.from_config(Path("/p"), cfg)
            self.assertTrue(p.check("implementer", "a.py", {}).allowed)
            self.assertFalse(p.check("implementer", "specs/a.md", {}).allowed)

    def test_fr06_kein_dateisystem(self):
        with tempfile.TemporaryDirectory() as d:
            p = PathPolicy(Path(d))
            self.assertTrue(p.check("implementer", "neu/datei.py", {}).allowed)
            self.assertEqual(list(Path(d).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
