---
id: CON-0230
title: "S3-Abnahme mit Task-Fakten"
type: behavior
format: gherkin
spec: SPEC-0064
version: 0.1.0
status: draft
artifact: ".sdd/contracts/behavior/s3-abnahme-mit-task-fakten.feature"
tests: ["TST-0259"]
---

# Contract: S3-Abnahme mit Task-Fakten

> **Spec:** SPEC-0064 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Legt fest, wie die Pipeline die Tasks eines Runs festhält und an der Abnahme (S3) dem Supervisor
vorlegt (SPEC-0064 FR-01 bis FR-04, FR-06, FR-07). Die Datenformen stehen in CON-0202
(`$defs/task_snapshot`, `$defs/s3_task`, `$defs/s3_fr`).

## Garantien

Die Szenarien im Artifact (`.sdd/contracts/behavior/s3-abnahme-mit-task-fakten.feature`) sind
**ausführbare Spezifikation**.

## Invarianten

- **INV-01:** Nach jeder S1-Freigabe steht `tasks.json` im Run-Verzeichnis und enthält genau die
  freigegebenen Tasks; nach `redecompose` und erneuter Freigabe den neuen Stand.
- **INV-02:** Jede S3-Anfrage erfüllt CON-0202: `facts.tasks` hat je Task aus `state.json` einen
  Eintrag in derselben Reihenfolge; `facts.frs[].tasks` leitet sich allein aus `facts.tasks`
  (`fr_ids`) ab.
- **INV-03:** Fehlt `tasks.json` oder fehlt darin eine Task aus `state.json`, entsteht keine
  S3-Anfrage; der Run hält (`status: halted`) mit einem Grund, der `tasks.json` nennt.
- **INV-04:** Die Fakten ändern nichts an `reopen`: jede Task-ID aus `facts.tasks` ist für `reopen`
  gültig, andere IDs werden wie bisher abgelehnt.
- **INV-05:** Die Anleitung der Rolle `supervisor` und `/sdd-supervise` nennen `facts.tasks` und
  `facts.frs[].tasks` als Quelle der `task_ids`. Die S3-Golden-Cases enthalten beide Felder, und
  ihre Beschreibungen verweisen für die Zuordnung auf die Fakten, nicht auf die Historie.
