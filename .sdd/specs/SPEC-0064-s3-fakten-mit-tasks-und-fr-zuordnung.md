---
id: SPEC-0064
title: "S3-Fakten mit Tasks und FR-Zuordnung"
type: feature
status: implemented
owner: "Boris"
created: 2026-09-28
updated: 2026-09-28
version: 0.2.1
priority: medium
tags: [pipeline, supervisor, s3]
depends_on: [SPEC-0053, SPEC-0055, SPEC-0061]
contracts:
- CON-0202
- CON-0230
tests:
- TST-0231
- TST-0259
fr_test_map:
  FR-01: [TST-0259]
  FR-02: [TST-0231, TST-0259]
  FR-03: [TST-0231, TST-0259]
  FR-04: [TST-0259]
  FR-05: [TST-0231]
  FR-06: [TST-0259]
  FR-07: [TST-0259]
---

# S3-Fakten mit Tasks und FR-Zuordnung

> **Status:** draft · **Owner:** Boris · **Version:** 0.2.1

## 1. Kontext & Motivation

An der Abnahme (S3) entscheidet der Supervisor je FR über `accept_frs` oder schickt einzelne
Tasks mit `reopen` (`task_ids`, `hint`, SPEC-0061 FR-09) zurück. Die S3-Anfrage enthält heute nur
`frs` (Status und Testdateien je FR), `gate_results`, `tokens` und mit `--auto` `holdout`. Welche
Tasks es gibt, welche FR sie abdecken und in welchem Zustand sie sind, steht nicht darin.

Folgen aus den Dogfooding-Läufen (SPEC-0055):
- Ein Supervisor kann `reopen` nur ausfüllen, wenn er die Task-IDs aus `history` oder aus
  `.sdd/tasks/<SPEC>.json` errät. Der Golden Case SUP-005 schreibt das offen hin („Laut Historie
  gehört FR-03 zu T03“).
- Die Anleitung `/sdd-supervise` behauptet, `facts` enthalte die Tasks. Für S3 stimmt das nicht.
- `pending-decision.json` bietet an S3 `reopen` an, CON-0202 kennt `reopen` in `allowed_commands`
  aber nicht. Jede Schemaprüfung einer S3-Anfrage scheitert (bestehender Contract-Fehler).

## 2. Zielsetzung

**Primärziel:** Die S3-Anfrage enthält alles, was für `reopen` nötig ist: die Tasks des Runs mit
ID, Titel, FR-Zuordnung, Testdatei und Zustand, und je FR die zugehörigen Task-IDs.

**Erfolgskriterien (messbar):**
- [ ] Jede S3-Anfrage erfüllt CON-0202 und enthält `facts.tasks` mit allen Tasks des Runs.
- [ ] Jede FR in `facts.frs` nennt ihre Task-IDs; eine FR ohne Task hat eine leere Liste.
- [ ] Die S3-Golden-Cases der Rolle `supervisor` nennen Task-Zuordnungen nur noch in den Fakten;
      `sdd role eval supervisor` bleibt mindestens auf dem bisherigen Stand.

**Nicht-Ziele (explizit):**
- Keine neuen Supervisor-Commands, keine Änderung an `reopen` und an seiner Prüfung (die
  vorhandene Prüfung, dass jede Task-ID zum Run gehört, bleibt).
- S1 und S2 bleiben unverändert (S1 trägt die Tasks bereits, S2 betrifft genau einen Task).
- Keine automatische Auswahl der Tasks für `reopen` durch die Pipeline.
- Keine Holdout-Fälle für die Rolle `supervisor` in dieser Spec.

## 3. Architektur & Design Patterns

Die S3-Fakten entstehen in einem eigenen Modul der Pipeline aus zwei Schnappschüssen des Runs.

| Pattern | Rolle in dieser Spec |
|---------|----------------------|
| **Memento** | Bei der S1-Freigabe schreibt die Pipeline die freigegebenen Tasks als `approved-tasks.json` ins Run-Verzeichnis (bei `redecompose` neu). S3 liest nur diesen Schnappschuss und `state.json` und erzeugt keinen eigenen Zustand; nach `reopen` zeigen `state` und `attempts` automatisch den neuen Stand. |
| **Adapter** | Bildet Task-Schnappschuss (Aufgabenbeschreibung) und `state.json` (Laufzeitstand) auf das eine Format `s3_task` aus CON-0202 ab. |
| **Proxy (Allowlist)** | Eine feste Feldliste (`id`, `title`, `fr_ids`, `test_file`, `state`, `attempts`) entscheidet, was in die Anfrage gelangt; weitere Felder der Task (etwa Beschreibung, `allowed_paths`) bleiben draußen. Erweiterungen nur über diese Liste. |
| **Builder** | Setzt die S3-Fakten in fester Reihenfolge zusammen: `tasks`, daraus `frs[].tasks`, dann `gate_results` und optional `holdout`. Beide Sichten hängen an derselben Task-Liste. |

**Alternativen:** Die Tasks bei S3 aus `.sdd/tasks/<SPEC>.json` zu lesen wurde verworfen: die
Datei gehört dem Projekt, kann sich außerhalb des Runs ändern und bräuchte eine Sonderbedeutung
für „unbekannt“ (SOLID-L). Ein eigener Snapshot gehört dem Run; fehlt er, ist der Run beschädigt.

## 4. Funktionale Anforderungen

- **FR-01:** **Task-Schnappschuss.** Bei der S1-Freigabe (`approve`) schreibt die Pipeline die
  freigegebenen Tasks als `approved-tasks.json` ins Run-Verzeichnis; eine spätere Freigabe nach
  `redecompose` ersetzt ihn. Die Datei wird nur von der Pipeline geschrieben. Der Name
  unterscheidet sie von `tasks.json` des `TaskRepository` (Kanban, CON-0123) im selben
  Verzeichnis.
- **FR-02:** **`facts.tasks` an S3.** Die S3-Anfrage enthält je Task aus `state.json` (in dieser
  Reihenfolge) genau die Felder `id`, `title`, `fr_ids`, `test_file`, `state` und `attempts`.
  `fr_ids` ist immer eine Liste (ohne FR: `[]`), `test_file` ist ein Pfad oder `null`.
- **FR-03:** **Task-IDs je FR.** Jeder Eintrag in `facts.frs` erhält `tasks`: die IDs der Tasks,
  deren `fr_ids` die FR enthalten, in der Reihenfolge von `facts.tasks`; ohne Task `[]`.
- **FR-04:** **Fehlender Schnappschuss.** Fehlt `approved-tasks.json` oder fehlt darin eine Task aus
  `state.json`, stellt die Pipeline keine S3-Anfrage, sondern hält den Run mit einem Grund, der die
  Datei nennt (`halted`, Exit wie bei anderen Halts).
- **FR-05:** **Contract-Fehler behoben.** CON-0202 nimmt `reopen` in `allowed_commands` auf
  (bestehender Fehler, unabhängig von FR-01 bis FR-04 nachweisbar).
- **FR-06:** **Supervisor-Anleitung.** Rolle `supervisor` und `/sdd-supervise` nennen
  `facts.tasks` und `facts.frs[].tasks` als Quelle der `task_ids` für `reopen`.
- **FR-07:** **Golden Cases.** Die S3-Fälle der Rolle `supervisor` (SUP-004, SUP-005) erhalten
  `facts.tasks` und `facts.frs[].tasks`; ihre Beschreibung verweist auf die Fakten statt auf die
  Historie. Ein neuer Fall prüft `reopen` bei zwei nicht grünen FRs, deren Tasks nur aus den Fakten
  hervorgehen.

## 5. Nicht-funktionale Anforderungen

| Kategorie       | Anforderung                                                            |
|-----------------|------------------------------------------------------------------------|
| Kompatibilität  | Nur zusätzliche Felder und Dateien; bestehende Leser von `pending-decision.json` bleiben gültig |
| Umfang          | Die Anfrage wächst linear mit der Zahl der Tasks (sechs Felder je Task), keine Diffs oder Inhalte |
| Datenschutz     | Keine Holdout-Inhalte oder -Pfade in `facts.tasks` (Allowlist)          |

## 6. Akzeptanzkriterien (Gherkin)

```gherkin
Feature: S3-Fakten mit Tasks

  Scenario: Abnahme nennt Tasks und ihre FRs
    Given ein Run mit drei freigegebenen Tasks, T03 deckt FR-03 ab
    When die Pipeline die Abnahme S3 anfragt
    Then enthält facts.tasks drei Einträge mit id, title, fr_ids, test_file, state und attempts
    And facts.frs nennt für FR-03 die Tasks ["T03"]

  Scenario: reopen mit Task-IDs aus den Fakten
    Given die S3-Anfrage nennt für FR-03 die Tasks ["T03"]
    When der Supervisor reopen mit task_ids ["T03"] entscheidet
    Then ist die Entscheidung gültig und T03 steht wieder auf red

  Scenario: Schnappschuss fehlt
    Given approved-tasks.json fehlt im Run-Verzeichnis
    When die Pipeline die Abnahme erreicht
    Then hält der Run mit einem Grund, der approved-tasks.json nennt
```

## 7. Edge Cases & Fehlerfälle

- FR ohne Task (Zerlegung lückenhaft): `tasks: []`.
- Task ohne `fr_ids` (z. B. `config`, `doc`): erscheint in `facts.tasks` mit `fr_ids: []`.
- `approved-tasks.json` fehlt oder enthält eine Task aus `state.json` nicht: Halt (FR-04), keine
  Teilfakten.
- Nach `reopen` wird S3 erneut angefragt; `state` und `attempts` zeigen den neuen Stand.
- Runs, die vor dieser Spec gestartet wurden und schon hinter S1 stehen, haben kein
  `approved-tasks.json`; sie halten an S3 mit Hinweis (Neustart des Runs nötig).

## 8. Contracts (was wird garantiert)

| Contract-ID | Typ      | Was wird garantiert? |
|-------------|----------|----------------------|
| CON-0202    | data     | `reopen` in `allowed_commands`; `$defs/task_snapshot` für `approved-tasks.json`; an S3 `facts.tasks` (`s3_task`) und `facts.frs[].tasks` |
| CON-0230    | behavior | Schnappschuss bei S1, Aufbau der S3-Fakten, Halt ohne Schnappschuss, `reopen` mit Task-IDs aus den Fakten, Anleitung und Golden Cases |

## 9. Tests (wie wird verifiziert)

| Test-ID  | Level      | Was prüft der Test? |
|----------|------------|---------------------|
| TST-0231 | unit       | CON-0202 (erweitert): Schemafälle für `reopen`, `task_snapshot`, S3-Fakten |
| TST-0259 | acceptance | Szenarien aus CON-0230 mit Fake-Rollen und Fake-Supervisor |

## 10. Offene Fragen

- Keine. Entscheidungen aus dem Review (2026-09-28): Contract-Fehler als eigene FR im selben PR
  (FR-05), Quelle ist ein Task-Schnappschuss des Runs mit Halt bei Fehlen (FR-01, FR-04), minimale
  Felder je Task (FR-02), Patterns Builder, Memento, Proxy, Adapter.

## 11. Änderungshistorie

| Datum      | Version | Autor         | Änderung            |
|------------|---------|---------------|---------------------|
| 2026-09-28 | 0.1.0   | Boris, Claude | Initiale Erstellung |
| 2026-09-28 | 0.2.0   | Boris, Claude | Review: Task-Schnappschuss, Halt statt Null-Semantik, Contract-Fehler als eigene FR, Patterns |
| 2026-09-28 | 0.2.1   | Boris, Claude | contract analyze: Schnappschuss heißt `approved-tasks.json` (Kollision mit Kanban-`tasks.json`), Abgrenzung der Task-Modelle in CON-0230 |
