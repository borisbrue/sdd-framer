# AGENTS.md (Auszug)

- Python 3.12, nur Standardbibliothek (`csv`, `sqlite3`).
- Paket `crm/`; Datenbankzugriff ausschließlich über `crm/db.py` (vorhanden, darf erweitert
  werden). Der Importer liegt in `crm/importer/` (neues Paket).
- Tests mit `unittest` unter `tests/`, Befehl `python3 -m unittest discover -s tests -t .`
- Testdaten (CSV) liegen unter `tests/data/`.
