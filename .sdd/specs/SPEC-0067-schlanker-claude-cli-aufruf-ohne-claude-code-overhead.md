---
id: SPEC-0067
title: Schlanker claude-cli-Aufruf ohne Claude-Code-Overhead
type: feature
status: in-progress
owner: borisbrue
created: 2026-10-06
updated: '2026-10-06'
version: 0.2.0
priority: medium
tags:
- llm
- claude-cli
- keyless
- tokens
depends_on:
- SPEC-0008
- SPEC-0050
- SPEC-0060
contracts:
- CON-0233
tests:
- TST-0262
fr_test_map:
  FR-01:
  - TST-0262
  FR-02:
  - TST-0262
  FR-03:
  - TST-0262
  FR-04:
  - TST-0262
  FR-05:
  - TST-0262
started_at: '2026-10-06T20:23:25Z'
---
# Schlanker claude-cli-Aufruf ohne Claude-Code-Overhead

> **Status:** draft · **Owner:** borisbrue · **Version:** 0.2.0

## 1. Kontext & Motivation

Im keyfreien Betrieb (SPEC-0050) läuft jeder LLM-Aufruf von sdd-framer über
`ClaudeCliCompletionProvider`, also über `claude --print --output-format json -p <prompt>`. Claude
Code startet dabei als vollständiger Agent: eigener System-Prompt, alle Tool-Definitionen,
MCP-Server, Hooks, CLAUDE.md-Dateien und der Auto-Memory-Index des Projekts. Nichts davon wird
gebraucht. Alle Aufrufer (Pipeline-Rollen, Review, Regression-Check, Web-API …) betten ihren
Kontext vollständig in den Prompt ein und erwarten Text oder JSON zurück; der Provider ist ein
reiner Completion-Provider (CON-0022), dieselbe Schnittstelle bedienen `anthropic` und
`openai-compat` ohne Tools.

Gemessen am 2026-10-06 (Claude Code 2.1.292, Prompt „Antworte nur mit: ok“, Summe aus
`input_tokens`, `cache_creation_input_tokens` und `cache_read_input_tokens`):

| Aufruf | Input-Tokens |
|---|---|
| heute, im Projektverzeichnis | 28.161 |
| `--system-prompt x --tools "" --setting-sources "" --strict-mcp-config` | 1.349 |
| dazu `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` | 887 |

Eine Pipeline erzeugt pro Feature 25–40 Rollenaufrufe; der Overhead summiert sich auf rund
0,7–1,1 Mio. Tokens je Feature und ist größer als der eigentliche Rolleninhalt (8–20k je Aufruf).

Zweiter Befund an derselben Stelle: Der Prompt wird als einzelnes argv-Argument übergeben. Linux
begrenzt ein einzelnes Argument auf 128 KiB (`MAX_ARG_STRLEN`); ab rund 32k Tokens scheitert der
Aufruf mit `OSError: [Errno 7] Argument list too long`. Der Implementer darf laut seinen
`input_budgets` bis ~49k Tokens Kontext bekommen.

### Abgrenzung
- **SPEC-0060:** Die Usage-Auswertung des Envelopes bleibt unverändert.
- **SPEC-0050/ADR-0005:** Claude-CLI wird weiterhin nur in `llm/providers/claude_cli.py` aufgerufen.
- **Session-Rollen** (`/sdd-implement`, `/sdd-supervise`) laufen in einer Claude-Code-Sitzung, nicht
  über diesen Provider, und sind nicht betroffen.

## 2. Zielsetzung

**Primärziel:** Ein `claude-cli`-Aufruf kostet nur den Prompt des Aufrufers plus einen minimalen,
festen Sockel und funktioniert auch mit Prompts über 128 KiB.

**Erfolgskriterien (messbar):**
- [x] Ein Aufruf mit dem Prompt „Antworte nur mit: ok“ aus dem Projektverzeichnis meldet in Summe
      weniger als 2.000 Input-Tokens (heute 28.161; nach Umsetzung 567).
- [x] Ein Prompt mit 200.000 Zeichen wird ohne `OSError` an `claude` übergeben (TST-0262 TC-04).
- [x] Alle bestehenden Aufrufer funktionieren unverändert (gleiche Schnittstelle, gleiche Rückgabe).

**Nicht-Ziele (explizit):**
- Keine Konfigurationsoption, um den alten Agent-Modus wieder einzuschalten; kein Aufrufer braucht
  ihn.
- Keine Änderung an Kontextquellen, `input_budgets` oder Retry-Logik der Pipeline.
- Kein `--bare`: Es verlangt zwingend `ANTHROPIC_API_KEY` und widerspricht dem keyfreien Betrieb.
- Keine Änderung an Modellwahl oder `max_tokens` (die CLI kennt weiterhin kein Output-Limit).

## 3. Architektur & Design Patterns

### Adapter: Claude Code als reine Completion-Engine
`ClaudeCliCompletionProvider` adaptiert die Claude-Code-CLI an `CompletionProvider` (CON-0022).
Der Adapter reicht nur durch, was die Zielschnittstelle kennt: Prompt rein, Text und Usage raus.
Fähigkeiten des Adaptees, die die Schnittstelle nicht kennt (Tools, MCP, Hooks, Memory), schaltet
er ab, statt sie still mitlaufen zu lassen.

→ [Refactoring Guru: Adapter](https://refactoring.guru/design-patterns/adapter)

### Facade: Aufrufdetails an einer Stelle
Flags, Umgebungsvariablen und die Übergabe per stdin baut eine einzige Funktion des Providers.
Aufrufer sehen davon nichts; ändert sich die CLI, ändert sich nur diese Funktion (ADR-0005).

→ [Refactoring Guru: Facade](https://refactoring.guru/design-patterns/facade)

## 4. Funktionale Anforderungen

- **FR-01:** Der Provider ruft `claude` mit `--print --output-format json` sowie
  `--tools ""`, `--setting-sources ""` und `--strict-mcp-config` auf. Damit stehen dem Aufruf
  keine Tools, keine Einstellungen (inkl. Hooks und Berechtigungen) und keine MCP-Server zur
  Verfügung.
- **FR-02:** Der Provider übergibt `system_prompt` per `--system-prompt <text>`. Ohne
  `system_prompt` übergibt er `--system-prompt ""`, damit der Claude-Code-System-Prompt nie
  geladen wird. Der Prompt enthält keinen `<system>`-Präfix mehr.
- **FR-03:** Der Provider setzt für den Kindprozess `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`; die
  übrige Umgebung erbt er unverändert.
- **FR-04:** Der Provider übergibt den Prompt über stdin, nicht als Kommandozeilenargument.
  stdin, stdout und stderr sind UTF-8, unabhängig von der Locale.
- **FR-05:** Endet `claude` mit einem Exit-Code ungleich 0 und liefert kein JSON-Envelope, wirft
  der Provider `RuntimeError` mit Exit-Code und den letzten 500 Zeichen von stderr. Liefert er ein
  Envelope, gilt das bisherige Verhalten (Text und Usage aus dem Envelope).

## 5. Nicht-funktionale Anforderungen

| Kategorie      | Anforderung                                                              |
|----------------|--------------------------------------------------------------------------|
| Kosten         | Fester Sockel je Aufruf < 2.000 Input-Tokens (Messung siehe Kontext).    |
| Keyfreiheit    | Kein Flag und keine Variable setzt `ANTHROPIC_API_KEY` voraus.           |
| Sicherheit     | Ohne Tools kann ein Aufruf weder Dateien lesen noch schreiben noch Befehle ausführen. |
| Kompatibilität | Schnittstelle und Rückgabe von `complete()` bleiben unverändert (CON-0022). |

## 6. Akzeptanzkriterien (Gherkin)

```gherkin
Feature: Schlanker claude-cli-Aufruf

  Scenario: Agent-Fähigkeiten sind abgeschaltet
    When der Provider complete("Hallo") aufruft
    Then enthält der claude-Aufruf --tools "", --setting-sources "" und --strict-mcp-config
    And die Umgebung des Kindprozesses enthält CLAUDE_CODE_DISABLE_AUTO_MEMORY=1

  Scenario: System-Prompt als echter System-Prompt
    When der Provider complete("Hallo", system_prompt="Sei knapp.") aufruft
    Then enthält der claude-Aufruf --system-prompt "Sei knapp."
    And der übergebene Prompt ist genau "Hallo"

  Scenario: Ohne System-Prompt
    When der Provider complete("Hallo") aufruft
    Then enthält der claude-Aufruf --system-prompt ""

  Scenario: Großer Prompt
    Given ein Prompt mit 200.000 Zeichen
    When der Provider ihn aufruft
    Then wird der Prompt über stdin übergeben und steht nicht in der Argumentliste

  Scenario: CLI scheitert ohne Envelope
    Given claude endet mit Exit-Code 2, leerem stdout und stderr "error: unknown option '--tools'"
    When der Provider complete("Hallo") aufruft
    Then wirft er RuntimeError mit Exit-Code 2 und "unknown option"
```

## 7. Edge Cases & Fehlerfälle

- Ältere Claude-Code-Versionen ohne `--tools`/`--setting-sources`: Die CLI bricht mit Fehler ab;
  FR-05 macht das sichtbar, statt leeren Text zurückzugeben.
- Exit-Code ≠ 0 mit Envelope (`is_error: true`): unverändert, der Text des Envelopes wird
  zurückgegeben, die Usage erfasst.
- Exit-Code 0 ohne Envelope: unverändert, roher stdout mit `source: unavailable`.
- Timeout: unverändert `RuntimeError` mit Timeout-Hinweis.
- Historische Token-Daten (SPEC-0011): Datensätze vor dieser Änderung enthalten den alten Sockel
  von rund 28k Tokens je Aufruf. `sdd estimate` schätzt bis zur nächsten Kalibrierung zu hoch;
  das ist die sichere Richtung, eine Bereinigung der Altdaten ist kein Ziel.

## 8. Contracts (was wird garantiert)

| Contract-ID | Typ      | Was wird garantiert?                                      |
|-------------|----------|-----------------------------------------------------------|
| CON-0233    | behavior | Aufrufform von `claude`: Flags, Umgebung, stdin, Fehler   |

## 9. Tests (wie wird verifiziert)

| Test-ID  | Level      | Was prüft der Test?                                 |
|----------|------------|-----------------------------------------------------|
| TST-0262 | acceptance | Szenarien aus CON-0233 gegen den echten Provider mit Fake-`claude` im PATH |

## 10. Offene Fragen

- [x] Neutrales Arbeitsverzeichnis statt `CLAUDE_CODE_DISABLE_AUTO_MEMORY`? Nein: Die Variable
      spart dasselbe (887 vs. 882 Tokens), und das Arbeitsverzeichnis bleibt wie bisher.

## 11. Änderungshistorie

| Datum      | Version | Autor            | Änderung            |
|------------|---------|------------------|---------------------|
| 2026-10-06 | 0.1.0   | borisbrue, Claude | Initiale Erstellung |
| 2026-10-06 | 0.2.0   | borisbrue, Claude | Contract-Review: UTF-8 explizit (FR-04), Fehlerszenario an CON-0233 angeglichen |
