---
id: CON-0041
project: PRJ-0001
title: "Schema der token_usage-Tabelle in evaluations.db"
type: data
format: json-schema
spec: SPEC-0011
version: 0.1.0
status: review
artifact: "contracts/data/token-usage-table.schema.json"
tests:
- TST-0055
---

# Contract: Schema der token_usage-Tabelle in evaluations.db

> **Spec:** SPEC-0011 · **Typ:** Daten · **Status:** review

## Zweck

Definiert das Datenbankschema der `token_usage`-Tabelle in `.sdd/evaluations.db`,
in der der tatsächliche Token-Verbrauch jeder LLM-Komponente gespeichert wird.

## Tabellenschema (SQLite)

```sql
CREATE TABLE IF NOT EXISTS token_usage (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp          TEXT    NOT NULL,            -- ISO 8601 UTC, z.B. "2026-05-14T12:00:00Z"
    spec_id            TEXT,                        -- NULL wenn kein Kontext-Spec bekannt
    component          TEXT    NOT NULL,            -- z.B. "review-contract", "orchestrator"
    model              TEXT    NOT NULL DEFAULT '',
    input_tokens       INTEGER NOT NULL DEFAULT 0,
    output_tokens      INTEGER NOT NULL DEFAULT 0,
    cache_read_tokens  INTEGER NOT NULL DEFAULT 0,
    cache_write_tokens INTEGER NOT NULL DEFAULT 0,
    duration_ms        INTEGER NOT NULL DEFAULT 0,
    calibrated         INTEGER NOT NULL DEFAULT 0   -- 1 = als Abschluss-Datenpunkt markiert
);
```

## Invarianten

- `timestamp` im Format `YYYY-MM-DDTHH:MM:SSZ` (UTC)
- `spec_id` ist `NULL` wenn der Aufruf keiner Spec zugeordnet werden kann
- `component` identifiziert die aufrufende Komponente (nicht leer)
- `model` ist der Modell-Identifier des LLM-Providers (kann leer sein wenn unbekannt)
- `input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_write_tokens` ≥ 0
- `duration_ms` ≥ 0; 0 wenn Messung nicht verfügbar
- `calibrated` ∈ {0, 1}; wird durch `sdd calibrate SPEC-XXXX` auf 1 gesetzt
- Die Tabelle wird erstellt durch `sdd init_db()` und `sdd estimate` (lazy init)

## Komponenten-Namen (Konvention)

| Komponente              | component-Wert      |
|-------------------------|---------------------|
| `sdd review-contract`   | `review-contract`   |
| `sdd orchestrate`       | `orchestrator`      |
| `sdd evaluate`          | `evaluator`         |
