# AGENTS.md (Auszug)

- Python 3.12, nur Standardbibliothek. Neues Paket `ratelimit/`.
- Kernlogik (`ratelimit/bucket.py`, `ratelimit/registry.py`) ist frei von WSGI;
  `ratelimit/middleware.py` ist der einzige WSGI-Berührungspunkt.
- `catalog/` ist fremder Code und wird nicht verändert.
- Tests mit `unittest` unter `tests/`, Befehl `python3 -m unittest discover -s tests -t .`;
  keine Tests mit `time.sleep`.
