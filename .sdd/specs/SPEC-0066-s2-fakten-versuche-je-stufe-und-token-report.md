---
id: SPEC-0066
title: "S2-Fakten, Versuche je Stufe und Token-Report"
type: feature
status: approved
owner: "Boris"
created: 2026-10-04
updated: 2026-10-04
version: 0.1.2
priority: high
tags: [pipeline, supervisor, usage]
depends_on: [SPEC-0053, SPEC-0060, SPEC-0063, SPEC-0064]
contracts:
- CON-0200
- CON-0202
- CON-0205
- CON-0232
tests:
- TST-0229
- TST-0231
- TST-0234
- TST-0261
fr_test_map:
  FR-01: [TST-0231, TST-0261]
  FR-02: [TST-0229, TST-0261]
  FR-03: [TST-0231, TST-0234, TST-0261]
  FR-04: [TST-0261]
---

# S2-Fakten, Versuche je Stufe und Token-Report

> **Status:** draft · **Owner:** Boris · **Version:** 0.1.2

## 1. Kontext & Motivation

Aus demselben Testlauf wie SPEC-0065 (Fixture `todo-service`, Qwen3.8 für die Arbeitsrollen,
`claude-cli` als Reviewer, Supervisor im Dialog). Hier geht es um das, was der Supervisor an S2
sieht, wann S2 überhaupt kommt, und wie der Report die Kosten ausweist.

Befunde:

1. **S2 ohne Review-Befunde.** Lehnt das Review ab, nennen die S2-Fakten nur `Review: fail`. Der
   Supervisor musste den Reviewer fünfmal von Hand aufrufen (`facade.run_role`), um die Gründe zu
   sehen. Mehrmals war das Review berechtigt (Neustart-Fehler mit Fälligkeit, Unicode-Tags,
   Umfang über die Task hinaus), einmal nicht (Konflikt mit einem Test aus SPEC-0002).
2. **„Nichts zu ändern“ unmöglich.** Die Implementer-Ausgabe verlangt mindestens eine Datei. Ist
   der Stand schon richtig (nach einem S2-Retry, wenn das Review nur noch einmal prüfen soll),
   scheitert der Versuch mit `files: [] should be non-empty`.
3. **Frühe Eskalation.** `attempts` zählt alle Stufen einer Task gemeinsam; nach einer
   Review-Ablehnung und einem weiteren Implementer-Versuch kam S2 bereits.
4. **Report unterschätzt Claude.** `sdd pipeline report` zählt Cache-Tokens nicht. Beim Reviewer
   über `claude-cli` stehen 8 Input-Tokens im Report, in `token_usage` aber 83 017 Cache-Read und
   39 067 Cache-Write; der angezeigte „Claude-Anteil 5 %“ ist stark untertrieben.

## 2. Zielsetzung

**Primärziel:** Der Supervisor entscheidet an S2 ohne Nebenkanal, S2 kommt erst, wenn eine Stufe
wirklich festhängt, und der Report zeigt die tatsächlichen Token-Kosten.

**Erfolgskriterien (messbar):**
- [ ] Jede S2-Anfrage nach einer Review-Ablehnung enthält die Befunde dieses Reviews.
- [ ] Nach einer einzelnen Review-Ablehnung eskaliert eine Task nicht an S2.
- [ ] `sdd pipeline report` des SPEC-0003-Laufs weist Cache-Tokens aus; der Claude-Anteil enthält sie.

**Nicht-Ziele (explizit):**
- Kein neuer S2-Command; `retry_with_hint` mit `stage` (HF-0013) bleibt das Mittel.
- Keine Preise oder Kosten in Euro; nur Token-Mengen.
- Keine Änderung am Rollenkontext (SPEC-0065).

## 3. Architektur & Design Patterns

| Pattern | Rolle in dieser Spec |
|---------|----------------------|
| **Adapter** | Übersetzt die Ausgabe des Reviewers (CON-0200 `$defs/reviewer`) in das feste Schema `facts.review` aus CON-0202. Gab es vor der Eskalation kein Review, entsteht kein Feld. |
| **Decorator** | Die bestehende Usage-Erfassung (SPEC-0063) liefert Cache-Read und Cache-Write anbieterneutral mit; der Report liest sie auf demselben Weg wie Input- und Output-Tokens. |

## 4. Funktionale Anforderungen

- **FR-01:** **Review-Befunde an S2.** Scheitert eine Task zuletzt am Review, enthält die
  S2-Anfrage `facts.review` mit `verdict` und `findings` des letzten Reviews (je Befund
  `category`, `file`, `line`, `reason`). Ohne vorheriges Review fehlt das Feld.
- **FR-02:** **Keine Änderung nötig.** Die Implementer-Ausgabe erlaubt `files: []`. Dann wird
  nichts geschrieben (der Schreibschritt ist ein No-op, die PathPolicy wird nicht befragt), das
  GREEN-Gate prüft den bestehenden Stand, und der Versuch zählt als Implementierungsversuch. Bei
  grünem Stand folgt das Review wie sonst; es bekommt den Diff der Task gegen ihren Ausgangsstand,
  der auch leer sein kann.
- **FR-03:** **Versuche je Stufe.** Jede Task zählt Versuche getrennt nach Stufe (`test`,
  `implementation`, `review`). Eine Task eskaliert an S2, sobald eine Stufe `max_attempts`
  erreicht. Eine Review-Ablehnung beginnt eine neue Runde und setzt den Zähler `implementation`
  auf 0; `review` begrenzt die Zahl der Runden. `retry_with_hint`, `reassign` und `reopen`
  setzen alle Stufenzähler der Task auf 0. `state.json` führt die
  Zähler je Task in `stage_attempts`; `attempts` behält seine Bedeutung als Zahl der Versuche
  der aktuellen Stufe, die S2 auslöst.
- **FR-04:** **Cache-Tokens im Report.** `sdd pipeline report` zeigt je Rolle zusätzlich
  Cache-Read und Cache-Write. Der Claude-Anteil rechnet für alle Rollen Input, Output, Cache-Read
  und Cache-Write ein. Fehlen Werte (`usage: None`), zählen sie als 0 und der Report nennt die
  Rollen ohne Usage.

## 5. Nicht-funktionale Anforderungen

| Kategorie | Anforderung |
|-----------|-------------|
| Kompatibilität | Nur zusätzliche Felder in `pending-decision.json` und `state.json`; bestehende Runs lassen sich mit `--resume` fortsetzen (fehlende Stufenzähler gelten als 0) |
| Datenschutz | `facts.review` enthält nur Befunde des Reviewers, keine Prompts und keine Holdout-Inhalte |
| Umfang | `facts.review` höchstens 20 Befunde, je Begründung höchstens 600 Zeichen |

## 6. Akzeptanzkriterien (Gherkin)

```gherkin
Feature: S2-Fakten, Versuche je Stufe und Token-Report

  Scenario: Review-Befunde an S2
    Given eine Task scheitert wiederholt am Review
    When die Pipeline an S2 eskaliert
    Then nennt facts.review das Urteil und die Befunde des letzten Reviews

  Scenario: Eine Review-Ablehnung führt nicht zu S2
    Given max_attempts ist 3 und das Review lehnt einmal ab
    When der Implementer danach grün liefert und das Review zustimmt
    Then gibt es keine S2-Anfrage
```

## 7. Edge Cases & Fehlerfälle

- Eskalation ohne vorheriges Review: `facts.review` fehlt.
- Reviewer-Ausgabe ungültig: `facts.review` fehlt, `errors` nennt den Grund wie bisher.
- Run aus der Zeit vor dieser Spec mit `--resume`: Stufenzähler starten bei 0.

## 8. Contracts (was wird garantiert)

| Contract-ID | Typ | Was wird garantiert? |
|-------------|-----|----------------------|
| CON-0200 | data | Implementer-Ausgabe erlaubt `files: []` |
| CON-0202 | data | `facts.review` an S2; Stufenzähler je Task in `state.json` |
| CON-0205 | behavior | `max_attempts` gilt je Stufe |
| CON-0232 | behavior | Szenarien zu S2-Fakten, Stufenzählern, leerer Implementer-Ausgabe und Report |

## 9. Tests (wie wird verifiziert)

| Test-ID | Level | Was prüft der Test? |
|---------|-------|---------------------|
| (nach Review) | unit / acceptance | Schemaerweiterungen, Szenarien aus CON-0232 |

## 10. Offene Fragen

- Keine. Entscheidungen aus dem Review von SPEC-0065 (2026-10-04): eigene Spec für S2, Versuche
  und Report; Versuche je Stufe; Patterns Adapter und Decorator.

## 11. Änderungshistorie

| Datum      | Version | Autor         | Änderung            |
|------------|---------|---------------|---------------------|
| 2026-10-04 | 0.1.0   | Boris, Claude | Initiale Erstellung, ausgegliedert aus SPEC-0065 |
| 2026-10-04 | 0.1.1   | Boris, Claude | SOLID-Warnungen: attempts behält seine Bedeutung, Reviewer-Contract benannt, Verhalten bei files: [] je Konsument |
| 2026-10-04 | 0.1.2   | Claude        | FR-03 präzisiert: Review-Ablehnung beginnt eine neue Runde (setzt implementation auf 0); reassign/reopen setzen wie retry_with_hint zurück |
