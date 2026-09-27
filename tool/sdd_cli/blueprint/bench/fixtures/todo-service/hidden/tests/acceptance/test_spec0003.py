"""Akzeptanztests SPEC-0003: Tags, Fälligkeiten, Filter, Export, Undo, CLI und Schichtregeln."""
import ast
import csv
import datetime as dt
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
D = dt.date


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


def cli(*args, datei):
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(filter(None, [str(ROOT), env.get("PYTHONPATH")]))
    return subprocess.run([sys.executable, "-m", "todo", "--file", str(datei), *args], cwd=ROOT,
                          env=env, capture_output=True, text=True, timeout=60)


def zustand(svc):
    return [(t.id, t.title, t.done, tuple(t.tags), t.due) for t in svc.list_todos()]


class TempDirTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.datei = self.tmp / "todo.json"

    def tearDown(self):
        self._tmp.cleanup()


class TagsAnlegenTest(unittest.TestCase):
    def test_spec0003_fr01_tags_werden_normalisiert_und_sortiert(self):
        todo = service().add("A", tags=["Home", " work ", "home", "a-1"])
        self.assertIsInstance(todo.tags, tuple)
        self.assertEqual(todo.tags, ("a-1", "home", "work"))

    def test_spec0003_fr01_ohne_tags_leeres_tupel(self):
        svc = service()
        self.assertEqual(svc.add("A").tags, ())
        self.assertEqual(svc.list_todos()[0].tags, ())

    def test_spec0003_fr01_tag_mit_20_zeichen_ist_erlaubt(self):
        self.assertEqual(service().add("A", tags=["t" * 20]).tags, ("t" * 20,))

    def test_spec0003_fr01_ungueltige_tags_werden_abgelehnt(self):
        svc = service()
        for tag in ("", "   ", "mit leer", "t" * 21, "über", "a_b", "x!"):
            with self.subTest(tag=tag), self.assertRaises(validation_error()):
                svc.add("A", tags=["ok", tag])
        self.assertEqual(svc.list_todos(), [])
        self.assertEqual(svc.add("B").id, 1)

    def test_spec0003_fr01_add_mit_nur_titel_bleibt_gueltig(self):
        todo = service().add("Nur Titel")
        self.assertEqual((todo.id, todo.title, todo.done), (1, "Nur Titel", False))


class TagsAendernTest(unittest.TestCase):
    def test_spec0003_fr02_tag_fuegt_hinzu(self):
        svc = service()
        svc.add("A", tags=["b"])
        todo = svc.tag(1, "C", "a", "b")
        self.assertEqual(todo.tags, ("a", "b", "c"))
        self.assertEqual(svc.get(1).tags, ("a", "b", "c"))

    def test_spec0003_fr02_untag_entfernt(self):
        svc = service()
        svc.add("A", tags=["a", "b", "c"])
        todo = svc.untag(1, "B", "fehlt")
        self.assertEqual(todo.tags, ("a", "c"))
        self.assertEqual(svc.get(1).tags, ("a", "c"))

    def test_spec0003_fr02_ungueltiger_tag_laesst_aufgabe_unveraendert(self):
        svc = service()
        svc.add("A", tags=["a"])
        with self.assertRaises(validation_error()):
            svc.tag(1, "neu", "nicht gültig")
        with self.assertRaises(validation_error()):
            svc.untag(1, "a", "")
        self.assertEqual(svc.get(1).tags, ("a",))

    def test_spec0003_fr02_unbekannte_id(self):
        svc = service()
        with self.assertRaises(not_found()):
            svc.tag(9, "a")
        with self.assertRaises(not_found()):
            svc.untag(9, "a")


class FaelligkeitTest(unittest.TestCase):
    def test_spec0003_fr03_add_mit_due(self):
        svc = service()
        self.assertEqual(svc.add("A", due=D(2026, 10, 1)).due, D(2026, 10, 1))
        self.assertIsNone(svc.add("B").due)

    def test_spec0003_fr03_set_due_setzt_und_entfernt(self):
        svc = service()
        svc.add("A")
        self.assertEqual(svc.set_due(1, D(2026, 12, 24)).due, D(2026, 12, 24))
        self.assertEqual(svc.get(1).due, D(2026, 12, 24))
        self.assertIsNone(svc.set_due(1, None).due)
        self.assertIsNone(svc.get(1).due)

    def test_spec0003_fr03_ungueltige_werte(self):
        svc = service()
        svc.add("A", due=D(2026, 1, 1))
        for wert in ("2026-02-01", dt.datetime(2026, 2, 1, 12, 0), 20260201):
            with self.subTest(wert=wert):
                with self.assertRaises(validation_error()):
                    svc.set_due(1, wert)
                with self.assertRaises(validation_error()):
                    svc.add("B", due=wert)
        self.assertEqual(svc.get(1).due, D(2026, 1, 1))
        self.assertEqual(len(svc.list_todos()), 1)

    def test_spec0003_fr03_unbekannte_id(self):
        with self.assertRaises(not_found()):
            service().set_due(3, D(2026, 1, 1))


class UeberfaelligTest(unittest.TestCase):
    def test_spec0003_fr04_sortiert_nach_datum_dann_id(self):
        svc = service()
        svc.add("A", due=D(2026, 1, 10))
        svc.add("B", due=D(2026, 1, 5))
        svc.add("C", due=D(2026, 1, 10))
        svc.add("D", due=D(2026, 1, 1))
        self.assertEqual([t.title for t in svc.overdue(D(2026, 1, 20))], ["D", "B", "A", "C"])

    def test_spec0003_fr04_ausschluesse(self):
        svc = service()
        svc.add("ohne Datum")
        svc.add("erledigt", due=D(2026, 1, 1))
        svc.complete(2)
        svc.add("heute", due=D(2026, 1, 20))
        svc.add("zukunft", due=D(2026, 2, 1))
        svc.add("gestern", due=D(2026, 1, 19))
        self.assertEqual([t.title for t in svc.overdue(D(2026, 1, 20))], ["gestern"])

    def test_spec0003_fr04_leer_ohne_treffer(self):
        svc = service()
        svc.add("A")
        self.assertEqual(svc.overdue(D(2030, 1, 1)), [])


class FilterTest(unittest.TestCase):
    def setUp(self):
        self.svc = service()
        self.svc.add("Milch kaufen", tags=["einkauf"], due=D(2026, 3, 1))
        self.svc.add("Steuer machen", tags=["buero"], due=D(2026, 5, 31))
        self.svc.add("Brot KAUFEN", tags=["einkauf", "dringend"])
        self.svc.add("Arzt anrufen")
        self.svc.complete(1)

    def ids(self, **kw):
        return [t.id for t in self.svc.list_todos(**kw)]

    def test_spec0003_fr05_nach_status(self):
        self.assertEqual(self.ids(done=True), [1])
        self.assertEqual(self.ids(done=False), [2, 3, 4])

    def test_spec0003_fr05_nach_tag_ohne_gross_klein(self):
        self.assertEqual(self.ids(tag="einkauf"), [1, 3])
        self.assertEqual(self.ids(tag="EINKAUF"), [1, 3])
        self.assertEqual(self.ids(tag="unbekannt"), [])

    def test_spec0003_fr05_due_before_ist_echt_davor(self):
        self.assertEqual(self.ids(due_before=D(2026, 5, 31)), [1])
        self.assertEqual(self.ids(due_before=D(2026, 6, 1)), [1, 2])

    def test_spec0003_fr05_text_ohne_gross_klein(self):
        self.assertEqual(self.ids(text="kaufen"), [1, 3])
        self.assertEqual(self.ids(text="ARZT"), [4])

    def test_spec0003_fr05_kriterien_werden_kombiniert(self):
        self.assertEqual(self.ids(tag="einkauf", done=False), [3])
        self.assertEqual(self.ids(text="kaufen", due_before=D(2027, 1, 1)), [1])
        self.assertEqual(self.ids(done=True, tag="buero"), [])

    def test_spec0003_fr05_ohne_argumente_alle(self):
        self.assertEqual(self.ids(), [1, 2, 3, 4])
        self.assertEqual(self.ids(done=None, tag=None, due_before=None, text=None), [1, 2, 3, 4])


class ExportTest(unittest.TestCase):
    def _svc(self):
        svc = service()
        svc.add("Milch, frisch", tags=["einkauf", "b"], due=D(2026, 3, 1))
        svc.add('Sag "Hallo"')
        svc.complete(2)
        return svc

    def test_spec0003_fr06_json(self):
        daten = json.loads(self._svc().export_json())
        self.assertEqual(daten, [
            {"id": 1, "title": "Milch, frisch", "done": False, "tags": ["b", "einkauf"],
             "due": "2026-03-01"},
            {"id": 2, "title": 'Sag "Hallo"', "done": True, "tags": [], "due": None},
        ])

    def test_spec0003_fr06_json_leer(self):
        self.assertEqual(json.loads(service().export_json()), [])

    def test_spec0003_fr06_csv(self):
        zeilen = list(csv.reader(io.StringIO(self._svc().export_csv())))
        self.assertEqual(zeilen, [
            ["id", "title", "done", "tags", "due"],
            ["1", "Milch, frisch", "false", "b;einkauf", "2026-03-01"],
            ["2", 'Sag "Hallo"', "true", "", ""],
        ])

    def test_spec0003_fr06_csv_quoting(self):
        text = self._svc().export_csv()
        self.assertIn('"Milch, frisch"', text)
        self.assertIn('"Sag ""Hallo"""', text)

    def test_spec0003_fr06_csv_leer_nur_kopfzeile(self):
        zeilen = list(csv.reader(io.StringIO(service().export_csv())))
        self.assertEqual(zeilen, [["id", "title", "done", "tags", "due"]])


class UndoTest(TempDirTest):
    def test_spec0003_fr07_ohne_aenderung_false(self):
        svc = service()
        self.assertIs(svc.undo(), False)
        svc2 = service()
        svc2.add("A")
        self.assertIs(svc2.undo(), True)
        self.assertIs(svc2.undo(), False)
        self.assertEqual(svc2.list_todos(), [])

    def test_spec0003_fr07_loeschen_rueckgaengig(self):
        svc = service()
        svc.add("A", tags=["home"], due=D(2026, 4, 1))
        svc.complete(1)
        svc.delete(1)
        self.assertIs(svc.undo(), True)
        todo = svc.get(1)
        self.assertEqual((todo.id, todo.title, todo.done, tuple(todo.tags), todo.due),
                         (1, "A", True, ("home",), D(2026, 4, 1)))

    def test_spec0003_fr07_jede_aenderung_ist_ein_schritt(self):
        svc = service()
        schritte = []
        svc.add("A")
        schritte.append(zustand(svc))
        svc.add("B")
        schritte.append(zustand(svc))
        svc.complete(1)
        schritte.append(zustand(svc))
        svc.reopen(1)
        schritte.append(zustand(svc))
        svc.rename(2, "B2")
        schritte.append(zustand(svc))
        svc.tag(2, "x")
        schritte.append(zustand(svc))
        svc.untag(2, "x")
        schritte.append(zustand(svc))
        svc.set_due(1, D(2026, 1, 1))
        schritte.append(zustand(svc))
        svc.delete(2)
        for erwartet in reversed(schritte):
            self.assertIs(svc.undo(), True)
            self.assertEqual(zustand(svc), erwartet)
        self.assertIs(svc.undo(), True)
        self.assertEqual(svc.list_todos(), [])
        self.assertIs(svc.undo(), False)

    def test_spec0003_fr07_fehlschlaege_erzeugen_keinen_schritt(self):
        svc = service()
        svc.add("A")
        svc.rename(1, "A2")
        for aufruf in (lambda: svc.add(""), lambda: svc.rename(1, ""),
                       lambda: svc.complete(99), lambda: svc.tag(1, "nicht ok")):
            with self.assertRaises((validation_error(), not_found())):
                aufruf()
        self.assertIs(svc.undo(), True)
        self.assertEqual(svc.get(1).title, "A")

    def test_spec0003_fr07_undo_wird_gespeichert(self):
        svc = datei_service(self.datei)
        svc.add("A")
        svc.add("B")
        svc.undo()
        self.assertEqual([t.title for t in datei_service(self.datei).list_todos()], ["A"])

    def test_spec0003_fr07_historie_beginnt_beim_erzeugen(self):
        datei_service(self.datei).add("A")
        svc = datei_service(self.datei)
        self.assertIs(svc.undo(), False)
        self.assertEqual([t.title for t in svc.list_todos()], ["A"])


class PersistenzNeueFelderTest(TempDirTest):
    def test_spec0003_fr08_tags_und_due_ueberdauern_neustart(self):
        svc = datei_service(self.datei)
        svc.add("A", tags=["x", "a"], due=D(2026, 7, 4))
        svc.add("B")
        neu = datei_service(self.datei)
        self.assertEqual(zustand(neu), [(1, "A", False, ("a", "x"), D(2026, 7, 4)),
                                        (2, "B", False, (), None)])

    def test_spec0003_fr08_dateiformat_mit_tags_und_due(self):
        svc = datei_service(self.datei)
        svc.add("A", tags=["x"], due=D(2026, 7, 4))
        svc.add("B")
        eintraege = json.loads(self.datei.read_text(encoding="utf-8"))["todos"]
        self.assertEqual([(e["tags"], e["due"]) for e in eintraege],
                         [(["x"], "2026-07-04"), ([], None)])

    def test_spec0003_fr08_altes_format_wird_geladen(self):
        self.datei.write_text(json.dumps({"next_id": 3, "todos": [
            {"id": 1, "title": "Alt", "done": True},
            {"id": 2, "title": "Neu", "done": False, "tags": ["t"], "due": "2026-01-02"}]}),
            encoding="utf-8")
        svc = datei_service(self.datei)
        self.assertEqual(zustand(svc), [(1, "Alt", True, (), None),
                                        (2, "Neu", False, ("t",), D(2026, 1, 2))])
        self.assertEqual(svc.add("C").id, 3)

    def test_spec0003_fr08_ungueltiges_datum_ist_beschaedigt(self):
        self.datei.write_text(json.dumps({"next_id": 2, "todos": [
            {"id": 1, "title": "A", "done": False, "tags": [], "due": "2026-13-45"}]}),
            encoding="utf-8")
        vorher = self.datei.read_bytes()
        with self.assertRaises(storage_error()):
            datei_service(self.datei).list_todos()
        self.assertEqual(self.datei.read_bytes(), vorher)


class CliErweitertTest(TempDirTest):
    def ok(self, *args):
        r = cli(*args, datei=self.datei)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def test_spec0003_fr09_add_mit_tags_und_due(self):
        out = self.ok("add", "Milch", "--tag", "Einkauf", "--tag", "b", "--due", "2026-03-01")
        self.assertEqual(out.strip(), "#1 Milch")
        todo = datei_service(self.datei).get(1)
        self.assertEqual((tuple(todo.tags), todo.due), (("b", "einkauf"), D(2026, 3, 1)))

    def test_spec0003_fr09_list_zeilenformat(self):
        self.ok("add", "Milch", "--tag", "einkauf", "--tag", "b", "--due", "2026-03-01")
        self.ok("add", "Nur Datum", "--due", "2026-04-01")
        self.ok("add", "Nur Tag", "--tag", "x")
        self.ok("add", "Schlicht")
        self.assertEqual(self.ok("list").splitlines(), [
            "[ ] #1 Milch due:2026-03-01 tags:b,einkauf",
            "[ ] #2 Nur Datum due:2026-04-01",
            "[ ] #3 Nur Tag tags:x",
            "[ ] #4 Schlicht",
        ])

    def test_spec0003_fr09_list_filter(self):
        self.ok("add", "Milch kaufen", "--tag", "einkauf")
        self.ok("add", "Steuer")
        self.ok("add", "Brot kaufen", "--tag", "einkauf")
        self.ok("done", "3")
        self.assertEqual(self.ok("list", "--tag", "einkauf").splitlines(),
                         ["[ ] #1 Milch kaufen tags:einkauf", "[x] #3 Brot kaufen tags:einkauf"])
        self.assertEqual(self.ok("list", "--open").splitlines(),
                         ["[ ] #1 Milch kaufen tags:einkauf", "[ ] #2 Steuer"])
        self.assertEqual(self.ok("list", "--done").splitlines(),
                         ["[x] #3 Brot kaufen tags:einkauf"])
        self.assertEqual(self.ok("list", "--search", "KAUFEN", "--open").splitlines(),
                         ["[ ] #1 Milch kaufen tags:einkauf"])

    def test_spec0003_fr09_export(self):
        self.ok("add", "Milch, frisch", "--tag", "einkauf", "--due", "2026-03-01")
        self.ok("add", "B")
        daten = json.loads(self.ok("export", "--format", "json"))
        self.assertEqual([(e["id"], e["title"], e["tags"], e["due"]) for e in daten],
                         [(1, "Milch, frisch", ["einkauf"], "2026-03-01"), (2, "B", [], None)])
        zeilen = list(csv.reader(io.StringIO(self.ok("export", "--format", "csv"))))
        self.assertEqual(zeilen, [["id", "title", "done", "tags", "due"],
                                  ["1", "Milch, frisch", "false", "einkauf", "2026-03-01"],
                                  ["2", "B", "false", "", ""]])

    def test_spec0003_fr09_ungueltiges_datum_oder_tag_exit_1(self):
        self.ok("add", "A")
        vorher = self.datei.read_bytes()
        for args in (("add", "B", "--due", "2026-02-30"), ("add", "B", "--due", "morgen"),
                     ("add", "B", "--tag", "nicht gültig")):
            with self.subTest(args=args):
                r = cli(*args, datei=self.datei)
                self.assertEqual(r.returncode, 1)
                self.assertEqual(r.stdout, "")
                self.assertNotEqual(r.stderr.strip(), "")
        self.assertEqual(self.datei.read_bytes(), vorher)


# ── FR-10: Schichtregeln (statische Prüfung der Importe) ──────────────────────

SCHICHTEN = ("domain", "service", "persistence", "cli")
ERLAUBT = {"domain": set(), "service": {"domain"}, "persistence": {"domain"},
           "cli": {"service", "domain"}}
IO_MODULE = {"os", "io", "pathlib", "json", "csv", "shutil", "subprocess", "tempfile"}


def _importe(datei: Path) -> set[str]:
    """Absolute Modulnamen aller Importe einer Datei (relative aufgelöst, dynamische mit Literal)."""
    rel = datei.relative_to(ROOT).with_suffix("")
    teile = list(rel.parts)
    paket = teile if teile[-1] == "__init__" else teile[:-1]
    if paket and paket[-1] == "__init__":
        paket = paket[:-1]
    namen = set()
    for knoten in ast.walk(ast.parse(datei.read_text(encoding="utf-8"))):
        if isinstance(knoten, ast.Import):
            namen.update(a.name for a in knoten.names)
        elif isinstance(knoten, ast.ImportFrom):
            if knoten.level:
                basis = paket[: len(paket) - (knoten.level - 1)]
                modul = ".".join([*basis, *([knoten.module] if knoten.module else [])])
            else:
                modul = knoten.module or ""
            namen.add(modul)
            namen.update(f"{modul}.{a.name}" for a in knoten.names)
        elif isinstance(knoten, ast.Call) and knoten.args \
                and isinstance(knoten.args[0], ast.Constant) \
                and isinstance(knoten.args[0].value, str):
            f = knoten.func
            name = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
            if name in ("import_module", "__import__"):
                namen.add(knoten.args[0].value)
    return namen


def _schichtimporte(schicht: str) -> dict[str, set[str]]:
    """Datei → importierte todo-Schichten (ohne die eigene)."""
    ergebnis = {}
    for datei in sorted((ROOT / "todo" / schicht).rglob("*.py")):
        ziele = set()
        for name in _importe(datei):
            teile = name.split(".")
            if teile[0] == "todo" and len(teile) > 1 and teile[1] in SCHICHTEN \
                    and teile[1] != schicht:
                ziele.add(teile[1])
        ergebnis[str(datei.relative_to(ROOT))] = ziele
    return ergebnis


class SchichtregelnTest(unittest.TestCase):
    def setUp(self):
        from todo.persistence import JsonFileRepository
        from todo.service import TodoService

        self.repo_cls, self.service_cls = JsonFileRepository, TodoService

    def test_spec0003_fr10_klassen_liegen_in_ihren_schichten(self):
        self.assertTrue(self.repo_cls.__module__.startswith("todo.persistence"))
        self.assertTrue(self.service_cls.__module__.startswith("todo.service"))

    def test_spec0003_fr10_importe_folgen_den_schichtregeln(self):
        verstoesse = []
        for schicht in SCHICHTEN:
            for datei, ziele in _schichtimporte(schicht).items():
                for ziel in sorted(ziele - ERLAUBT[schicht]):
                    verstoesse.append(f"{datei} → todo.{ziel}")
        self.assertEqual(verstoesse, [])

    def test_spec0003_fr10_service_kennt_die_persistenz_nicht(self):
        for datei, ziele in _schichtimporte("service").items():
            self.assertNotIn("persistence", ziele, datei)
        self.assertTrue(any((ROOT / "todo" / "service").rglob("*.py")))

    def test_spec0003_fr10_domain_ohne_datei_und_prozesszugriff(self):
        dateien = sorted((ROOT / "todo" / "domain").rglob("*.py"))
        self.assertTrue(dateien)
        for datei in dateien:
            io_importe = {n.split(".")[0] for n in _importe(datei)} & IO_MODULE
            self.assertEqual(io_importe, set(), str(datei.relative_to(ROOT)))


if __name__ == "__main__":
    unittest.main()
