---
id: CON-0096
title: "Task-Schema – Datenstruktur eines Distribution-Tasks"
type: data
format: json-schema
spec: SPEC-0026
version: 0.1.0
status: draft
artifact: "contracts/data/task.schema.json"
tests:
- TST-0115
---

# Contract: Task-Schema – Datenstruktur eines Distribution-Tasks

> **Spec:** SPEC-0026 · **Typ:** Daten (JSON Schema) · **Status:** draft

## Zweck

Definiert die kanonische Datenstruktur eines `Task`-Objekts, das aus einem Spec
abgeleitet, einem LLM zugewiesen und in einem Container ausgeführt wird.
Wird in `decompose.py`, `task_runner.py` und `orchestrator.py` verwendet.

## Invarianten

- **INV-01:** `id` ist ein nicht-leerer, eindeutiger String (z.B. UUID4).
- **INV-02:** `retry_count` liegt immer im Bereich 0–3.
- **INV-03:** `commit_hash` ist nur gesetzt wenn `status == "committed"`.
- **INV-04:** `llm_id` ist nur gesetzt wenn `status != "pending"`.
- **INV-05:** `error_context` enthält maximal 3 Einträge (einen pro Retry).
- **INV-06:** `dependencies` enthält nur gültige Task-IDs desselben Specs.

## Felder

| Feld | Typ | Pflicht | Beschreibung |
|---|---|---|---|
| `id` | string | ja | UUID4 |
| `spec_id` | string | ja | z.B. `SPEC-0026` |
| `title` | string | ja | Kurztitel des Tasks |
| `description` | string | ja | Vollständige Aufgabenbeschreibung |
| `type` | enum | ja | `code` \| `test` \| `config` \| `doc` |
| `complexity` | enum | ja | `low` \| `medium` \| `high` |
| `context_size` | enum | ja | `S` \| `M` \| `L` |
| `estimated_tokens` | integer | ja | Geschätzte Tokenmenge (> 0) |
| `status` | enum | ja | Siehe CON-0095 |
| `retry_count` | integer | ja | 0–3 |
| `llm_id` | string\|null | ja | Zugewiesenes LLM oder null |
| `container_id` | string\|null | ja | Container-ID oder null |
| `commit_hash` | string\|null | ja | Git-Commit-Hash oder null |
| `dependencies` | array[string] | ja | IDs abhängiger Tasks (kann leer sein) |
| `error_context` | array[string] | ja | Fehlermeldungen aus Retries |

## Beispiele

**Gültig (pending):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "spec_id": "SPEC-0026",
  "title": "Implementiere TaskLifecycle State Machine",
  "description": "Erstelle tool/sdd_cli/task_runner.py mit dem State Pattern...",
  "type": "code",
  "complexity": "medium",
  "context_size": "M",
  "estimated_tokens": 4200,
  "status": "pending",
  "retry_count": 0,
  "llm_id": null,
  "container_id": null,
  "commit_hash": null,
  "dependencies": [],
  "error_context": []
}
```

**Ungültig (commit_hash ohne committed-Status):**
```json
{
  "status": "running",
  "commit_hash": "abc123"
}
```
→ Verstößt gegen INV-03.

## Validierung

- Schema unter `contracts/data/task.schema.json` (JSON Schema Draft 2020-12)
- Python: `jsonschema`, JS: `ajv`
