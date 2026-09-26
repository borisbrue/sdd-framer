---
id: CON-0213
title: "Session-Arbeitsrollen, Routing, Task-Typen und Gates pro Task"
type: behavior
format: gherkin
spec: SPEC-0061
version: 0.2.0
status: approved
artifact: ".sdd/contracts/behavior/session-arbeitsrollen-routing-task-typen-und-gates-pro-task.feature"
tests: ["TST-0242"]
---

# Contract: Session-Arbeitsrollen, Routing, Task-Typen und Gates pro Task

> **Spec:** SPEC-0061 · **Typ:** Verhalten (Gherkin) · **Status:** approved

## Zweck

Legt fest, wie Arbeitsrollen im Modus `session` arbeiten, wie `sdd pipeline done` einen Auftrag
bestätigt, welcher Rollenvertrag für alle Modi gilt, wie die Belegung nach Komplexität aufgelöst
wird, wie Task-Typen und Gates pro Task wirken und was `--task` tut (SPEC-0061 FR-01 bis FR-07).

## Garantien

Die Szenarien im Artifact (`.sdd/contracts/behavior/session-arbeitsrollen-routing-task-typen-und-gates-pro-task.feature`) sind **ausführbare Spezifikation**. Jedes Szenario MUSS durch
einen automatisierten Test (pytest) abgedeckt sein; LLM-Rollen laufen gegen den Fake-LLM-Server,
Session-Rollen werden im Test durch Dateischreiben und `sdd pipeline done` gespielt.

## Invarianten

- **INV-01 (Rollenvertrag):** Für jeden Modus gilt nach dem Ergebnis einer Arbeitsrolle
  dasselbe: Änderungen nur in den Pfaden der PathPolicy (CON-0204), danach dieselben Gates,
  dieselbe Versuchszählung und bei `max_attempts` S2. Ein Pfadverstoß ist `write_rejected` und
  macht den Versuch zu `gate_failed`. LLM-Ausgaben mit Verstoß werden nicht geschrieben; Dateien
  einer Session stellt die Pipeline nicht selbst zurück, der nächste Auftrag nennt sie.
- **INV-02:** Geänderte Dateien einer Session ermittelt die Pipeline über einen Schnappschuss der
  Prüfsummen zum Zeitpunkt des Auftrags (ohne `.sdd/`, `.git/`, `node_modules/`).
- **INV-03:** `sdd pipeline done RUN [--json]`: Exit 2 ohne offenen Auftrag oder bei ungültiger
  Ausgabe (Auftrag bleibt offen); sonst setzt der Run fort und endet mit den Exit-Codes aus CON-0205
  (0/1/3).
- **INV-04:** Belegung eines Aufrufs, in dieser Reihenfolge: `reassign` des Supervisors →
  `by_complexity[komplexität]` → `profile` bzw. eigene Parameter der Rolle → `legacy_component` →
  `claude-cli`. Ein unbekanntes Profil verhindert den Start (Exit 2).
- **INV-05:** Task-Typen: `code` mit RED und GREEN, `test` ohne RED-Zwang, `config`/`doc` ohne
  test_author; alle mit Reviewer. Für `config`/`doc` blockiert das Test-Gate nur neue Fehler.
- **INV-06:** Gates aus `pipeline.task_gates` laufen nach jedem Implementer-Versuch; `n/a` blockiert
  nie. Ein blockierendes Gate setzt die Dateien eines LLM-Implementers zurück.
- **INV-07:** `--task ID` braucht eine gespeicherte Zerlegung, bearbeitet nur diesen Task und endet
  ohne S1, S3 und Abschluss; kombiniert mit `--auto` oder `--resume` Exit 2.
- **INV-08 (Abgrenzung):** Die Pipeline führt Task-Zustände in `state.json` (CON-0202) und nutzt
  weder `TaskLifecycle` (CON-0124) noch die Regeln des Skills `/sdd-implement` (CON-0061); deren
  Test-Pflicht für `passed` gilt für die Pipeline nicht. `--task` liest die Task-IDs aus
  `.sdd/tasks/<SPEC>.json`, egal ob `sdd decompose` oder die Pipeline die Zerlegung gespeichert hat.
