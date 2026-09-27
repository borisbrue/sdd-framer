## Stack: python-cli

- **Tests:** `PYTHONPATH=.sdd/quality python3 -m pytest -p sdd_fr_marker` – jeder Test trägt
  `@pytest.mark.fr("FR-xx")` mit der Anforderung, die er prüft.
- **Lint:** `ruff check .`, **Typen:** `mypy {{package_name}}` (optional).
- **Messen:** `sdd quality measure`, **Architektur:** `sdd arch check`, **Einrichtung prüfen:**
  `sdd stack verify`.
- **Schichten [ARCH-01]:** `cli` → `service` → `domain`; `persistence` → `domain`; nur
  `{{package_name}}/__init__.py` und `__main__.py` verdrahten die Schichten.
