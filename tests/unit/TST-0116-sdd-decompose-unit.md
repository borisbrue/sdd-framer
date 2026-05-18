---
id: TST-0116
title: "sdd decompose Task-Ableitung (Unit)"
level: unit
spec: SPEC-0026
contract: CON-0097
status: draft
---

# TST-0116: sdd decompose Task-Ableitung

## Zu prüfendes Verhalten

`decompose.py` zerlegt ein Spec korrekt in klassifizierte Tasks und validiert
die Ausgabe vor dem Speichern gemäß CON-0097.

## Testfälle

- T01: Spec mit 5 FRs erzeugt ≥ 5 Tasks
- T02: Jeder Task hat complexity, context_size und type gesetzt
- T03: Kein Task hat leeren Titel (INV-02 Duplicate-Check)
- T04: Zwei Tasks mit identischem Titel → ValueError
- T05: estimated_tokens > 0 für alle Tasks (INV-03)
- T06: Spec ohne FRs → SystemExit mit Meldung "Keine Tasks ableitbar" (INV-01)
- T07: Nach Bestätigung wird `.sdd/tasks/SPEC-XXXX.json` geschrieben
- T08: Gespeicherte JSON-Datei validiert gegen CON-0096 (task.schema.json)
