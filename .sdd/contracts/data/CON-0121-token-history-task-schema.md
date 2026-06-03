---
id: CON-0121
project: ""
title: "Token-History-Task-Schema"
type: data
format: json-schema
spec: SPEC-0035
depends_on: ["CON-0041"]
version: 0.1.0
status: draft
artifact: ".sdd/contracts/data/token-history-task-schema.schema.json"
tests: ["TST-0140", "TST-0142"]
---

# Contract: Token-History-Task-Schema

> **Spec:** SPEC-0035 · **Typ:** Daten (JSON Schema) · **Status:** draft

## Zweck

Beschreibt die Erweiterung des `token_usage`-Datenbankschemas um optionale
Task-Granularitäts-Felder für Sub-Agenten-Delegation. Ermöglicht `sdd token-history`
und `sdd calibrate` eine Aufschlüsselung nach Tasks (FR-03, FR-04).

## Invarianten

- **INV-01:** Pflichtfelder bleiben unverändert: `id`, `timestamp`, `component`, `model`, `input_tokens`, `output_tokens`.
- **INV-02:** `task_id` ist ein optionaler String oder null. Wenn vorhanden, identifiziert er einen Decompose-Task eindeutig.
- **INV-03:** `task_label` ist ein optionaler String oder null. Wenn `task_id` gesetzt ist, muss `task_label` ein nicht-leerer String sein.
- **INV-04:** Wenn `task_id` null ist (nicht task-granularer Eintrag), darf `task_label` null oder abwesend sein.
- **INV-05:** Die Summe aller task-granularen Einträge einer Spec entspricht dem Gesamt-Token-Verbrauch dieser Spec in `token-history`.

## Abhängigkeit

Dieses Schema **erweitert** das kanonische `token_usage`-Tabellenschema aus CON-0041.
Die Pflichtfelder aus CON-0041 bleiben unverändert (INV-01). Eine Datenbankmigration
für bestehende `token_usage`-Instanzen (ALTER TABLE … ADD COLUMN task_id TEXT,
ADD COLUMN task_label TEXT) ist bei der Implementierung erforderlich; beide Spalten
sind nullable und können per DEFAULT NULL hinzugefügt werden ohne Datenverlust.

## Garantien

Jede Implementierung, die Token-Verbrauch von Sub-Agenten persistiert, **muss**:
- `task_id` und `task_label` gemeinsam setzen (nie eines ohne das andere)
- Bei Single-Context-Mode (kein Sub-Agent) beide Felder auf null lassen
- Das Schema in `token-history-task-schema.schema.json` vollständig einhalten
- Eine Migration von CON-0041-konformen DBs sicherstellen (nullable columns)
