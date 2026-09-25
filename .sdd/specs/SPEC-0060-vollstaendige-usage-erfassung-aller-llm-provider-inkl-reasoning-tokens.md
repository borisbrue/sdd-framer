---
id: SPEC-0060
title: "Vollständige Usage-Erfassung aller LLM-Provider inkl. Reasoning-Tokens"
type: feature
status: draft
owner: "Boris"
created: 2026-09-25
updated: 2026-09-25
version: 0.3.0
priority: high
tags: [llm, token-tracking, usage, keyless]
depends_on: [SPEC-0003, SPEC-0005, SPEC-0008, SPEC-0011, SPEC-0013, SPEC-0035, SPEC-0050]
contracts: [CON-0206, CON-0207]
tests: []
---

# Vollständige Usage-Erfassung aller LLM-Provider inkl. Reasoning-Tokens

> **Status:** draft · **Owner:** Boris · **Version:** 0.3.0

## 1. Kontext & Motivation

sdd-framer erfasst den Tokenverbrauch heute lückenhaft:

- `claude-cli`, der Default im keyfreien Betrieb, liefert `usage: None`. Deshalb bleiben
  `sdd token-history` und `sdd estimate` leer, obwohl `claude --print --output-format json` die
  Usage im Envelope mitliefert (`usage.input_tokens`, `output_tokens`,
  `cache_creation_input_tokens`, `cache_read_input_tokens`,
  `output_tokens_details.thinking_tokens`, Modell in `modelUsage`, `stop_reason`).
- `openai-compat` liest nur `prompt_tokens`/`completion_tokens`. Reasoning-Tokens
  (`completion_tokens_details.reasoning_tokens`) und `finish_reason` gehen verloren.
- `CodeGenProvider.generate` gibt gar keine Usage zurück.
- Persistiert wird nur an zwei Stellen (`lifecycle.py`, `sub_agent.py`); `decompose`, `task-exec`,
  `task-loop`, Evaluator und Orchestrator schreiben nichts. `decompose.py` und
  `web/api/analyzer.py` erzeugen `ClaudeCliCompletionProvider` direkt. Die Web-API führt mit
  `.sdd/ai_usage.json` einen zweiten Speicher.

Die Rollen-Pipeline (SPEC-0053) und der Benchmark (SPEC-0056) brauchen verlässliche Zahlen je
Aufruf, einschließlich Reasoning-Tokens. Diese Spec schließt die Lücke unabhängig von der Pipeline.

### Abgrenzung
- **SPEC-0008/SPEC-0050 (Factory):** Die Factory bleibt der einzige Ort, an dem Provider entstehen;
  sie umhüllt sie zusätzlich. Die umhüllten Provider haben dieselbe Schnittstelle.
- **SPEC-0011 (Schätzung):** `sdd estimate` und `calibrate` lesen weiter dieselbe Tabelle; die
  Erweiterung ist additiv.
- **SPEC-0003 (Web-API):** Die AI-Routes schreiben künftig über die Erfassung und lesen aus
  `token_usage`; `.sdd/ai_usage.json` wird migriert.
- **SPEC-0004/SPEC-0005/SPEC-0013:** Evaluator, Orchestrator, Analyzer und HuggingFace werden über
  die Factory automatisch erfasst; HuggingFace liefert geschätzte Werte.
- **SPEC-0053:** Die Pipeline hängt ihren Kontext (Rolle, Versuch, Ergebnis …) über den offenen
  Aufrufkontext an; `token_usage` kennt keine Rollen-Semantik.

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
- Keine Rollen-Semantik in `token_usage`; Verbraucher hängen eigenen Kontext an.
- Kein Netzwerkzugriff zur Nachermittlung von Usage.

## 3. Architektur & Design Patterns

### Factory Method + Decorator: umhüllte Provider
Die Factory ist der einzige Ort, an dem Provider entstehen. Sie umhüllt jeden Provider mit einem
Decorator derselben Schnittstelle: `RecordingCompletionProvider` für `CompletionProvider`,
`RecordingCodeGenProvider` für `CodeGenProvider`. Der Decorator misst die Dauer, liest die Usage
aus dem Ergebnis und meldet einen `UsageRecord`. Aufrufstellen müssen nichts tun; ein vergessener
Datensatz ist strukturell ausgeschlossen.

→ [Refactoring Guru: Decorator](https://refactoring.guru/design-patterns/decorator) ·
[Factory Method](https://refactoring.guru/design-patterns/factory-method)

### Adapter: Usage je Provider
Jeder Provider übersetzt seine native Antwort in `UsageMetadata`. Der Vertrag ist für alle gleich:
Es gibt **immer** ein `UsageMetadata`-Objekt, und `source` sagt, woher die Zahlen kommen:
`reported` (vom Server/CLI gemeldet), `estimated` (geschätzt) oder `unavailable` (keine Zahlen).

→ [Refactoring Guru: Adapter](https://refactoring.guru/design-patterns/adapter)

### Observer: Senken
Der Decorator meldet jeden `UsageRecord` an die registrierten `UsageSink`s. Standard ist die
SQLite-Senke (`token_usage` in `.sdd/evaluations.db`); Tests registrieren eine Fake-Senke. Weitere
Senken (z. B. Benchmark-Export) kommen ohne Änderung am Decorator hinzu.

→ [Refactoring Guru: Observer](https://refactoring.guru/design-patterns/observer)

### Aufrufkontext
Kontext (Spec, Task, Pipeline-Run, Rolle, …) fließt nicht durch die Provider-Schnittstelle, sondern
über eine Kontextvariable: `with usage_context(spec_id="SPEC-0900", run_id=…, role=…):`. Der
Decorator liest sie beim Melden. Provider und ihre Signaturen bleiben unverändert. Unbekannte
Schlüssel landen im offenen Feld `context`; nur `spec_id`, `task_id` und `run_id` sind eigene,
indizierbare Spalten.

## 4. Funktionale Anforderungen

- **FR-01:** `UsageMetadata` bekommt die Felder `reasoning_tokens`, `finish_reason`, `latency_ms` (wird in `duration_ms` gespeichert),
  `server_model` (vom Server gemeldeter Modellname) und `source` (`reported|estimated|unavailable`).
  Jeder Provider liefert immer ein `UsageMetadata`-Objekt, nie `None`.
- **FR-02:** `claude-cli` liest aus dem JSON-Envelope von `claude --print --output-format json`:
  `usage.input_tokens`, `usage.output_tokens`, `usage.cache_creation_input_tokens`,
  `usage.cache_read_input_tokens`, `usage.output_tokens_details.thinking_tokens` (→
  `reasoning_tokens`), das Modell aus dem Schlüssel von `modelUsage` und `stop_reason` (→
  `finish_reason`). Fehlt das Envelope oder die Usage, ist `source: unavailable` und ein Hinweis
  wird geloggt; der Aufruf scheitert nicht.
- **FR-03:** `openai-compat` liest `usage.completion_tokens_details.reasoning_tokens` (falls
  vorhanden), `choices[0].finish_reason` und `model` der Antwort.
- **FR-04:** `CodeGenProvider.generate` liefert ein Ergebnisobjekt mit Dateien, Erklärung und
  Usage. Bestehende Aufrufer, die ein Tupel `(files, explanation)` erwarten, funktionieren über
  eine Übergangs-Schnittstelle weiter, bis SPEC-0058 sie ablöst.
- **FR-05:** Die SQLite-Senke persistiert in `token_usage` (`.sdd/evaluations.db`). Die Migration
  ist additiv und fügt die nullable Spalten `reasoning_tokens`, `finish_reason`, `server_model`,
  `source`, `run_id` und `context_json` hinzu; die Dauer steht weiter in `duration_ms`. `context_json` enthält alle übrigen
  Kontextschlüssel als JSON-Objekt.
- **FR-06:** Die Provider-Factory umhüllt jeden Completion- und CodeGen-Provider mit dem passenden
  Decorator. `decompose.py` und `web/api/analyzer.py` holen ihren Provider über die Factory statt
  ihn direkt zu erzeugen.
- **FR-07:** `usage_context(**kw)` setzt den Aufrufkontext für die Dauer eines `with`-Blocks;
  verschachtelte Blöcke ergänzen bzw. überschreiben Schlüssel. Ohne Kontext werden nur
  `component` und `model` erfasst.
- **FR-08:** Die Web-API schreibt Usage über die Erfassung (Kontext `origin: web`) und liest
  Zusammenfassung und Liste aus `token_usage`. `.sdd/ai_usage.json` wird beim nächsten
  `sdd upgrade` in `token_usage` übernommen und danach nicht mehr geschrieben.
- **FR-09:** `sdd token-history` zeigt zusätzlich die Spalte Reasoning-Tokens; `--export` schreibt
  alle neuen Spalten in die CSV.
- **FR-10:** Scheitert eine Senke (DB gesperrt, Datei nicht beschreibbar), wird ein Warnhinweis
  geloggt; der LLM-Aufruf selbst gilt nicht als gescheitert, und andere Senken erhalten den
  Datensatz trotzdem.
- **FR-11:** `sdd estimate`, `calibrate`, die Summen von `token-history` und die Web-Zusammenfassung
  schließen Zeilen mit `source: unavailable` aus Mittelwerten und Summen aus und nennen ihre Anzahl.

## 5. Nicht-funktionale Anforderungen

| Kategorie      | Anforderung                                                            |
|----------------|------------------------------------------------------------------------|
| Performance    | Erfassen kostet pro Aufruf weniger als 20 ms.                          |
| Datenschutz    | Prompts und Antworten werden nicht gespeichert, nur Zahlen und Metadaten. |
| Keyfreiheit    | Kein Teil der Erfassung setzt `ANTHROPIC_API_KEY` voraus.              |
| Kompatibilität | Bestehende Zeilen und Abfragen bleiben gültig (additive Migration).    |
| Nebenläufigkeit | Parallele Aufrufe (`max_concurrent`) schreiben serialisiert; der Kontext ist je Thread/Task getrennt. |

## 6. Akzeptanzkriterien (Gherkin)

```gherkin
Feature: Usage-Erfassung

  Scenario: claude-cli liefert Usage aus dem Envelope
    Given claude --print liefert ein Envelope mit usage.input_tokens 1200, output_tokens 300 und thinking_tokens 40
    When ein Aufruf über claude-cli erfolgt
    Then enthält token_usage einen Datensatz mit input_tokens 1200, output_tokens 300, reasoning_tokens 40 und source reported

  Scenario: Reasoning-Tokens bei openai-compat
    Given der Server antwortet mit completion_tokens_details.reasoning_tokens 800
    When ein Aufruf über openai-compat erfolgt
    Then enthält der Datensatz reasoning_tokens 800 und finish_reason

  Scenario: Kontext landet im Datensatz
    Given ein Aufruf innerhalb von usage_context(spec_id="SPEC-0900", run_id="r1", role="implementer")
    Then hat der Datensatz spec_id SPEC-0900, run_id r1 und context_json mit role implementer

  Scenario: Kein Aufruf ohne Datensatz
    Given alle Komponenten der Factory mit einem Fake-Provider
    When jede Komponente einmal aufgerufen wird
    Then gibt es je Aufruf genau einen Datensatz

  Scenario: Senkenfehler bricht den Aufruf nicht ab
    Given evaluations.db ist schreibgeschützt
    When ein LLM-Aufruf erfolgt
    Then liefert der Aufruf sein Ergebnis und ein Warnhinweis wird geloggt
```

## 7. Edge Cases & Fehlerfälle

- Envelope von `claude --print` in älteren CLI-Versionen ohne `usage`: `source: unavailable`,
  Hinweis.
- Streaming-Antworten ohne Usage-Block: `source: estimated`, falls ein Tokenizer verfügbar ist,
  sonst `unavailable`.
- Provider wirft eine Ausnahme: Der Decorator meldet einen Datensatz mit `finish_reason: error`
  und `source: unavailable` und gibt die Ausnahme unverändert weiter.

## 8. Contracts (was wird garantiert)

| Contract-ID | Typ      | Was wird garantiert?                                          |
|-------------|----------|---------------------------------------------------------------|
| CON-0206    | data     | `token_usage` 2.0: Zeilenschema, additive Spalten, `context_json` |
| CON-0207    | behavior | Usage je Provider, Decorator, Aufrufkontext, Senken, Fehlertoleranz |

## 9. Tests (wie wird verifiziert)

| Test-ID  | Level       | Was prüft der Test?                                         |
|----------|-------------|-------------------------------------------------------------|
| TST-XXXX | unit        | Zeilenschema und Migration                                  |
| TST-XXXX | acceptance  | Gherkin-Szenarien aus Abschnitt 6 und der Contracts         |

## 10. Offene Fragen

- [ ] Soll `sdd estimate` künftig Reasoning-Tokens getrennt ausweisen? Vorschlag: ja, als eigene
      Spalte, ohne die Schätzlogik zu ändern.

## 11. Änderungshistorie

| Datum      | Version | Autor         | Änderung                                                   |
|------------|---------|---------------|------------------------------------------------------------|
| 2026-09-25 | 0.1.0   | Boris, Claude | Aus SPEC-0053 FR-06/FR-07 (0.4.0) ausgelagert und erweitert |
| 2026-09-25 | 0.2.0   | Boris, Claude | Review: Patterns Decorator/Adapter/Factory Method/Observer; keine Rollen-Spalten, offener Kontext `context_json` + `run_id` (SRP, OCP); `UsageMetadata` immer vorhanden mit `source` (LSP); Kontext über Kontextvariable (ISP); `UsageSink`-Abstraktion (DIP); Abgrenzung zu SPEC-0003/0004/0005/0008/0011/0013 |
| 2026-09-25 | 0.3.0   | Boris, Claude | Contract-Review: keine `latency_ms`-Spalte; `unavailable`-Zeilen aus Mittelwerten ausgeschlossen (FR-11); reservierte Kontextschlüssel; `register_sink` |
