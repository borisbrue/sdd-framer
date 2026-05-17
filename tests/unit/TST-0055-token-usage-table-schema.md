---
id: TST-0055
project: PRJ-0001
title: "token_usage-Tabelle: Schema-Validierung und Persistenz"
level: unit
spec: SPEC-0011
contract: CON-0041
status: planned
framework: pytest
artifact: "tests/unit/test_estimation.py"
tags: ["token-usage", "db", "estimation"]
---

# Test: token_usage-Tabelle – Schema-Validierung und Persistenz

> **Level:** unit · **Spec:** SPEC-0011 · **Contract:** CON-0041 · **Status:** planned

## Was wird geprüft?

- `init_token_usage_table()` erstellt die Tabelle mit korrektem Schema
- `persist_token_usage()` schreibt valide Zeilen in die DB
- `token_history()` liest Zeilen korrekt zurück
- `spec_id = None` ist erlaubt (nullable)

## Ablauf

### TC-01: Tabellenstruktur

1. Erstelle temporäre SddConfig mit `tmp_path`
2. Rufe `init_token_usage_table(config)` auf
3. Öffne SQLite-Verbindung, frage `PRAGMA table_info(token_usage)` ab
4. Prüfe: Alle Pflicht-Spalten vorhanden (id, timestamp, spec_id, component, model,
   input_tokens, output_tokens, cache_read_tokens, cache_write_tokens, duration_ms, calibrated)

### TC-02: Persistenz mit spec_id

1. Rufe `persist_token_usage(config, component="test", model="m", input_tokens=100,
   output_tokens=50, spec_id="SPEC-0001")` auf
2. Prüfe: Eine Zeile in DB, Werte korrekt

### TC-03: Persistenz ohne spec_id (NULL)

1. Rufe `persist_token_usage(config, component="test", model="m", input_tokens=10,
   output_tokens=5)` ohne `spec_id` auf
2. Prüfe: `spec_id` ist NULL in DB

### TC-04: token_history Filter

1. Schreibe 2 Zeilen (SPEC-0001, SPEC-0002)
2. `token_history(config, "SPEC-0001")` → 1 Zeile
3. `token_history(config)` → 2 Zeilen

## Erwartetes Ergebnis

Alle 4 Test-Cases bestehen in < 1 s. Keine Netzwerk- oder LLM-Aufrufe.
