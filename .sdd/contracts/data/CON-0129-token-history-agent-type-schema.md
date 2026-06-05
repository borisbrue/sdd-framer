---
id: CON-0129
project: ""
title: "Token-History-Schema-Erweiterung: agent_type und model"
type: data
format: json-schema
spec: SPEC-0036
depends_on: ["CON-0121"]
version: 0.1.0
status: draft
artifact: ".sdd/contracts/data/token-history-agent-type.schema.json"
tests: ["TST-0151"]
---

# Contract: Token-History-Schema-Erweiterung: agent_type und model

> **Spec:** SPEC-0036 · **Typ:** Daten (JSON Schema) · **Status:** draft

## Zweck

Beschreibt die Erweiterung des `token_usage`-Schemas (CON-0121, SPEC-0035) um die
Felder `agent_type` und `model` für SPEC-0036 (FR-07). Die Erweiterung erfolgt
koordiniert mit SPEC-0011 — kein zweites Schema, keine separate Migration.

## Verhältnis zu CON-0121

CON-0129 *erweitert* CON-0121: alle Invarianten von CON-0121 bleiben gültig.
CON-0129 fügt zwei optionale Felder hinzu ohne bestehende Pflichtfelder zu ändern.

## Invarianten

- **INV-01:** `agent_type` ist optional. Wenn vorhanden: `"local"` oder `"cloud"`.
- **INV-02:** `model` ist optional. Wenn `agent_type` gesetzt ist, muss `model`
  ein nicht-leerer String sein (z.B. `"llama3.1:8b"` oder `"claude-sonnet-4-6"`).
- **INV-03:** Bestehende Zeilen ohne `agent_type`/`model` (von SPEC-0011/SPEC-0035)
  bleiben gültig — Rückwärtskompatibilität ist garantiert.
- **INV-04:** Lokale Tasks haben `agent_type: "local"` und `model` = lokales Modell.
  Cloud-Tasks haben `agent_type: "cloud"` und `model` = Cloud-Modell-ID.

## Schema-Artifact

Siehe: `token-history-agent-type.schema.json`
