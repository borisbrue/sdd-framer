# AGENTS.md (Auszug)

- Python 3.12, nur Standardbibliothek (`urllib.request`, `sqlite3`, `hmac`).
- Neues Paket `webhooks/`: `store.py` (Tabellen `subscriptions`, `deliveries`),
  `signing.py`, `schedule.py` (Backoff/Reihenfolge, reine Funktionen mit injizierbarer Zeit),
  `sender.py` (HTTP), `worker.py` (Schleife), `admin.py` (CLI).
- `shop/` ist fremder Code; `events` wird nur gelesen.
- Tests mit `unittest` unter `tests/`, Befehl `python3 -m unittest discover -s tests -t .`;
  HTTP wird in Tests über einen lokalen `http.server` auf Port 0 geprüft, nie über das Netz.
