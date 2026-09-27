"""Akzeptanztests SPEC-0002: bearbeiten, JSON-Persistenz und CLI."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def service(repo=None):
    from todo.service import TodoService

    return TodoService() if repo is None else TodoService(repo)


def datei_service(pfad):
    from todo.persistence import JsonFileRepository

    return service(JsonFileRepository(pfad))


def not_found():
    from todo.domain import TodoNotFoundError

    return TodoNotFoundError


def validation_error():
    from todo.domain import ValidationError

    return ValidationError


def storage_error():
    from todo.persistence import StorageError

    return StorageError


def cli(*args, datei=None, cwd=None):
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(filter(None, [str(ROOT), env.get("PYTHONPATH")]))
    argv = [sys.executable, "-m", "todo"]
    if datei is not None:
        argv += ["--file", str(datei)]
    return subprocess.run([*argv, *args], cwd=cwd or ROOT, env=env, capture_output=True,
                          text=True, timeout=60)


class TempDirTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.datei = self.tmp / "todo.json"

    def tearDown(self):
        self._tmp.cleanup()


class AbrufenErledigenTest(unittest.TestCase):
    def test_spec0002_fr01_get_liefert_die_aufgabe(self):
        svc = service()
        svc.add("A")
        svc.add("B")
        todo = svc.get(2)
        self.assertEqual((todo.id, todo.title, todo.done), (2, "B", False))

    def test_spec0002_fr01_complete_setzt_done(self):
        svc = service()
        svc.add("A")
        todo = svc.complete(1)
        self.assertEqual((todo.id, todo.done), (1, True))
        self.assertIs(svc.get(1).done, True)
        self.assertIs(svc.list_todos()[0].done, True)

    def test_spec0002_fr01_complete_zweimal_bleibt_erledigt(self):
        svc = service()
        svc.add("A")
        svc.complete(1)
        self.assertIs(svc.complete(1).done, True)
        self.assertIs(svc.get(1).done, True)

    def test_spec0002_fr01_unbekannte_id_wirft_not_found(self):
        self.assertTrue(issubclass(not_found(), LookupError))
        svc = service()
        svc.add("A")
        with self.assertRaises(not_found()):
            svc.get(99)
        with self.assertRaises(not_found()):
            svc.complete(99)


class OeffnenLoeschenTest(unittest.TestCase):
    def test_spec0002_fr02_reopen_setzt_done_zurueck(self):
        svc = service()
        svc.add("A")
        svc.complete(1)
        self.assertIs(svc.reopen(1).done, False)
        self.assertIs(svc.get(1).done, False)

    def test_spec0002_fr02_delete_entfernt_die_aufgabe(self):
        svc = service()
        svc.add("A")
        svc.add("B")
        svc.delete(1)
        self.assertEqual([t.id for t in svc.list_todos()], [2])
        with self.assertRaises(not_found()):
            svc.get(1)

    def test_spec0002_fr02_unbekannte_id_bei_reopen_und_delete(self):
        svc = service()
        with self.assertRaises(not_found()):
            svc.reopen(7)
        with self.assertRaises(not_found()):
            svc.delete(7)

    def test_spec0002_fr02_ids_werden_nicht_wiederverwendet(self):
        svc = service()
        svc.add("A")
        svc.add("B")
        svc.delete(2)
        self.assertEqual(svc.add("C").id, 3)
        svc.delete(1)
        svc.delete(3)
        self.assertEqual(svc.add("D").id, 4)


class UmbenennenTest(unittest.TestCase):
    def test_spec0002_fr03_rename_aendert_und_bereinigt_titel(self):
        svc = service()
        svc.add("Alt")
        todo = svc.rename(1, "  Neu ")
        self.assertEqual((todo.id, todo.title), (1, "Neu"))
        self.assertEqual(svc.get(1).title, "Neu")

    def test_spec0002_fr03_ungueltiger_titel_laesst_alten_titel(self):
        svc = service()
        svc.add("Alt")
        for titel in ("", "   ", "x" * 201, None):
            with self.subTest(titel=titel), self.assertRaises(validation_error()):
                svc.rename(1, titel)
        self.assertEqual(svc.get(1).title, "Alt")

    def test_spec0002_fr03_unbekannte_id(self):
        with self.assertRaises(not_found()):
            service().rename(5, "Neu")


class PersistenzTest(TempDirTest):
    def test_spec0002_fr04_zustand_ueberdauert_neustart(self):
        svc = datei_service(self.datei)
        svc.add("A")
        svc.add("B")
        svc.complete(1)
        neu = datei_service(self.datei)
        self.assertEqual([(t.id, t.title, t.done) for t in neu.list_todos()],
                         [(1, "A", True), (2, "B", False)])

    def test_spec0002_fr04_pfad_als_str_und_path(self):
        datei_service(str(self.datei)).add("A")
        self.assertEqual([t.title for t in datei_service(self.datei).list_todos()], ["A"])

    def test_spec0002_fr04_fehlende_datei_ist_leer_und_entsteht_bei_erster_aenderung(self):
        svc = datei_service(self.datei)
        self.assertEqual(svc.list_todos(), [])
        self.assertFalse(self.datei.exists())
        svc.add("A")
        self.assertTrue(self.datei.exists())

    def test_spec0002_fr04_ids_werden_nach_neustart_fortgesetzt(self):
        svc = datei_service(self.datei)
        svc.add("A")
        svc.add("B")
        svc.delete(2)
        self.assertEqual(datei_service(self.datei).add("C").id, 3)

    def test_spec0002_fr04_jede_aenderung_wird_gespeichert(self):
        svc = datei_service(self.datei)
        svc.add("A")
        svc.add("B")
        svc.rename(1, "A2")
        svc.complete(2)
        svc.reopen(2)
        svc.complete(1)
        svc.delete(2)
        neu = datei_service(self.datei)
        self.assertEqual([(t.id, t.title, t.done) for t in neu.list_todos()], [(1, "A2", True)])

    def test_spec0002_fr04_dateiformat(self):
        svc = datei_service(self.datei)
        svc.add("A")
        svc.add("B")
        svc.complete(2)
        daten = json.loads(self.datei.read_text(encoding="utf-8"))
        self.assertEqual(daten["next_id"], 3)
        self.assertEqual([(e["id"], e["title"], e["done"]) for e in daten["todos"]],
                         [(1, "A", False), (2, "B", True)])

    def test_spec0002_fr04_datei_im_format_wird_geladen(self):
        self.datei.write_text(json.dumps({"next_id": 10, "todos": [
            {"id": 3, "title": "Drei", "done": True},
            {"id": 7, "title": "Sieben", "done": False}]}), encoding="utf-8")
        svc = datei_service(self.datei)
        self.assertEqual([(t.id, t.title, t.done) for t in svc.list_todos()],
                         [(3, "Drei", True), (7, "Sieben", False)])
        self.assertEqual(svc.add("Neu").id, 10)


class BeschaedigteDateiTest(TempDirTest):
    FAELLE = {
        "kein_json": "{kaputt",
        "leer": "",
        "liste_statt_objekt": "[]",
        "ohne_todos": '{"next_id": 1}',
        "eintrag_ohne_id": '{"next_id": 2, "todos": [{"title": "x", "done": false}]}',
    }

    def _pruefe(self, inhalt):
        self.datei.write_text(inhalt, encoding="utf-8")
        vorher = self.datei.read_bytes()
        with self.assertRaises(storage_error()):
            datei_service(self.datei).list_todos()
        self.assertEqual(self.datei.read_bytes(), vorher)

    def test_spec0002_fr05_storage_error_ist_exception(self):
        self.assertTrue(issubclass(storage_error(), Exception))

    def test_spec0002_fr05_ungueltiges_json(self):
        self._pruefe(self.FAELLE["kein_json"])

    def test_spec0002_fr05_leere_datei(self):
        self._pruefe(self.FAELLE["leer"])

    def test_spec0002_fr05_falsche_struktur(self):
        for name in ("liste_statt_objekt", "ohne_todos", "eintrag_ohne_id"):
            with self.subTest(fall=name):
                self._pruefe(self.FAELLE[name])


class CliTest(TempDirTest):
    def test_spec0002_fr06_add_gibt_id_und_titel_aus(self):
        r = cli("add", "  Brot ", datei=self.datei)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), "#1 Brot")
        r = cli("add", "Milch", datei=self.datei)
        self.assertEqual(r.stdout.strip(), "#2 Milch")

    def test_spec0002_fr06_list_zeigt_status_und_reihenfolge(self):
        cli("add", "A", datei=self.datei)
        cli("add", "B", datei=self.datei)
        self.assertEqual(cli("done", "2", datei=self.datei).returncode, 0)
        r = cli("list", datei=self.datei)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.splitlines(), ["[ ] #1 A", "[x] #2 B"])

    def test_spec0002_fr06_list_ohne_aufgaben_ohne_ausgabe(self):
        r = cli("list", datei=self.datei)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), "")

    def test_spec0002_fr06_reopen_und_delete(self):
        for titel in ("A", "B", "C"):
            cli("add", titel, datei=self.datei)
        cli("done", "1", datei=self.datei)
        self.assertEqual(cli("reopen", "1", datei=self.datei).returncode, 0)
        self.assertEqual(cli("delete", "2", datei=self.datei).returncode, 0)
        r = cli("list", datei=self.datei)
        self.assertEqual(r.stdout.splitlines(), ["[ ] #1 A", "[ ] #3 C"])

    def test_spec0002_fr06_datei_ist_mit_der_service_api_lesbar(self):
        cli("add", "A", datei=self.datei)
        cli("done", "1", datei=self.datei)
        todo = datei_service(self.datei).get(1)
        self.assertEqual((todo.title, todo.done), ("A", True))

    def test_spec0002_fr06_default_datei_im_arbeitsverzeichnis(self):
        r = cli("add", "A", cwd=self.tmp)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((self.tmp / "todo.json").is_file())
        self.assertEqual(cli("list", cwd=self.tmp).stdout.splitlines(), ["[ ] #1 A"])

    def test_spec0002_fr06_unbekannte_id_exit_1(self):
        cli("add", "A", datei=self.datei)
        vorher = self.datei.read_bytes()
        for befehl in ("done", "reopen", "delete"):
            with self.subTest(befehl=befehl):
                r = cli(befehl, "99", datei=self.datei)
                self.assertEqual(r.returncode, 1)
                self.assertEqual(r.stdout, "")
                self.assertNotEqual(r.stderr.strip(), "")
        self.assertEqual(self.datei.read_bytes(), vorher)

    def test_spec0002_fr06_leerer_titel_exit_1(self):
        r = cli("add", "   ", datei=self.datei)
        self.assertEqual(r.returncode, 1)
        self.assertEqual(r.stdout, "")
        self.assertNotEqual(r.stderr.strip(), "")
        self.assertEqual(cli("list", datei=self.datei).stdout.strip(), "")

    def test_spec0002_fr06_beschaedigte_datei_exit_1(self):
        self.datei.write_text("{kaputt", encoding="utf-8")
        for args in (("list",), ("add", "A")):
            with self.subTest(args=args):
                r = cli(*args, datei=self.datei)
                self.assertEqual(r.returncode, 1)
                self.assertEqual(r.stdout, "")
                self.assertNotEqual(r.stderr.strip(), "")
                self.assertNotIn("Traceback", r.stderr)
        self.assertEqual(self.datei.read_text(encoding="utf-8"), "{kaputt")


if __name__ == "__main__":
    unittest.main()
