---
id: CON-0206
title: "token_usage 2.0: Zeilenschema und Aufrufkontext"
type: data
format: json-schema
spec: SPEC-0060
version: 0.3.0
status: approved
artifact: ".sdd/contracts/data/token-usage-2-0-zeilenschema-und-aufrufkontext.schema.json"
tests: ["TST-0235"]
---

# Contract: token_usage 2.0: Zeilenschema und Aufrufkontext

> **Spec:** SPEC-0060 · **Typ:** Daten (JSON Schema) · **Status:** approved

## Zweck

Beschreibt eine Zeile der Tabelle `token_usage` in `.sdd/evaluations.db` nach SPEC-0060 FR-05. Das
Schema baut auf dem Basisschema aus CON-0041 auf und schließt die Erweiterungen aus CON-0121
(`task_id`/`task_label`) und CON-0129 (`agent_type`) ein; es listet damit alle Spalten der Tabelle; Leser wie `sdd estimate`, `calibrate`,
`token-history` und die Web-API arbeiten mit alten und neuen Zeilen.

## Invarianten

- **INV-01:** Alle neuen Spalten (`reasoning_tokens`, `finish_reason`, `server_model`, `source`,
  `run_id`, `context_json`) sind nullable. Die Dauer eines Aufrufs steht wie bisher in
  `duration_ms`; es gibt keine zweite Zeitspalte. Zeilen aus der Zeit vor
  SPEC-0060 bleiben gültig und unverändert.
- **INV-02:** `source` ist `reported`, `estimated` oder `unavailable`; `null` nur bei Altzeilen.
- **INV-03:** `context_json` ist entweder `null` oder der Text eines JSON-**Objekts**. Es enthält
  alle Kontextschlüssel, für die es keine eigene Spalte gibt. Schlüssel mit eigener Spalte
  (`spec_id`, `task_id`, `task_label`, `run_id`, `agent_type`) stehen nur in der Spalte, nie
  zusätzlich in `context_json`.
  Rollen-Semantik steht nur hier. Reservierte Schlüssel mit fester Bedeutung:
  | Schlüssel | Bedeutung | gesetzt von |
  |-----------|-----------|-------------|
  | `role` | Rolle des Aufrufs | SPEC-0053 |
  | `attempt` | Versuchsnummer ab 1 | SPEC-0053 |
  | `call_id` | Verknüpfung zum Ereignis `role_call` | SPEC-0053 |
  | `role_version` | Version der Rollendatei | SPEC-0053 |
  | `origin` | Herkunft außerhalb der CLI, z. B. `web` | SPEC-0060 FR-08 |

  Weitere Schlüssel sind erlaubt; neue reservierte Schlüssel erweitern diese Tabelle.
- **INV-04:** Keine Spalte enthält Prompt- oder Antworttext.
- **INV-05:** Tokenzahlen sind nicht negativ; bei `source: unavailable` sind `input_tokens` und
  `output_tokens` 0. `reasoning_tokens` ist `null`, wenn der Provider ihn nicht meldet, und `0`
  nur, wenn er „kein Reasoning“ meldet.
- **INV-06:** Leser, die Verbrauch mitteln oder summieren (`sdd estimate`, `calibrate`,
  `token-history`-Summen, Web-Zusammenfassung), schließen Zeilen mit `source: unavailable` aus und
  weisen ihre Anzahl gesondert aus. Da diese Zeilen 0/0 Tokens haben, bleibt die Summenregel aus
  CON-0121 INV-05 unberührt. Zeilen mit `source: estimated` gehen in Summen und Mittelwerte ein;
  `token-history` zeigt ihre Quelle in der Spalte `source`.
- **INV-07:** `model` ist die konfigurierte Modell-ID der Komponente (`llm.<komponente>.model`);
  Auswertungen gruppieren nach `model`. `server_model` ist die Modell-ID, die der Server in der
  Antwort meldet, und dient nur der Nachvollziehbarkeit. Ist `agent_type` gesetzt, ist `model`
  nicht leer (CON-0129 INV-02).
- **INV-08:** Ist `task_id` gesetzt, ist auch `task_label` ein nicht leerer String (CON-0121).

## Beispiele

**Gültig (neu):**
```json
{ "id": 2, "timestamp": "2026-09-25T10:00:00Z", "spec_id": "SPEC-0900",
  "component": "completion", "model": "fake-implementer", "input_tokens": 1200,
  "output_tokens": 300, "cache_read_tokens": 50, "cache_write_tokens": 70, "duration_ms": 900,
  "calibrated": 0, "reasoning_tokens": 40, "finish_reason": "end_turn",
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

```json
{ "id": 4, "timestamp": "2026-09-25T10:00:00Z", "component": "completion", "model": "m",
  "input_tokens": 1, "output_tokens": 1, "task_id": "T1", "task_label": null }
```
→ `task_id` ohne `task_label` (INV-08).

## Validierung

- Schema: `.sdd/contracts/data/token-usage-2-0-zeilenschema-und-aufrufkontext.schema.json`.
- INV-03 (JSON-Objekt, keine Spaltenschlüssel im JSON) und INV-05 prüft TST-0235 zur Laufzeit.
