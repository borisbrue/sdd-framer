# AGENTS.md (wetterapi)

- Paket `wetterapi/`; WSGI-App in `wetterapi/app.py`, Middlewares in `wetterapi/middleware/`,
  Metriken in `wetterapi/metrics.py` (Registry existiert), Admin-Routen in `wetterapi/admin.py`.
- Fachlogik ohne WSGI-Abhängigkeit in eigenen Modulen.
- Tests: `unittest`, `tests/test_*.py`, `python3 -m unittest discover -s tests -t .`.
