---
id: TST-0125
title: "SDD Config Schema (Unit)"
level: unit
spec: SPEC-0027
contract: CON-0106
status: draft
artifact: tests/unit/test_tst_0125.py
---

# TST-0125: SDD Config Schema

## Zu prüfendes Verhalten

`contracts/data/sdd-config.schema.json` wird via `jsonschema` in `config_manager.py`
für jede valide und ungültige Config-Instanz korrekt ausgewertet (CON-0106).

## Testfälle

- T01: Vollständige valide Config (ollama local + claude remote) → validiert ohne Fehler
- T02: Remote-Provider mit Klartext-Key als `api_key_env` (Pattern verletzt) → ValidationError (INV-02)
- T03: Remote-Provider ohne `api_key_env` → ValidationError (required, INV-02)
- T04: `max_parallel_containers: 0` → ValidationError (minimum:1, INV-04)
- T05: `memory_limit: "1gb"` (ungültiges Format) → ValidationError (INV-06)
- T06: `strategy: "random"` → ValidationError (enum, INV-03)
- T07: Doppelte Provider-IDs → per uniqueItems oder app-seitige Prüfung → Fehler (INV-01)
- T08: `registry.url` gesetzt, `registry.auth_env` fehlt → app-seitige ValidationError (INV-07)
