---
id: CON-0233
title: "Aufrufform des claude-cli-Providers"
type: behavior
format: gherkin
spec: SPEC-0067
version: 0.3.1
status: approved
artifact: ".sdd/contracts/behavior/aufrufform-des-claude-cli-providers.feature"
tests: ["TST-0262"]
---

# Contract: Aufrufform des claude-cli-Providers

> **Spec:** SPEC-0067 · **Typ:** Verhalten (Gherkin) · **Status:** approved

## Zweck

Legt fest, wie `ClaudeCliCompletionProvider` den Prozess `claude` startet: Flags, Umgebung,
Übergabe von Prompt und System-Prompt und Verhalten bei Fehlschlag (SPEC-0067 FR-01 bis FR-05, SPEC-0068 FR-05).
Ergänzt CON-0022 G-02; Usage-Auswertung des Envelopes bleibt bei CON-0207. Die Datei-Übergabe des
System-Prompts (INV-01) stammt aus SPEC-0068 FR-05; dort ist TST-0262 als Test für FR-05 eingetragen.

## Garantien

Die Szenarien im Artifact (`.sdd/contracts/behavior/aufrufform-des-claude-cli-providers.feature`)
sind **ausführbare Spezifikation**.

## Invarianten

- **INV-01:** Die Argumentliste ist genau `[<claude>, "--print", "--output-format", "json",
  "--tools", "", "--setting-sources", "", "--strict-mcp-config", "--system-prompt-file", <datei>]`.
  `<datei>` enthält den übergebenen `system_prompt` (UTF-8) oder ist leer, wenn keiner übergeben
  wurde; sie ist nur für den eigenen Benutzer les- und schreibbar (Modus `0600`) und existiert nach `complete()` nicht mehr,
  auch nach Exit-Code ≠ 0 oder Timeout
  (SPEC-0068 FR-05). Die Argumentliste enthält weder den Prompt
  noch den System-Prompt noch `-p`.
- **INV-02:** Der Prompt wird unverändert über stdin übergeben, ohne `<system>`-Präfix. stdin,
  stdout und stderr sind UTF-8, unabhängig von der Locale. Erreicht wird das über das Encoding
  der Pipes im Elternprozess, nicht über Umgebungsvariablen des Kindes (siehe INV-03).
- **INV-03:** Die Umgebung des Kindprozesses ist die des Elternprozesses plus
  `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`. Weitere Variablen werden weder gesetzt noch entfernt.
- **INV-04:** Endet der Prozess mit Exit-Code ≠ 0 und ist stdout kein JSON-Objekt mit `result`,
  wirft `complete()` `RuntimeError`; die Meldung enthält `Exit-Code <n>` und die letzten 500
  Zeichen von stderr. In allen anderen Fällen gilt CON-0022 G-02 und CON-0207 unverändert.
- **INV-05:** Überschreitet `claude` den Timeout, beendet der Provider den Kindprozess und wirft
  `RuntimeError` mit `Timeout nach <n>s`.

## Begriffe

| Begriff  | Definition |
|----------|------------|
| Envelope | JSON-Objekt mit dem Schlüssel `result` aus `claude --print --output-format json`; der zurückgegebene Text ist `str(result)` |
| Timeout  | Parameter `timeout` von `complete()` (CON-0022 G-02) |
