---
id: CON-0038
project: PRJ-0001
title: "Schema von .sdd/content-hashes.json"
type: data
format: json-schema
spec: SPEC-0010
version: 0.1.0
status: review
artifact: "contracts/data/content-hashes.schema.json"
tests:
- TST-0048
- TST-0049
- TST-0050
---

# Contract: Schema von .sdd/content-hashes.json

> **Spec:** SPEC-0010 · **Typ:** Daten · **Status:** review

## Zweck

Definiert das exakte Format der Datei `.sdd/content-hashes.json`, in der
Content-Hashes aller Artefakte persistent gespeichert werden.

## Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "SDD Content-Hashes",
  "description": "Mapping von Artefakt-ID zu SHA-256-Hash des bereinigten Inhalts",
  "type": "object",
  "additionalProperties": {
    "type": "string",
    "pattern": "^[0-9a-f]{64}$",
    "description": "SHA-256-Hexdigest (64 Zeichen, lowercase)"
  },
  "examples": [
    {
      "SPEC-0001": "a3f1b2c9d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1",
      "CON-0001":  "b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2"
    }
  ]
}
```

## Invarianten

- Schlüssel: Artefakt-ID im Format `[A-Z]+-[0-9]{4}` (SPEC-XXXX, CON-XXXX)
- Wert: SHA-256-Hexdigest, exakt 64 Zeichen, nur `[0-9a-f]`
- Datei ist JSON (UTF-8, 2-Spaces-Indent, sortierte Keys)
- Leere Datei ist `{}` (leeres Objekt), nicht `null` oder leer
- Datei wird von `sdd status-check`, `sdd status-check --fix` und
  `sdd install-hooks`-Hook gelesen/geschrieben
