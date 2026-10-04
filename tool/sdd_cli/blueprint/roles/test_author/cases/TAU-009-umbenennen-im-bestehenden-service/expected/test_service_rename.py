"""Tests für TodoService.rename (SPEC-0109 FR-01, FR-02, FR-03)."""
import unittest

from todo.domain import TodoNotFoundError, ValidationError
from todo.repository import InMemoryRepository
from todo.service import TodoService


class RenameTest(unittest.TestCase):
    def setUp(self):
        self.repo = InMemoryRepository()
        self.service = TodoService(self.repo)
        self.todo = self.service.add("Einkaufen")

    # FR-01
    def test_fr01_neuer_titel_wird_gespeichert(self):
        ergebnis = self.service.rename(self.todo.id, "Wocheneinkauf")
        self.assertEqual(ergebnis.title, "Wocheneinkauf")
        self.assertEqual(self.repo.get(self.todo.id).title, "Wocheneinkauf")

    def test_fr01_id_und_status_bleiben(self):
        self.service.complete(self.todo.id)
        ergebnis = self.service.rename(self.todo.id, "Erledigt umbenannt")
        self.assertEqual(ergebnis.id, self.todo.id)
        self.assertTrue(ergebnis.done)
        self.assertEqual([t.id for t in self.repo.todos()], [self.todo.id])

    # FR-02
    def test_fr02_leerraum_wird_entfernt(self):
        self.assertEqual(self.service.rename(self.todo.id, "  Kochen  ").title, "Kochen")

    def test_fr02_leerer_titel_ist_fehler_und_aendert_nichts(self):
        with self.assertRaises(ValidationError):
            self.service.rename(self.todo.id, "   ")
        self.assertEqual(self.repo.get(self.todo.id).title, "Einkaufen")

    def test_fr02_zu_langer_titel_ist_fehler(self):
        self.service.rename(self.todo.id, "x" * 200)
        with self.assertRaises(ValidationError):
            self.service.rename(self.todo.id, "x" * 201)

    # FR-03
    def test_fr03_unbekannte_id(self):
        with self.assertRaises(TodoNotFoundError):
            self.service.rename(999, "Neu")
        self.assertIsNone(self.repo.get(999))


if __name__ == "__main__":
    unittest.main()
