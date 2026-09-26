"""Versteckte Tests zu SPEC-0104 (FR-01 bis FR-06)."""
import json
import re
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sddlib.run_store import (
    RUN_ID_RE,
    RunNotFound,
    RunStore,
    atomic_write_json,
    new_run_id,
    now,
)


class HiddenRunIdTest(unittest.TestCase):
    def test_fr01_zeitstempel_utc(self):
        run_id = new_run_id("SPEC-0007")
        m = re.fullmatch(r"SPEC-0007-(\d{8}T\d{6})-([0-9a-z]+)", run_id)
        self.assertIsNotNone(m, run_id)
        stempel = datetime.strptime(m.group(1), "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)
        self.assertLess(abs(datetime.now(timezone.utc) - stempel), timedelta(seconds=5))

    def test_fr01_eindeutig(self):
        ids = {new_run_id("SPEC-0007") for _ in range(50)}
        self.assertEqual(len(ids), 50)

    def test_fr01_regex_grenzen(self):
        self.assertIsNotNone(RUN_ID_RE.match("SPEC-0001-20260101T120000-ab12cd"))
        for falsch in ("SPEC-01-20260101T120000-ab", "SPEC-0001-20260101-120000-ab",
                       "SPEC-0001-20260101T120000-AB", "SPEC-0001-20260101T120000-",
                       "x/SPEC-0001-20260101T120000-ab", "SPEC-0001-20260101T120000-ab/.."):
            self.assertIsNone(RUN_ID_RE.match(falsch), falsch)

    def test_fr01_now_utc(self):
        wert = now()
        self.assertRegex(wert, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
        zeit = datetime.strptime(wert, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        self.assertLess(abs(datetime.now(timezone.utc) - zeit), timedelta(seconds=5))


class HiddenAtomicTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_fr02_format_und_elternverzeichnisse(self):
        ziel = self.root / "a" / "b" / "x.json"
        atomic_write_json(ziel, {"name": "Größe", "n": [1]})
        text = ziel.read_text(encoding="utf-8")
        self.assertIn("Größe", text)
        self.assertTrue(text.endswith("\n"))
        self.assertIn('\n  "name"', text)
        self.assertEqual(json.loads(text), {"name": "Größe", "n": [1]})
        self.assertEqual(sorted(p.name for p in ziel.parent.iterdir()), ["x.json"])

    def test_fr02_ueberschreiben(self):
        ziel = self.root / "x.json"
        atomic_write_json(ziel, {"v": 1})
        atomic_write_json(ziel, {"v": 2})
        self.assertEqual(json.loads(ziel.read_text(encoding="utf-8")), {"v": 2})
        self.assertEqual([p.name for p in self.root.iterdir()], ["x.json"])

    def test_fr02_fehler_laesst_alte_datei_und_keine_reste(self):
        ziel = self.root / "x.json"
        atomic_write_json(ziel, {"v": 1})
        vorher = ziel.read_text(encoding="utf-8")
        with self.assertRaises(TypeError):
            atomic_write_json(ziel, {"v": object()})
        self.assertEqual(ziel.read_text(encoding="utf-8"), vorher)
        self.assertEqual([p.name for p in self.root.iterdir()], ["x.json"])

    def test_fr02_fehler_ohne_bestehende_datei(self):
        ziel = self.root / "neu.json"
        with self.assertRaises(TypeError):
            atomic_write_json(ziel, {1, 2})
        self.assertEqual(list(self.root.iterdir()), [])


class HiddenStoreTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_fr03_verzeichnis_und_attribute(self):
        store = RunStore.create(self.root, "SPEC-0042")
        self.assertEqual(store.spec_id, "SPEC-0042")
        self.assertEqual(store.root, self.root)
        self.assertEqual(store.dir, self.root / ".sdd" / "runs" / "SPEC-0042" / store.run_id)
        self.assertIsNotNone(RUN_ID_RE.match(store.run_id))

    def test_fr03_vorgegebene_id(self):
        rid = "SPEC-0042-20260101T120000-abc123"
        store = RunStore.create(self.root, "SPEC-0042", rid)
        self.assertEqual(store.run_id, rid)
        self.assertTrue(store.dir.is_dir())

    def test_fr03_vorgegebene_id_falsch(self):
        with self.assertRaises(ValueError):
            RunStore.create(self.root, "SPEC-0042", "SPEC-0043-20260101T120000-abc123")
        with self.assertRaises(ValueError):
            RunStore.create(self.root, "SPEC-0042", "../../etc")
        self.assertFalse((self.root / ".sdd").exists())

    def test_fr03_existiert_schon(self):
        rid = "SPEC-0042-20260101T120000-abc123"
        RunStore.create(self.root, "SPEC-0042", rid)
        with self.assertRaises(FileExistsError):
            RunStore.create(self.root, "SPEC-0042", rid)

    def test_fr04_open(self):
        store = RunStore.create(self.root, "SPEC-0042")
        store.write_state({"phase": "x"})
        offen = RunStore.open(self.root, store.run_id)
        self.assertEqual(offen.spec_id, "SPEC-0042")
        self.assertEqual(offen.dir, store.dir)

    def test_fr04_open_fehler(self):
        store = RunStore.create(self.root, "SPEC-0042")
        with self.assertRaises(RunNotFound):
            RunStore.open(self.root, store.run_id)  # noch kein state.json
        with self.assertRaises(RunNotFound):
            RunStore.open(self.root, "kaputt")
        with self.assertRaises(RunNotFound):
            RunStore.open(self.root, "SPEC-0042-20260101T120000-ffffff")

    def test_fr05_updated_at(self):
        store = RunStore.create(self.root, "SPEC-0042")
        state = {"phase": "x"}
        store.write_state(state)
        self.assertRegex(state["updated_at"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
        self.assertEqual(store.read_state(), state)
        self.assertEqual(sorted(p.name for p in store.dir.iterdir()), ["state.json"])

    def test_fr06_ereignisse(self):
        store = RunStore.create(self.root, "SPEC-0042")
        self.assertEqual(store.read_jsonl("events.jsonl"), [])
        store.event("task_started", task_id="T01", hint=None)
        store.event("task_done", task_id="T01", note="grün ✓")
        zeilen = (store.dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(zeilen), 2)
        self.assertIn("✓", zeilen[1])
        events = store.read_jsonl("events.jsonl")
        self.assertEqual(events[0]["type"], "task_started")
        self.assertEqual(events[0]["run_id"], store.run_id)
        self.assertNotIn("hint", events[0])
        self.assertEqual(set(events[0]), {"ts", "run_id", "type", "task_id"})
        self.assertRegex(events[1]["ts"], r"Z$")

    def test_fr06_leerzeilen(self):
        store = RunStore.create(self.root, "SPEC-0042")
        (store.dir / "x.jsonl").write_text('{"a": 1}\n\n  \n{"a": 2}\n', encoding="utf-8")
        self.assertEqual(store.read_jsonl("x.jsonl"), [{"a": 1}, {"a": 2}])


if __name__ == "__main__":
    unittest.main()
