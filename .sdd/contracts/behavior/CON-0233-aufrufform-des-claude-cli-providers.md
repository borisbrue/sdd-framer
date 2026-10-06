---
id: CON-0233
title: "Aufrufform des claude-cli-Providers"
type: behavior
format: gherkin
spec: SPEC-0067
version: 0.2.0
status: approved
artifact: ".sdd/contracts/behavior/aufrufform-des-claude-cli-providers.feature"
tests: ["TST-0262"]
---

# Contract: Aufrufform des claude-cli-Providers

> **Spec:** SPEC-0067 · **Typ:** Verhalten (Gherkin) · **Status:** review

## Zweck

Legt fest, wie `ClaudeCliCompletionProvider` den Prozess `claude` startet: Flags, Umgebung,
Übergabe von Prompt und System-Prompt und Verhalten bei Fehlschlag (SPEC-0067 FR-01 bis FR-05).
Ergänzt CON-0022 G-02; Usage-Auswertung des Envelopes bleibt bei CON-0207.

## Garantien

Die Szenarien im Artifact (`.sdd/contracts/behavior/aufrufform-des-claude-cli-providers.feature`)
sind **ausführbare Spezifikation**.

## Invarianten

- **INV-01:** Die Argumentliste ist genau `[<claude>, "--print", "--output-format", "json",
  "--tools", "", "--setting-sources", "", "--strict-mcp-config", "--system-prompt", <s>]`, wobei
  `<s>` der übergebene `system_prompt` ist oder `""`, wenn keiner übergeben wurde. Sie enthält
  weder den Prompt noch `-p`.
- **INV-02:** Der Prompt wird unverändert über stdin übergeben, ohne `<system>`-Präfix. stdin,
  stdout und stderr sind UTF-8, unabhängig von der Locale.
- **INV-03:** Die Umgebung des Kindprozesses ist die des Elternprozesses plus
  `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`. Weitere Variablen werden weder gesetzt noch entfernt.
- **INV-04:** Endet der Prozess mit Exit-Code ≠ 0 und ist stdout kein JSON-Objekt mit `result`,
  wirft `complete()` `RuntimeError`; die Meldung enthält den Exit-Code und die letzten 500
  Zeichen von stderr. In allen anderen Fällen gilt CON-0022 G-02 und CON-0207 unverändert.

## Begriffe

| Begriff  | Definition |
|----------|------------|
| Envelope | Das JSON-Objekt `{"type":"result","result":"<text>",…}` von `claude --print --output-format json` |
| Sockel   | Input-Tokens, die ein Aufruf unabhängig vom Prompt des Aufrufers kostet |
