---
id: TST-0115
title: "Task-Schema JSON-Validierung (Unit)"
level: unit
spec: SPEC-0026
contract: CON-0096
status: draft
---

# TST-0115: Task-Schema JSON-Validierung

## Zu prüfendes Verhalten

JSON Schema (`contracts/data/task.schema.json`) lehnt ungültige Task-Objekte
ab und akzeptiert valide gemäß CON-0096.

## Testfälle

- T01: Vollständig valides pending-Task-Objekt → valid
- T02: `id` leer → invalid (INV-01)
- T03: `retry_count = 4` → invalid (INV-02)
- T04: `status = "committed"` + `commit_hash = null` → invalid (INV-03)
- T05: `status = "pending"` + `llm_id` gesetzt → invalid (INV-04)
- T06: `error_context` mit 4 Einträgen → invalid (INV-05)
- T07: `type = "unknown"` → invalid (nicht im Enum)
- T08: `estimated_tokens = 0` → invalid (muss > 0 sein)
- T09: `dependencies` mit nicht-existenter Task-ID → valid (referenzielle Prüfung ist Laufzeit)
- T10: vollständig valides committed-Task-Objekt mit commit_hash → valid
