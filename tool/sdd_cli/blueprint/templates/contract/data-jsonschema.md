---
id: CON-XXXX
project: ""                # PRJ-XXXX
title: "<Datenmodell-Name>"
type: data
format: json-schema
spec: SPEC-XXXX
version: 0.1.0
status: draft
artifact: "contracts/data/<name>.schema.json"
tests: []
---

# Contract: {{title}}

> **Spec:** {{spec}} · **Typ:** Daten (JSON Schema) · **Status:** {{status}}

## Zweck

<!-- Welches Datenmodell beschreibt dieser Contract? Wo wird es verwendet (Request-Body, Event-Payload, DB-Persistenz)? -->

## Invarianten

Diese Regeln MÜSSEN für jede gültige Instanz gelten:

- **INV-01:** ...
- **INV-02:** ...

## Beispiele

**Gültig:**
```json
{
  "id": "01HZ...",
  "name": "Beispiel"
}
```

**Ungültig (und warum):**
```json
{
  "id": "",
  "name": null
}
```
→ Verstößt gegen INV-01 (id darf nicht leer sein).

## Validierung

- Schema unter `{{artifact}}` (JSON Schema Draft 2020-12)
- Validatoren je nach Sprache: `ajv` (JS), `jsonschema` (Python), etc.
