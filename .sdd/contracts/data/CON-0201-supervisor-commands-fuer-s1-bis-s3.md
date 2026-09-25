---
id: CON-0201
title: "Supervisor-Commands fuer S1 bis S3"
type: data
format: json-schema
spec: SPEC-0053
version: 0.2.0
status: approved
artifact: ".sdd/contracts/data/supervisor-commands-fuer-s1-bis-s3.schema.json"
tests: ["TST-0230"]
---

# Contract: Supervisor-Commands für S1 bis S3

> **Spec:** SPEC-0053 · **Typ:** Daten (JSON Schema) · **Status:** approved

## Zweck

Legt die Entscheidungen des Supervisors als serialisierbare Commands fest (SPEC-0053 FR-08, FR-15,
Command Pattern). Der Supervisor führt nichts aus; der Mediator validiert und führt das Command aus
und protokolliert es in `decisions.jsonl`. Dasselbe Format gilt für `inline` und `session`.

## Invarianten

- **INV-01:** Jedes Command hat `point`, `command` und eine nicht leere Begründung `reason`.
- **INV-02:** Erlaubte Commands je Punkt:
  | Punkt | Commands |
  |-------|----------|
  | S1 | `approve`, `revise`, `halt` |
  | S2 | `retry_with_hint`, `reassign`, `redecompose`, `halt` |
  | S3 | `accept_frs`, `halt` |
- **INV-03:** `reassign` nennt Task, Arbeitsrolle (`test_author|implementer|reviewer`, nie
  `supervisor`) und ein Modellprofil bzw. einen Modellnamen.
- **INV-04:** `accept_frs` nennt je FR `erfüllt|teilweise|fehlt` mit Beleg (Datei oder Test).
- **INV-05:** Die Tabelle aus INV-02 ist die Obergrenze. Die offene Anfrage (CON-0202) nennt mit
  `allowed_commands` die in der konkreten Situation wirksame Teilmenge (z. B. kein `revise` mehr
  nach `max_revisions`). Ein Command ist nur gültig, wenn es dem Schema entspricht und in dieser
  Teilmenge liegt. Wie auf ungültige Commands reagiert wird, regelt CON-0205.

## Beispiele

**Gültig:**
```json
{ "point": "S2", "command": "reassign", "task_id": "t-7", "role": "implementer",
  "model": "qwen38-27b", "reason": "Drei Fehlversuche mit demselben Typfehler; größeres Modell." }
```

**Ungültig (und warum):**
```json
{ "point": "S2", "command": "approve" }
```
→ Verstößt gegen INV-01 (keine Begründung) und INV-02 (`approve` nur in S1).

## Validierung

- Schema: `.sdd/contracts/data/supervisor-commands-fuer-s1-bis-s3.schema.json`.
