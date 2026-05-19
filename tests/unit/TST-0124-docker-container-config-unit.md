---
id: TST-0124
title: "Docker-Container-Konfiguration (Unit)"
level: unit
spec: SPEC-0027
contract: CON-0105
status: draft
artifact: tests/unit/test_tst_0124.py
---

# TST-0124: Docker-Container-Konfiguration

## Zu prüfendes Verhalten

`config_wizard.py` (Docker-Section) + `config_manager.py`: Ressourcenlimits, Parallelität,
Cleanup-Verhalten und Registry-Validierung (CON-0105).

## Testfälle

- T01: Docker-Section setzt runtime, image, dockerfile, max_parallel_containers korrekt
- T02: `cpu_limit` + `memory_limit` landen als Docker-Run-Flags in DevContainerManager
- T03: `cleanup.on_success=True` → Container nach grünen Tests removed
- T04: `cleanup.on_failure=False` → Container nach roten Tests bleibt erhalten
- T05: `max_parallel_containers=0` → ValidationError (INV-01)
- T06: `registry.url` gesetzt, `registry.auth_env` leer → ValidationError (INV-03)
- T07: `skip_if_unavailable=True` + Docker nicht verfügbar → lokaler Fallback mit Warnung
- T08: Parallelitäts-Semaphore begrenzt gleichzeitige Container auf `max_parallel_containers`
