---
id: TST-0118
title: "Container-Lifecycle (Unit)"
level: unit
spec: SPEC-0026
contract: CON-0099
status: draft
---

# TST-0118: Container-Lifecycle

## Zu prüfendes Verhalten

`container.py` erstellt, startet und entfernt Container korrekt gemäß CON-0099.
Tests laufen gegen einen Docker/Podman-Mock oder eine Test-Registry.

## Testfälle

- T01: `container.create([T1])` → Name folgt Schema `sdd-SPEC-XXXX-<uuid>` (INV-03)
- T02: Container enthält Code-Stand von Git-HEAD (INV-02)
- T03: Container mit 3 Tasks → alle 3 dem selben Container zugewiesen (INV-01)
- T04: Leere Task-Liste → ValueError (INV-01)
- T05: `container.remove(C1)` → Container existiert danach nicht mehr (INV-04)
- T06: SIGINT während laufendem Container → cleanup() wird aufgerufen
- T07: Container-Name-Kollision (gleiche UUID) → zweiter Aufruf schlägt fehl
- T08: Container-Status nach remove → nicht "running" oder "stopped"
