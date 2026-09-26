import tempfile
import unittest
from pathlib import Path

from sddlib.fields import FrontmatterError, set_frontmatter_fields


class HiddenFieldsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, text, fields, name="SPEC-0001-a.md"):
        p = self.dir / name
        p.write_bytes(text.encode("utf-8"))
        set_frontmatter_fields(p, fields)
        return p.read_bytes().decode("utf-8")

    def test_replaces_existing_line(self):
        out = self._run("---\nid: X\nreplaced_by: \"OLD\"\ntitle: T\n---\nBody\n",
                        {"replaced_by": "SPEC-0009"})
        self.assertEqual(out, "---\nid: X\nreplaced_by: \"SPEC-0009\"\ntitle: T\n---\nBody\n")

    def test_non_ascii_and_quotes(self):
        out = self._run("---\nid: X\n---\n", {"reason": 'Überholt "alt"'})
        self.assertEqual(out, '---\nid: X\nreason: "Überholt \\"alt\\""\n---\n')

    def test_order_of_appended_fields(self):
        out = self._run("---\nid: X\n---\nB\n", {"b": "2", "a": "1"})
        self.assertEqual(out, '---\nid: X\nb: "2"\na: "1"\n---\nB\n')

    def test_prefix_key_not_matched(self):
        out = self._run("---\nstatus_note: n\nstatus: draft\n---\n", {"status": "deprecated"})
        self.assertEqual(out, '---\nstatus_note: n\nstatus: "deprecated"\n---\n')

    def test_only_first_occurrence(self):
        out = self._run("---\nk: 1\nk: 2\n---\n", {"k": "3"})
        self.assertEqual(out, '---\nk: "3"\nk: 2\n---\n')

    def test_indented_line_is_not_field(self):
        out = self._run("---\nmeta:\n  reason: x\n---\n", {"reason": "y"})
        self.assertEqual(out, '---\nmeta:\n  reason: x\nreason: "y"\n---\n')

    def test_key_is_literal(self):
        out = self._run("---\naXb: 1\n---\n", {"a.b": "2"})
        self.assertEqual(out, '---\naXb: 1\na.b: "2"\n---\n')

    def test_body_untouched(self):
        body = "reason: im Rumpf\n\n---\nreason: auch\n"
        out = self._run("---\nid: X\n---\n" + body, {"reason": "neu"})
        self.assertEqual(out, '---\nid: X\nreason: "neu"\n---\n' + body)

    def test_trailing_whitespace_in_block_dropped_on_append(self):
        out = self._run("---\nid: X\n\n---\nB", {"a": "1"})
        self.assertEqual(out, '---\nid: X\na: "1"\n---\nB')

    def test_delimiter_spaces_preserved(self):
        out = self._run("---  \nid: X\n---\t\nB\nC\n", {"id": "Y"})
        self.assertEqual(out, '---  \nid: "Y"\n---\t\nB\nC\n')

    def test_empty_fields_no_change(self):
        text = "---\nid: X\n---\nB\n"
        self.assertEqual(self._run(text, {}), text)

    def test_no_frontmatter_raises_and_keeps_file(self):
        p = self.dir / "SPEC-0002-ohne.md"
        p.write_text("# Nur Rumpf\nid: X\n", encoding="utf-8")
        with self.assertRaises(FrontmatterError) as ctx:
            set_frontmatter_fields(p, {"id": "Y"})
        self.assertIn("SPEC-0002-ohne.md", str(ctx.exception))
        self.assertEqual(p.read_text(encoding="utf-8"), "# Nur Rumpf\nid: X\n")

    def test_error_is_exception(self):
        self.assertTrue(issubclass(FrontmatterError, Exception))


if __name__ == "__main__":
    unittest.main()
