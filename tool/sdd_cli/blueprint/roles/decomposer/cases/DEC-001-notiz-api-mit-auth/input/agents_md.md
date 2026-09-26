# AGENTS.md (Auszug)

- Sprache: Python 3.12, nur Standardbibliothek.
- Paket `notes/`, Tests unter `tests/` mit `unittest`.
- Testbefehl: `python3 -m unittest discover -s tests -t .`
- Schichten: `notes/store.py` (SQLite-Zugriff) → `notes/service.py` (Regeln, Eigentümer)
  → `notes/server.py` (HTTP). Der HTTP-Teil greift nie direkt auf `sqlite3` zu.
- Konfiguration liest ausschließlich `notes/config.py` (`tomllib`).
