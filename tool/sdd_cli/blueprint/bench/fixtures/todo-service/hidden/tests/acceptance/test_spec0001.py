"""Akzeptanztests SPEC-0001: Aufgaben anlegen und auflisten."""
import unittest


def neuer_service():
    from todo.service import TodoService

    return TodoService()


def validation_error():
    from todo.domain import ValidationError

    return ValidationError


class AnlegenTest(unittest.TestCase):
    def test_spec0001_fr01_neuer_service_ist_leer(self):
        self.assertEqual(neuer_service().list_todos(), [])

    def test_spec0001_fr01_add_gibt_todo_mit_id_titel_und_status_zurueck(self):
        from todo.domain import Todo

        todo = neuer_service().add("Milch kaufen")
        self.assertIsInstance(todo, Todo)
        self.assertEqual(todo.id, 1)
        self.assertEqual(todo.title, "Milch kaufen")
        self.assertIs(todo.done, False)

    def test_spec0001_fr01_ids_sind_fortlaufend_ab_eins(self):
        svc = neuer_service()
        ids = [svc.add(t).id for t in ("A", "B", "C")]
        self.assertEqual(ids, [1, 2, 3])
        self.assertTrue(all(type(i) is int for i in ids))

    def test_spec0001_fr01_titel_wird_an_den_enden_bereinigt(self):
        svc = neuer_service()
        self.assertEqual(svc.add("   Steuer  machen  ").title, "Steuer  machen")
        self.assertEqual(svc.list_todos()[0].title, "Steuer  machen")


class ValidierungTest(unittest.TestCase):
    def test_spec0001_fr02_validation_error_ist_value_error(self):
        self.assertTrue(issubclass(validation_error(), ValueError))

    def test_spec0001_fr02_leerer_titel_wird_abgelehnt(self):
        svc = neuer_service()
        for titel in ("", "   "):
            with self.subTest(titel=titel), self.assertRaises(validation_error()):
                svc.add(titel)
        self.assertEqual(svc.list_todos(), [])

    def test_spec0001_fr02_titel_ueber_200_zeichen_wird_abgelehnt(self):
        svc = neuer_service()
        with self.assertRaises(validation_error()):
            svc.add("x" * 201)
        self.assertEqual(svc.list_todos(), [])

    def test_spec0001_fr02_titel_mit_genau_200_zeichen_ist_erlaubt(self):
        todo = neuer_service().add("y" * 200)
        self.assertEqual(todo.title, "y" * 200)

    def test_spec0001_fr02_titel_ohne_str_wird_abgelehnt(self):
        svc = neuer_service()
        for titel in (None, 42, b"bytes"):
            with self.subTest(titel=titel), self.assertRaises(validation_error()):
                svc.add(titel)
        self.assertEqual(svc.list_todos(), [])

    def test_spec0001_fr02_abgelehnte_aufgabe_verbraucht_keine_id(self):
        svc = neuer_service()
        with self.assertRaises(validation_error()):
            svc.add("  ")
        self.assertEqual(svc.add("Erste").id, 1)
        with self.assertRaises(validation_error()):
            svc.add("z" * 300)
        self.assertEqual(svc.add("Zweite").id, 2)


class AuflistenTest(unittest.TestCase):
    def test_spec0001_fr03_liste_in_anlagereihenfolge(self):
        svc = neuer_service()
        for titel in ("Eins", "Zwei", "Drei"):
            svc.add(titel)
        todos = svc.list_todos()
        self.assertIsInstance(todos, list)
        self.assertEqual([(t.id, t.title, t.done) for t in todos],
                         [(1, "Eins", False), (2, "Zwei", False), (3, "Drei", False)])

    def test_spec0001_fr03_aenderung_der_rueckgabe_wirkt_nicht_auf_den_service(self):
        svc = neuer_service()
        svc.add("A")
        svc.add("B")
        liste = svc.list_todos()
        liste.clear()
        self.assertEqual(len(svc.list_todos()), 2)
        liste2 = svc.list_todos()
        liste2.append(liste2[0])
        self.assertEqual([t.id for t in svc.list_todos()], [1, 2])

    def test_spec0001_fr03_jeder_aufruf_liefert_eine_neue_liste(self):
        svc = neuer_service()
        svc.add("A")
        self.assertIsNot(svc.list_todos(), svc.list_todos())


if __name__ == "__main__":
    unittest.main()
