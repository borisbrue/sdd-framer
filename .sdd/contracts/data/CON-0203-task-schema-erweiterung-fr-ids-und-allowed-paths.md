---
id: CON-0203
title: "Task-Schema-Erweiterung: fr_ids und allowed_paths"
type: data
format: json-schema
spec: SPEC-0053
version: 0.1.0
status: draft
artifact: ".sdd/contracts/data/task-schema-erweiterung-fr-ids-und-allowed-paths.schema.json"
tests: ["TST-0232"]
---

# Contract: Task-Schema-Erweiterung: fr_ids und allowed_paths

> **Spec:** SPEC-0053 · **Typ:** Daten (JSON Schema) · **Status:** draft

## Zweck

Erweitert das Task-Schema aus CON-0096 (SPEC-0026) um `fr_ids` und `allowed_paths`
(SPEC-0053 FR-05, FR-07). Alle Invarianten von CON-0096 bleiben gültig; die Erweiterung ist
additiv, bestehende `.sdd/tasks/<SPEC>.json` ohne die Felder bleiben gültig.

## Invarianten

- **INV-01:** `fr_ids` ist optional. Wenn vorhanden und `type` ist `code` oder `test`, enthält es
  mindestens eine FR-ID.
- **INV-02:** `allowed_paths` ist optional; fehlt es, gilt für den Task nur die allgemeine
  PathPolicy (CON-0204) ohne Task-Einschränkung.
- **INV-03:** Bei der Umsetzung wird `contracts/data/task.schema.json` (Artefakt von CON-0096)
  um beide Felder ergänzt und `Task.to_dict`/`from_dict` gelesen und geschrieben.

## Beispiele

**Gültig:**
```json
{ "type": "code", "fr_ids": ["FR-05"], "allowed_paths": ["tool/sdd_cli/decompose.py"] }
```

**Ungültig (und warum):**
```json
{ "type": "code", "fr_ids": [] }
```
→ Verstößt gegen INV-01.

## Validierung

- Schema: `.sdd/contracts/data/task-schema-erweiterung-fr-ids-und-allowed-paths.schema.json`.
