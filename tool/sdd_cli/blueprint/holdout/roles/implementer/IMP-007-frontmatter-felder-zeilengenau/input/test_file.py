import tempfile
import unittest
from pathlib import Path

from sddlib.fields import set_frontmatter_fields

DOC = "---\nid: SPEC-0007\nstatus: deprecated\n---\n# Titel\n\nText.\n"


class FieldsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "SPEC-0007-x.md"
        self.path.write_text(DOC, encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_fr03_appends_missing_field(self):
        set_frontmatter_fields(self.path, {"deprecated_reason": "ersetzt"})
        self.assertEqual(
            self.path.read_text(encoding="utf-8"),
            '---\nid: SPEC-0007\nstatus: deprecated\ndeprecated_reason: "ersetzt"\n---\n'
            "# Titel\n\nText.\n",
        )


if __name__ == "__main__":
    unittest.main()
