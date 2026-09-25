---
id: SPEC-0060
title: "Vollständige Usage-Erfassung aller LLM-Provider inkl. Reasoning-Tokens"
type: feature
status: draft
owner: "Boris"
created: 2026-09-25
updated: 2026-09-25
version: 0.1.0
priority: high
tags: [llm, token-tracking, usage, keyless]
depends_on: [SPEC-0008, SPEC-0011, SPEC-0035, SPEC-0050]
contracts: []
tests: []
---

# Vollständige Usage-Erfassung aller LLM-Provider inkl. Reasoning-Tokens

> **Status:** draft · **Owner:** Boris · **Version:** 0.1.0

## 1. Kontext & Motivation

sdd-framer erfasst den Tokenverbrauch heute lückenhaft:

- `claude-cli`, der Default im keyfreien Betrieb, liefert `usage: None`. Deshalb bleiben
  `sdd token-history` und `sdd estimate` leer, obwohl `claude --print --output-format json` die
  Usage im Envelope mitliefert.
- `openai-compat` liest nur `prompt_tokens`/`completion_tokens`. Reasoning-Tokens
  (`completion_tokens_details.reasoning_tokens`) und `finish_reason` gehen verloren.
- `CodeGenProvider.generate` gibt gar keine Usage zurück.
- Persistiert wird nur an zwei Stellen (`lifecycle.py`, `sub_agent.py`); `decompose`, `task-exec`,
  `task-loop`, Evaluator und Orchestrator schreiben nichts. Die Web-API führt mit
  `.sdd/ai_usage.json` einen zweiten Speicher.

Die Rollen-Pipeline (SPEC-0053) und der Benchmark (SPEC-0056) brauchen verlässliche Zahlen je
Aufruf, einschließlich Reasoning-Tokens. Diese Spec schließt die Lücke unabhängig von der Pipeline.

## 2. Zielsetzung

**Primärziel:** Jeder LLM-Aufruf von sdd-framer erzeugt genau einen Usage-Datensatz in der
bestehenden Tabelle `token_usage`, mit Input-, Output- und Reasoning-Tokens, sofern der Provider
sie liefert.

**Erfolgskriterien (messbar):**
- [ ] Im keyfreien Betrieb (`claude-cli`) zeigt `sdd token-history` nach einem `sdd spec review`
      Datensätze mit Input- und Output-Tokens > 0.
- [ ] Ein Aufruf eines Reasoning-Modells über `openai-compat` erzeugt einen Datensatz mit
      `reasoning_tokens > 0`, sofern der Server sie meldet.
- [ ] Kein LLM-Aufruf, der über die Provider-Factory läuft, bleibt ohne Datensatz. Ein Test
      prüft das für alle Komponenten.
- [ ] Bestehende Auswertungen (`token-history`, `estimate`, `calibrate`) funktionieren unverändert.

**Nicht-Ziele (explizit):**
- Keine neue Preislogik und keine Kostenschätzung für lokale Modelle.
- Keine Rollen-Semantik; SPEC-0053 liefert nur zusätzlichen Kontext (Rolle, Run, Versuch).
- Kein Netzwerkzugriff zur Nachermittlung von Usage.

## 3. Architektur & Design Patterns

### Decorator: `RecordingProvider`
Die Factory (SPEC-0008) umhüllt jeden erzeugten Provider mit einem `RecordingProvider`. Er misst
die Dauer, liest die Usage aus dem Ergebnis und übergibt sie mit Komponente und optionalem Kontext
an den `UsageRecorder`. Aufrufstellen müssen dafür nichts tun; ein vergessener Datensatz ist
strukturell ausgeschlossen.

→ [Refactoring Guru: Decorator](https://refactoring.guru/design-patterns/decorator)

### Adapter: Usage je Provider
Jeder Provider übersetzt seine native Antwort in `UsageMetadata` (Envelope von `claude --print`,
OpenAI-kompatibles `usage`-Objekt, Anthropic-API, Schätzung bei HuggingFace).

## 4. Funktionale Anforderungen

- **FR-01:** `UsageMetadata` bekommt die Felder `reasoning_tokens`, `finish_reason`, `latency_ms`
  und `server_model` (vom Server gemeldeter Modellname), zusätzlich zu den bestehenden Feldern.
  `estimated: true` kennzeichnet geschätzte Werte.
- **FR-02:** `claude-cli` liest die Usage aus dem JSON-Envelope von `claude --print --output-format
  json` (`usage.input_tokens`, `usage.output_tokens`, `usage.cache_creation_input_tokens`,
  `usage.cache_read_input_tokens`) sowie das Modell. Fehlt das Envelope oder die Usage, bleibt
  `usage` leer und ein Warnhinweis wird geloggt, ohne den Aufruf scheitern zu lassen.
- **FR-03:** `openai-compat` liest `usage.completion_tokens_details.reasoning_tokens` (falls
  vorhanden), `choices[0].finish_reason` und `model` der Antwort.
- **FR-04:** `CodeGenProvider.generate` liefert ein Ergebnisobjekt mit Dateien, Erklärung und
  Usage. Bestehende Aufrufer, die ein Tupel `(files, explanation)` erwarten, funktionieren über
  eine Übergangs-Schnittstelle weiter, bis SPEC-0058 sie ablöst.
- **FR-05:** Ein `UsageRecorder` persistiert Datensätze in `token_usage` in `.sdd/evaluations.db`.
  Die Migration ist additiv und fügt die Spalten `reasoning_tokens`, `finish_reason`, `latency_ms`,
  `server_model`, `estimated`, `role`, `run_id`, `attempt`, `outcome` und `role_version` hinzu
  (alle nullable). Die letzten fünf füllt nur die Pipeline (SPEC-0053).
- **FR-06:** Die Provider-Factory umhüllt jeden Provider mit dem `RecordingProvider` (Decorator).
  Aufrufer können optional Kontext übergeben (`spec_id`, `task_id`, Rollenkontext). Direkte
  Instanziierungen von Providern außerhalb der Factory werden auf die Factory umgestellt.
- **FR-07:** Die Web-API schreibt Usage künftig über den `UsageRecorder`. `.sdd/ai_usage.json`
  wird nur noch gelesen (Altbestand) und beim nächsten `sdd upgrade` in `token_usage` übernommen.
- **FR-08:** `sdd token-history` zeigt zusätzlich die Spalten Reasoning-Tokens und, falls
  vorhanden, Rolle; `--export` schreibt alle neuen Spalten in die CSV.
- **FR-09:** Scheitert das Persistieren (DB gesperrt, Datei nicht beschreibbar), wird ein
  Warnhinweis geloggt; der LLM-Aufruf selbst gilt nicht als gescheitert.

## 5. Nicht-funktionale Anforderungen

| Kategorie      | Anforderung                                                            |
|----------------|------------------------------------------------------------------------|
| Performance    | Erfassen kostet pro Aufruf weniger als 20 ms.                          |
| Datenschutz    | Prompts und Antworten werden nicht gespeichert, nur Zahlen und Metadaten. |
| Keyfreiheit    | Kein Teil der Erfassung setzt `ANTHROPIC_API_KEY` voraus.              |
| Kompatibilität | Bestehende Zeilen und Abfragen bleiben gültig (additive Migration).    |

## 6. Akzeptanzkriterien (Gherkin)

```gherkin
Feature: Usage-Erfassung

  Scenario: claude-cli liefert Usage aus dem Envelope
    Given llm.completion.provider ist claude-cli
    And claude --print liefert ein Envelope mit usage.input_tokens 1200 und output_tokens 300
    When sdd spec review SPEC-0900 einen LLM-Aufruf macht
    Then enthält token_usage einen Datensatz mit input_tokens 1200 und output_tokens 300

  Scenario: Reasoning-Tokens bei openai-compat
    Given der Server antwortet mit completion_tokens_details.reasoning_tokens 800
    When ein Aufruf über openai-compat erfolgt
    Then enthält der Datensatz reasoning_tokens 800 und finish_reason

  Scenario: Kein Aufruf ohne Datensatz
    Given alle Komponenten der Factory mit einem Fake-Provider
    When jede Komponente einmal aufgerufen wird
    Then gibt es je Aufruf genau einen Datensatz

  Scenario: Persistenzfehler bricht den Aufruf nicht ab
    Given evaluations.db ist schreibgeschützt
    When ein LLM-Aufruf erfolgt
    Then liefert der Aufruf sein Ergebnis und ein Warnhinweis wird geloggt
```

## 7. Edge Cases & Fehlerfälle

- Envelope von `claude --print` in älteren CLI-Versionen ohne `usage`: leere Usage, Warnhinweis.
- Streaming-Antworten ohne Usage-Block: `estimated: true` mit Tokenschätzung, falls ein Tokenizer
  verfügbar ist, sonst leer.
- Parallele Aufrufe (`max_concurrent`): Schreibzugriffe auf SQLite werden serialisiert.

## 8. Contracts (was wird garantiert)

| Contract-ID | Typ      | Was wird garantiert?                                          |
|-------------|----------|---------------------------------------------------------------|
| CON-XXXX    | data     | `token_usage` 2.0: additive Spalten, Migration                |
| CON-XXXX    | behavior | Usage-Abbildung je Provider und Erfassung über den Decorator  |

## 9. Tests (wie wird verifiziert)

| Test-ID  | Level       | Was prüft der Test?                                         |
|----------|-------------|-------------------------------------------------------------|
| TST-XXXX | unit        | Envelope-Parsing `claude-cli`, Reasoning-Tokens `openai-compat` |
| TST-XXXX | unit        | Migration: alte Zeilen gültig, neue Spalten nullable        |
| TST-XXXX | integration | Jede Factory-Komponente erzeugt genau einen Datensatz       |
| TST-XXXX | acceptance  | Gherkin-Szenarien aus Abschnitt 6                           |

## 10. Offene Fragen

- [ ] Soll `sdd estimate` künftig Reasoning-Tokens getrennt ausweisen? Vorschlag: ja, als eigene
      Spalte, ohne die Schätzlogik zu ändern.

## 11. Änderungshistorie

| Datum      | Version | Autor         | Änderung                                                   |
|------------|---------|---------------|------------------------------------------------------------|
| 2026-09-25 | 0.1.0   | Boris, Claude | Aus SPEC-0053 FR-06/FR-07 (0.4.0) ausgelagert und erweitert |
