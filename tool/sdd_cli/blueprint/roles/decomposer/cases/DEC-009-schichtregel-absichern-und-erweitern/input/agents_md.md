# AGENTS.md (Auszug)

- Python 3.12, nur Standardbibliothek.
- Schichten im Paket `todo/`: `domain.py` → `repository.py` → `service.py`. Eine Schicht
  importiert nur Schichten links von ihr.
- Tests mit `unittest` unter `tests/`, Befehl `python3 -m unittest discover -s tests -t .`
- Ein Task vom Typ `test` schreibt nur seine Testdatei; der Test muss sofort grün sein.
