---
id: SPEC-0068
title: 'Cachebarer Rollen-Prompt: stabile Quellen im System-Prompt'
type: feature
status: implemented
owner: borisbrue
created: 2026-10-06
updated: '2026-10-06'
version: 0.2.0
priority: medium
tags:
- llm
- pipeline
- tokens
- cache
depends_on:
- SPEC-0053
- SPEC-0067
contracts:
- CON-0234
- CON-0233
tests:
- TST-0263
- TST-0262
fr_test_map:
  FR-01:
  - TST-0263
  FR-02:
  - TST-0263
  FR-03:
  - TST-0263
  FR-04:
  - TST-0263
  FR-05:
  - TST-0262
started_at: '2026-10-06T21:06:44Z'
---
# Cachebarer Rollen-Prompt: stabile Quellen im System-Prompt

> **Status:** draft · **Owner:** borisbrue · **Version:** 0.2.0

## 1. Kontext & Motivation

Der `RoleRunner` (SPEC-0053) baut je Rollenaufruf einen Prompt aus allen Kontextquellen der Rolle
und hängt einen Nonce an; der System-Prompt ist nur der Rollen-Prompt. Wiederholt eine Rolle einen
Versuch (GREEN-Gate rot, Review abgelehnt, ungültige Ausgabe), sind die meisten Quellen
unverändert: spec, contracts, agents_md, repo_map, current_files (nach einem roten Versuch stellt
der Mediator die Dateien wieder her), dependency_api, task und test_file. Neu sind nur
test_output, review, history, diff und gate_results.

Gemessen am 2026-10-06 mit `claude --print` (Claude Code 2.1.292, ~35k Tokens Kontext):

| Aufbau | Wiederholungsversuch mit neuer Testausgabe |
|---|---|
| alles im Prompt (heute) | 35.566 Tokens neu in den Cache geschrieben, 0 gelesen |
| stabile Quellen im System-Prompt | 545 geschrieben, 35.033 aus dem Cache gelesen |

Claude Code setzt einen Cache-Punkt ans Ende des System-Prompts und einen ans Ende der Nachricht.
Ein gleicher Anfang mit anderem Ende trifft den Nachrichten-Cache nicht. Heute macht der Nonce
jeden Prompt einzigartig: Jeder Aufruf schreibt seinen ganzen Prompt in den Cache und liest ihn
nie. Ein angehängter System-Prompt (`--append-system-prompt-file`) und mehrere Nachrichten
(`--input-format stream-json`) bringen keinen zweiten Cache-Punkt (gemessen).

Eine leere Datei hinter `--system-prompt-file` lädt keinen Default-System-Prompt (gemessen: 606
Input-Tokens für „Antworte nur mit: ok“, wie mit `--system-prompt ""`).

Auch Server mit Präfix-Cache (llama.cpp, vLLM über `openai-compat`) profitieren davon, wenn der
gleichbleibende Teil vorn steht.

### Abgrenzung
- **SPEC-0053:** Rollen, Quellen, Budgets und Nonce bleiben; nur die Aufteilung auf System-Prompt
  und Prompt ändert sich.
- **SPEC-0067/CON-0233:** Der `claude-cli`-Provider übergibt den System-Prompt künftig als Datei,
  weil er jetzt groß werden kann.
- **SPEC-0055/0056 (Evals, Benchmark):** Cache-Nonce je Aufruf bleibt, er steht im Prompt.

## 2. Zielsetzung

**Primärziel:** Ein Wiederholungsversuch derselben Rolle mit unveränderten stabilen Quellen liest
den stabilen Teil aus dem Prompt-Cache, statt ihn neu zu schreiben.

**Erfolgskriterien (messbar):**
- [x] In einem Pipeline-Lauf sind die System-Prompts aller Versuche einer Rolle für dieselbe Task
      byte-gleich, solange sich ihre stabilen Quellen nicht ändern (TST-0263 TC-01).
- [x] Ein Wiederholungsversuch über `claude-cli` mit ~35k Tokens stabilem Kontext meldet mehr als
      90 % seiner Input-Tokens als `cache_read` (gemessen mit dem echten RoleRunner, Implementer,
      ~31k Kontext: Versuch 1 schreibt 31.392, Versuch 2 liest 30.815 und schreibt 578, 98,2 %).
- [x] System-Prompts über 128 KiB scheitern nicht an der argv-Grenze (TST-0262).

**Nicht-Ziele (explizit):**
- Kein Cache-Treffer über Task- oder Rollengrenzen hinweg; pro Aufruf gibt es nur einen
  nutzbaren Cache-Punkt.
- Keine Änderung an Quellen, `input_budgets`, Kürzung oder Retry-Logik.
- Keine Konfiguration, welche Quellen stabil sind; die Einteilung ist fest.
- Kein explizites `cache_control` im `anthropic`-Provider.

## 3. Architektur & Design Patterns

### Template Method: fester Ablauf im RoleRunner
Der Ablauf des RoleRunners bleibt (SPEC-0053 FR-06). Nur der Schritt „Prompt rendern“ liefert
zwei Teile statt einem: System-Prompt (Rollen-Prompt plus stabile Quellen) und Prompt (Anfrage,
wechselnde Quellen, Nonce).

→ [Refactoring Guru: Template Method](https://refactoring.guru/design-patterns/template-method)

### Adapter: Provider bleiben austauschbar
Die Schnittstelle `complete(prompt, system_prompt=…)` (CON-0022) ändert sich nicht. Jeder Provider
bildet `system_prompt` auf sein Mittel ab: `claude-cli` auf `--system-prompt-file`,
`openai-compat` auf die System-Nachricht, `anthropic` auf `system`.

→ [Refactoring Guru: Adapter](https://refactoring.guru/design-patterns/adapter)

## 4. Funktionale Anforderungen

- **FR-01:** `roles.SOURCE_KINDS` ordnet jeder Kontextquelle genau eine Einteilung zu, `stable`
  oder `volatile`; `CONTEXT_SOURCES` wird daraus abgeleitet. Wechselnd sind `test_output`,
  `review`, `history`, `diff` und `gate_results`. Eine neue Quelle ohne Einteilung kann es nicht
  geben (Review: Open/Closed).
- **FR-02:** Der RoleRunner übergibt als `system_prompt` den Rollen-Prompt, gefolgt von den
  gerenderten stabilen Quellen der Rolle in der Reihenfolge ihrer `inputs`. Als Prompt übergibt er
  `lead`, die gerenderten wechselnden Quellen in der Reihenfolge der `inputs` und den Nonce.
  Fehlen `lead` und wechselnde Quellen, steht wie bisher `purpose` vor dem Nonce.
- **FR-03:** Der System-Prompt enthält keine Werte, die je Aufruf wechseln (kein Nonce, keine
  Aufruf-ID, keine Zeitstempel, keine Versuchsnummer). Bei gleichen stabilen Quellen ist er
  byte-gleich.
- **FR-04:** `prompt_hash` wird über System-Prompt und Prompt ohne Nonce gebildet.
- **FR-05:** Der `claude-cli`-Provider schreibt den System-Prompt in eine temporäre Datei und
  übergibt sie per `--system-prompt-file`; die Datei wird nach dem Aufruf gelöscht, auch bei
  Fehler oder Timeout. Ohne `system_prompt` ist die Datei leer.

## 5. Nicht-funktionale Anforderungen

| Kategorie      | Anforderung                                                               |
|----------------|---------------------------------------------------------------------------|
| Kosten         | Wiederholungsversuch: > 90 % der Input-Tokens aus dem Cache (claude-cli). |
| Kompatibilität | Schnittstelle `complete()` und Rollendateien bleiben unverändert.         |
| Sicherheit     | Temporäre Datei nur für den eigenen Benutzer lesbar, immer gelöscht.      |

## 6. Akzeptanzkriterien (Gherkin)

```gherkin
Feature: Cachebarer Rollen-Prompt

  Scenario: Stabile Quellen im System-Prompt
    Given eine Task, deren Implementer dreimal am GREEN-Gate scheitert
    When die Pipeline läuft
    Then sind die System-Nachrichten der drei Implementer-Aufrufe byte-gleich
    And sie enthalten Spec, Contracts und den aktuellen Dateiinhalt
    And die Testausgabe steht nur in der Nutzer-Nachricht

  Scenario: Wechselnde Quellen im Prompt
    When der Implementer mit test_output und history aufgerufen wird
    Then enthält der Prompt die Testausgabe und history vor dem Nonce
    And der System-Prompt enthält weder Testausgabe noch Nonce

  Scenario: Großer System-Prompt über claude-cli
    Given ein System-Prompt mit 200.000 Zeichen
    When der claude-cli-Provider aufgerufen wird
    Then liest claude ihn aus der Datei hinter --system-prompt-file
    And die Datei existiert nach dem Aufruf nicht mehr
```

## 7. Edge Cases & Fehlerfälle

- Nach einer Review-Ablehnung ändern sich `current_files` (der grüne Stand bleibt). Der nächste
  Implementer-Versuch schreibt seinen System-Prompt neu; das ist erwartet.
- Supervisor-Anfragen (`lead`) wechseln je Entscheidung und stehen im Prompt.
- Timeout oder Abbruch von `claude`: die temporäre Datei wird trotzdem gelöscht.
- `openai-compat` mit Chat-Templates, die System-Nachrichten kürzen oder in die Nutzer-Nachricht
  falten: Der Rollen-Prompt steht schon heute dort, neu ist die Menge. Abgesichert über die
  Rollen-Evals (SPEC-0055) je Modellbelegung, nicht über eine Ausnahme im Runner.

## 8. Contracts (was wird garantiert)

| Contract-ID | Typ      | Was wird garantiert?                                   |
|-------------|----------|--------------------------------------------------------|
| CON-0234    | behavior | Aufteilung System-Prompt/Prompt im RoleRunner          |
| CON-0233    | behavior | Ergänzung: System-Prompt per `--system-prompt-file`    |

## 9. Tests (wie wird verifiziert)

| Test-ID  | Level      | Was prüft der Test?                                          |
|----------|------------|--------------------------------------------------------------|
| TST-0263 | acceptance | Pipeline-Lauf mit Fake-LLM: System-Nachrichten je Versuch    |
| TST-0262 | acceptance | Fake-`claude` liest `--system-prompt-file`, Datei gelöscht   |

## 10. Offene Fragen

- [x] Zweiter Cache-Punkt für Run-weite Quellen (Spec, Contracts) über Tasks hinweg? Nein:
      `--append-system-prompt-file` wird mit dem System-Prompt verschmolzen, `stream-json` erzeugt
      mehrere Gesprächsrunden (beides am 2026-10-06 gemessen).

## 11. Änderungshistorie

| Datum      | Version | Autor             | Änderung            |
|------------|---------|-------------------|---------------------|
| 2026-10-06 | 0.1.0   | borisbrue, Claude | Initiale Erstellung |
| 2026-10-06 | 0.2.0   | borisbrue, Claude | Spec-Review: `SOURCE_KINDS` statt Restmenge (O/C); Risiko System-Nachricht bei `openai-compat` |
