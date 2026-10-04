---
id: CON-0232
title: "S2-Fakten, Versuche je Stufe und Token-Report"
type: behavior
format: gherkin
spec: SPEC-0066
version: 0.2.0
status: approved
artifact: ".sdd/contracts/behavior/s2-fakten-versuche-je-stufe-und-token-report.feature"
tests: ["TST-0261"]
---

# Contract: S2-Fakten, Versuche je Stufe und Token-Report

> **Spec:** SPEC-0066 · **Typ:** Verhalten (Gherkin) · **Status:** approved

## Zweck

Legt fest, was der Supervisor an S2 nach einer Review-Ablehnung sieht, wann S2 ausgelöst wird,
wie eine leere Implementer-Ausgabe behandelt wird und was `sdd pipeline report` an Tokens zeigt
(SPEC-0066 FR-01 bis FR-04). Datenformen: CON-0200, CON-0202.

## Garantien

Die Szenarien im Artifact (`.sdd/contracts/behavior/s2-fakten-versuche-je-stufe-und-token-report.feature`)
sind **ausführbare Spezifikation**.

## Invarianten

- **INV-01:** War der letzte Versuch einer Task vor der Eskalation ein Review mit `verdict: fail`,
  enthält die S2-Anfrage `facts.review` mit `verdict` und `findings` dieses Reviews (höchstens 20
  Befunde, Begründung je höchstens 600 Zeichen). Sonst fehlt `facts.review`.
- **INV-02:** Jede Task zählt Versuche je Stufe in `state.json` (`stage_attempts` mit `test`,
  `implementation`, `review`); jeder Lauf der Rolle einer Stufe ist ein Versuch, auch ein
  ungültiger. S2 wird ausgelöst, sobald eine Stufe `max_attempts` erreicht. Eine
  Review-Ablehnung beginnt eine neue Runde: Sie setzt `implementation` auf 0; `review` begrenzt
  die Zahl der Runden. `attempts` ist die Zahl der Versuche der aktuellen Stufe.
  `retry_with_hint`, `reassign` und `reopen` setzen alle Stufenzähler und `attempts` auf 0.
  Fehlt `stage_attempts` (Run vor SPEC-0066), gelten 0.
- **INV-03:** Liefert der Implementer `files: []`, wird nichts geschrieben, die PathPolicy nicht
  befragt, das GREEN-Gate prüft den bestehenden Stand, und der Versuch zählt in
  `stage_attempts.implementation`. Bei grünem Stand folgt das Review mit dem Diff der Task gegen
  ihren Ausgangsstand.
- **INV-04:** `sdd pipeline report` zeigt je Rolle Aufrufe, Fehlversuche, Input, Output,
  Reasoning, Cache-Read, Cache-Write und Dauer. Der Claude-Anteil ist die Summe aus Input, Output,
  Cache-Read und Cache-Write der Rollen mit `claude-cli` oder `anthropic`, geteilt durch dieselbe
  Summe über alle Rollen. Rollen ohne Usage-Werte werden mit Namen genannt.
