---
id: TST-0123
title: "Config-Commands set/get/show/validate (Unit)"
level: unit
spec: SPEC-0027
contract: CON-0104
status: draft
artifact: tests/unit/test_tst_0123.py
---

# TST-0123: Config-Commands set/get/show/validate

## Zu prüfendes Verhalten

`config_manager.py` bietet Dot-Notation-Zugriff für `set`, `get`, `show` und `validate`
mit atomarem Schreiben und Sofort-Validierung (CON-0104).

## Testfälle

- T01: `config_set("docker.max_parallel_containers", 4)` → Wert in YAML korrekt gesetzt (INV-01)
- T02: `config_set("llm.pool[0].api_key_env", "KEY")` → Array-Index-Zugriff funktioniert (INV-04)
- T03: `config_get("docker.max_parallel_containers")` → gibt `2` zurück
- T04: `config_get("llm.pool[5].model")` → KeyError oder None → Exit-Code 1 (INV-02)
- T05: `config_show()` → enthält alle Sections
- T06: `config_show(section="llm")` → enthält nur LLM-Sektion
- T07: `config_validate()` auf ungültige Config → gibt Fehlerliste zurück, Exit-Code 1 (INV-03)
- T08: `config_set` mit ungültigem Wert → ValidationError, YAML unverändert (INV-01)
