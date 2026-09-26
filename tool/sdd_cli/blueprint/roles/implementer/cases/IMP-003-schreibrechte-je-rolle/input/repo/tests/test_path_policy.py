"""TST-0103: PathPolicy (SPEC-0103 FR-01, FR-02)."""
import unittest
from pathlib import Path

from sddlib.path_policy import PathPolicy, normalize

TASK = {"test_file": "tests/test_x.py", "allowed_paths": ["pkg/**"]}


class PathPolicyTest(unittest.TestCase):
    def setUp(self):
        self.policy = PathPolicy(Path("/projekt"))

    def test_fr01_normalize(self):
        self.assertEqual(normalize("pkg/./a.py"), "pkg/a.py")
        self.assertIsNone(normalize("../x.py"))

    def test_fr02_implementer_in_allowed_paths(self):
        d = self.policy.check("implementer", "pkg/a.py", TASK)
        self.assertTrue(d.allowed)
        self.assertIsNone(d.reason)

    def test_fr02_implementer_ausserhalb(self):
        d = self.policy.check("implementer", "other/a.py", TASK)
        self.assertFalse(d.allowed)
        self.assertEqual(d.reason, "außerhalb allowed_paths")


if __name__ == "__main__":
    unittest.main()
