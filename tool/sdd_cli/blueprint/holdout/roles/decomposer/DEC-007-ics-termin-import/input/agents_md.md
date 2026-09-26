# AGENTS.md (belegung)

## Architektur
- `belegung/cli.py` – argparse, nur Verdrahtung.
- `belegung/ics/` – reines Parsen und Umrechnen, keine Datenbank.
- `belegung/store.py` – einziger Ort mit SQL (außer Migrationen).
- `belegung/migrations/NNNN_name.sql` – Schemaänderungen, werden beim Start in Nummernfolge
  angewandt (`belegung/migrate.py`, existiert). Nie eine Tabelle im Anwendungscode anlegen.

## Tests
- `unittest`, `tests/test_*.py`, Aufruf `python3 -m unittest discover -s tests -t .`.
- Datenbanktests mit `sqlite3.connect(":memory:")` und angewandten Migrationen.
