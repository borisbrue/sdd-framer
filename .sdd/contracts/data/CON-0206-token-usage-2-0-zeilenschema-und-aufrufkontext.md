---
id: CON-0206
title: "token_usage 2.0: Zeilenschema und Aufrufkontext"
type: data
format: json-schema
spec: SPEC-0060
version: 0.1.0
status: draft
artifact: ".sdd/contracts/data/token-usage-2-0-zeilenschema-und-aufrufkontext.schema.json"
tests: ["TST-0235"]
---

# Contract: token_usage 2.0: Zeilenschema und Aufrufkontext

> **Spec:** SPEC-0060 · **Typ:** Daten (JSON Schema) · **Status:** draft

## Zweck

Beschreibt eine Zeile der Tabelle `token_usage` in `.sdd/evaluations.db` nach SPEC-0060 FR-05. Das
Schema erweitert CON-0121 und CON-0129 additiv; Leser wie `sdd estimate`, `calibrate`,
`token-history` und die Web-API arbeiten mit alten und neuen Zeilen.

## Invarianten

- **INV-01:** Alle neuen Spalten (`reasoning_tokens`, `finish_reason`, `latency_ms`,
  `server_model`, `source`, `run_id`, `context_json`) sind nullable. Zeilen aus der Zeit vor
  SPEC-0060 bleiben gültig und unverändert.
- **INV-02:** `source` ist `reported`, `estimated` oder `unavailable`; `null` nur bei Altzeilen.
- **INV-03:** `context_json` ist entweder `null` oder der Text eines JSON-**Objekts**. Es enthält
  alle Kontextschlüssel außer `spec_id`, `task_id` und `run_id`, die eigene Spalten haben.
  Rollen-Semantik (z. B. `role`, `attempt`, `call_id`) steht nur hier.
- **INV-04:** Keine Spalte enthält Prompt- oder Antworttext.
- **INV-05:** Tokenzahlen sind nicht negativ; bei `source: unavailable` sind sie 0.

## Beispiele

**Gültig (neu):**
```json
{ "id": 2, "timestamp": "2026-09-25T10:00:00Z", "spec_id": "SPEC-0900",
  "component": "completion", "model": "fake-implementer", "input_tokens": 1200,
  "output_tokens": 300, "cache_read_tokens": 50, "cache_write_tokens": 70, "duration_ms": 900,
  "calibrated": 0, "reasoning_tokens": 40, "finish_reason": "end_turn", "latency_ms": 900,
  "server_model": "claude-opus-5-5", "source": "reported",
  "run_id": "SPEC-0900-20260925T101500-a1",
  "context_json": "{\"role\": \"implementer\", \"attempt\": 1, \"call_id\": \"c-7\"}" }
```

**Ungültig (und warum):**
```json
{ "id": 3, "timestamp": "2026-09-25T10:00:00Z", "component": "completion", "model": "m",
  "input_tokens": -1, "output_tokens": 0, "source": "guess", "prompt": "…" }
```
→ Negative Tokenzahl (INV-05), unbekannte `source` (INV-02), Prompttext (INV-04).

## Validierung

- Schema: `.sdd/contracts/data/token-usage-2-0-zeilenschema-und-aufrufkontext.schema.json`.
- INV-03 (JSON-Objekt) und INV-05 prüft TST-0235 zur Laufzeit.
