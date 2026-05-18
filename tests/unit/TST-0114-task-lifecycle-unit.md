---
id: TST-0114
title: "Task-Lifecycle Zustandsübergänge (Unit)"
level: unit
spec: SPEC-0026
contract: CON-0095
status: draft
---

# TST-0114: Task-Lifecycle Zustandsübergänge

## Zu prüfendes Verhalten

Die `TaskLifecycle`-Klasse (State Pattern) erlaubt nur gültige Zustandsübergänge
gemäß CON-0095 und blockiert ungültige mit einer Exception.

## Testfälle

- T01: `pending → assigned` ist erlaubt
- T02: `assigned → running` ist erlaubt
- T03: `running → review` ist erlaubt
- T04: `review → committed` bei positivem Review
- T05: `review → retrying` bei negativem Review (Versuch 1/2)
- T06: `review → blocked` nach dem 3. fehlgeschlagenen Versuch
- T07: `pending → committed` direkt wirft `InvalidTransitionError`
- T08: Retry-Zähler überschreitet nie 3 (INV-02)
