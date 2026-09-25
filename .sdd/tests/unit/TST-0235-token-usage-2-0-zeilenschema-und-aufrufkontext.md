---
id: TST-0235
title: "token_usage 2.0: Zeilenschema und Aufrufkontext"
level: unit
spec: SPEC-0060
contract: CON-0206
status: planned
framework: pytest
artifact: "tests/unit/test_con_0206.py"
tags: [usage, token-tracking]
---

# Test: token_usage 2.0: Zeilenschema und Aufrufkontext

> **Level:** unit · **Spec:** SPEC-0060 · **Contract:** CON-0206 · **Status:** planned

## Was wird geprüft?

Zeilenschema von `token_usage` 2.0 und das Schreiben der SQLite-Senke.

Verhaltenstests werden mit `requires_usage_capture` übersprungen, bis `UsageMetadata.source` existiert.

## Vorbedingungen

- Schema-Artefakt von CON-0206.
- Für den Laufzeittest: `sdd_cli.llm.usage.SqliteUsageSink` und `UsageRecord` (übersprungen bis SPEC-0060 umgesetzt ist).

## Ablauf

1. Alte und neue Zeilen gegen das Schema prüfen.
2. Einen Datensatz über die SQLite-Senke schreiben und die Zeile prüfen.

## Erwartetes Ergebnis

- Alte Zeilen bleiben gültig; `latency_ms`, unbekannte `source`, negative Zählwerte und Prompttext werden abgelehnt.
- `spec_id`/`run_id` als Spalten, übrige Kontextschlüssel als JSON-Objekt in `context_json`.

## Verknüpfung mit Contract

- [x] INV-01
- [x] INV-02
- [x] INV-03
- [x] INV-04
- [x] INV-05

## Verknüpfung mit Spec

FR-05
