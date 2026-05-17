---
id: CON-0005
title: "extension-config"
type: data
format: json-schema
spec: SPEC-0002
version: 0.1.0
status: draft
artifact: "contracts/data/extension-config.schema.json"
tests: [TST-0006]
---

# Contract: extension-config

> **Spec:** SPEC-0002 · **Typ:** Daten (JSON Schema) · **Status:** draft

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

- Schema unter `contracts/data/extension-config.schema.json` (JSON Schema Draft 2020-12)
- Validatoren je nach Sprache: `ajv` (JS), `jsonschema` (Python), etc.
