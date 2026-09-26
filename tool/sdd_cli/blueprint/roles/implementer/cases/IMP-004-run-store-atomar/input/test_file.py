"""TST-0104: RunStore (SPEC-0104 FR-01, FR-03, FR-05)."""
import tempfile
import unittest
from pathlib import Path

from sddlib.run_store import RUN_ID_RE, RunStore, new_run_id


class RunStoreTest(unittest.TestCase):
    def test_fr01_format(self):
        run_id = new_run_id("SPEC-0042")
        treffer = RUN_ID_RE.match(run_id)
        self.assertIsNotNone(treffer)
        self.assertEqual(treffer.group(1), "SPEC-0042")

    def test_fr03_fr05_state_rundreise(self):
        with tempfile.TemporaryDirectory() as d:
            store = RunStore.create(Path(d), "SPEC-0042")
            self.assertTrue(store.dir.is_dir())
            store.write_state({"phase": "decompose"})
            self.assertEqual(store.read_state()["phase"], "decompose")


if __name__ == "__main__":
    unittest.main()
