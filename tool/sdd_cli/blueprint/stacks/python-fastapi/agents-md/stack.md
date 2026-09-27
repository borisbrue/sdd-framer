## Stack: python-fastapi

- **Tests:** `PYTHONPATH=.sdd/quality python3 -m pytest -p sdd_fr_marker` – jeder Test trägt
  `@pytest.mark.fr("FR-xx")` mit der Anforderung, die er prüft; HTTP-Tests über
  `fastapi.testclient.TestClient`.
- **Start:** `python3 -m {{package_name}}` (uvicorn, Port 8000), Gesundheitsprüfung `GET /health`.
- **Lint:** `ruff check .`, **Typen:** `mypy {{package_name}}` (optional).
- **Messen:** `sdd quality measure`, **Architektur:** `sdd arch check`, **Einrichtung prüfen:**
  `sdd stack verify`.
- **Schichten [ARCH-01]:** `api` → `service` → `domain`; `persistence` → `domain`; nur
  `{{package_name}}/__init__.py` und `__main__.py` verdrahten die Schichten.
