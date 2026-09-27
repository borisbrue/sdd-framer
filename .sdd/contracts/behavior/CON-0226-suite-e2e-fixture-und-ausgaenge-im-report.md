---
id: CON-0226
title: "Suite e2e, Fixture und Ausgänge im Report"
type: behavior
format: gherkin
spec: SPEC-0063
version: 0.1.0
status: draft
artifact: ".sdd/contracts/behavior/suite-e2e-fixture-und-ausgaenge-im-report.feature"
tests: ["TST-0255"]
---

# Contract: Suite e2e, Fixture und Ausgänge im Report

> **Spec:** SPEC-0063 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Legt die Suite-Art `e2e`, ihre Isolation und Messung, das Fixture `todo-service` und die Ausweisung von Ausgängen im Report fest (SPEC-0063 FR-02 bis FR-07).

## Garantien

Die Szenarien im Artifact (`.sdd/contracts/behavior/suite-e2e-fixture-und-ausgaenge-im-report.feature`) sind **ausführbare Spezifikation**; Rollen laufen gegen den Fake-LLM-Server.

## Invarianten

- **INV-01:** `kind: e2e` verlangt `fixture` (Pfad relativ zum Projekt mit `project/`, `hidden/`, `reference/`), `specs` (mindestens eine Spec-ID, Reihenfolge der Runs) und `test_command` (mit `{python}`, `{junit}`); optional `isolation` (Default `dir`), `weights`, `timeout_seconds`. Das Schema CON-0221 wird additiv erweitert.
- **INV-02:** Isolation `dir`: Das Arbeitsverzeichnis ist eine Kopie von `project/` als eigenes Git-Repository mit Start-Commit; `hidden/` und `reference/` liegen nicht darin. Eine unbekannte Isolationsart ergibt Exit 2 vor dem ersten Lauf. Projekt-Worktree und `.sdd/` des Projekts bleiben byte-gleich.
- **INV-03:** Die Belegung wird als abgeleitete Profile (`profil@variante`) und `llm.roles.<rolle>.profile` in die `config.yaml` der Kopie geschrieben; `supervisor` läuft `inline`. Je Spec startet `sdd pipeline run SPEC --auto --steps ""` als Prozess mit `--max-tokens`/`--max-claude-tokens` aus dem Budget der Matrix. Hält ein Run mit Grund `budget`, endet der Lauf mit Ausgang `halted: budget`; sonst folgt die nächste Spec.
- **INV-04:** Erst nach dem letzten Run wird `hidden/` in das Arbeitsverzeichnis kopiert. `frs_total` und `frs_met` ergeben sich aus den FR-Markern der Testnamen (`fr01` → FR-01); eine FR ist erfüllt, wenn alle ihre Tests grün sind. `Q_req = frs_met / frs_total`; `Q_arch`/`Q_code` aus `sdd quality measure --diff <start>` oder `null`, `Q` renormalisiert nach den Gewichten.
- **INV-05:** Tokens je Rolle kommen aus `token_usage` des Arbeitsverzeichnisses (Komponente `role:<rolle>`); Zeilen ohne gemeldete Usage markieren den Record als `estimated`.
- **INV-06:** Fixture `todo-service`: drei Specs mit 3, 6 und 10 FRs, jede `approved` mit Gate-Phase `execute-unlocked`; die Referenzlösung erfüllt alle FRs der versteckten Tests, der Startstand keine. `sdd bench init` kopiert Fixture und `bench/suites/e2e.yaml`.
- **INV-07:** Der Report nennt je Eintrag die Zahl der Läufe je Ausgang (`completed`, `halted: budget`, `error`); die Formeln aus CON-0224 bleiben unverändert.
