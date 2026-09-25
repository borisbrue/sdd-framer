---
id: TST-0236
title: "Usage-Erfassung: Provider, Decorator, Kontext und Senken"
level: acceptance
spec: SPEC-0060
contract: CON-0207
status: planned
framework: pytest
artifact: "tests/acceptance/test_con_0207.py"
tags: [usage, token-tracking]
---

# Test: Usage-Erfassung: Provider, Decorator, Kontext und Senken

> **Level:** acceptance · **Spec:** SPEC-0060 · **Contract:** CON-0207 · **Status:** planned

## Was wird geprüft?

Alle 17 Szenarien der Usage-Erfassung plus Prompt-Schutz.

Verhaltenstests werden mit `requires_usage_capture` übersprungen, bis `UsageMetadata.source` existiert.

## Vorbedingungen

- `sdd_cli.llm.usage` mit `usage_context`, `use_sinks`, `register_sink`/`unregister_sink`, `RecordingCompletionProvider`, `SqliteUsageSink`, `UsageRecord`.
- Fake-Server `tests/support/fake_llm.py` (braucht das Paket `openai`, sonst werden diese Fälle übersprungen); Envelope-Fixture `tests/fixtures/usage/claude_envelope.json`.

## Ablauf

1. `claude --print` durch das Envelope ersetzen bzw. Fake-Server antworten lassen.
2. Provider über die Factory holen und aufrufen, Senken und `token_usage` auswerten.
3. `sdd upgrade`, `token-history --export` und `calibrate` über die CLI bzw. API ausführen.

## Erwartetes Ergebnis

- Usage-Felder je Provider wie im Contract; `source` immer gesetzt; nicht gemeldete Reasoning-Tokens `None`.
- Genau ein Datensatz je Aufruf, auch bei Ausnahme; Senkenfehler brechen nichts ab.
- Web-API und Altdaten laufen über `token_usage`; `unavailable`-Zeilen fließen nicht in Summen.

## Verknüpfung mit Contract

- [x] INV-01
- [x] INV-02
- [x] INV-03
- [x] INV-04
- [x] INV-05
- [x] INV-06

## Verknüpfung mit Spec

FR-01, FR-02, FR-03, FR-04, FR-05, FR-06, FR-07, FR-08, FR-09, FR-10, FR-11
