"""TST-0101: extract_fr_ids (SPEC-0101 FR-01, FR-03)."""
import unittest

from sddlib.fr_ids import extract_fr_ids

SPEC = """# SPEC-0101

## 3. Nicht-Ziele

- nichts

## 4. Funktionale Anforderungen

- **FR-01:** Das System liest Dateien.
- **FR-02:** Das System schreibt Dateien.

## 5. Akzeptanzkriterien

- ok
"""


class ExtractFrIdsTest(unittest.TestCase):
    def test_fr01_fr03_liste_mit_fettung(self):
        self.assertEqual(extract_fr_ids(SPEC), ["FR-01", "FR-02"])

    def test_fr01_ohne_abschnitt_leer(self):
        self.assertEqual(extract_fr_ids("# Titel\n\nKein Abschnitt.\n"), [])


if __name__ == "__main__":
    unittest.main()
