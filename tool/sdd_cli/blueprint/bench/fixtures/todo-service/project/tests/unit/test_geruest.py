"""Gerüst-Tests: Pakete der Schichten sind importierbar (kein Spec-Bezug)."""
import importlib
import unittest


class GeruestTest(unittest.TestCase):
    def test_schichten_sind_importierbar(self):
        for name in ("todo", "todo.domain", "todo.service", "todo.persistence", "todo.cli"):
            with self.subTest(paket=name):
                self.assertIsNotNone(importlib.import_module(name))

    def test_version_ist_gesetzt(self):
        import todo

        self.assertIsInstance(todo.__version__, str)

    def test_cli_hat_main(self):
        from todo.cli import main

        self.assertTrue(callable(main))


if __name__ == "__main__":
    unittest.main()
