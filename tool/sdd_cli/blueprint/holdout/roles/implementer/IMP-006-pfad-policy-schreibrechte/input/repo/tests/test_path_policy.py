import unittest

from sddlib.path_policy import PathPolicy, normalize


class PathPolicyTest(unittest.TestCase):
    def test_fr01_normalize_resolves_segments(self):
        self.assertEqual(normalize("pkg/./a/../b.py"), "pkg/b.py")

    def test_fr02_implementer_inside_allowed_paths(self):
        task = {"test_file": "tests/test_x.py", "allowed_paths": ["pkg/*.py"]}
        d = PathPolicy().check("implementer", "pkg/x.py", task)
        self.assertTrue(d.allowed)

    def test_fr02_test_author_writes_own_test_file(self):
        task = {"test_file": "tests/test_x.py", "allowed_paths": ["pkg/*.py"]}
        self.assertTrue(PathPolicy().check("test_author", "tests/test_x.py", task).allowed)


if __name__ == "__main__":
    unittest.main()
