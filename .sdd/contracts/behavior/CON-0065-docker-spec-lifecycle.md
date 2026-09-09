---
id: CON-0065
title: "docker-spec-lifecycle"
type: behavior
format: gherkin
spec: SPEC-0021
version: 0.3.0
status: draft
artifact: "contracts/behavior/docker-spec-lifecycle.feature"
tests: [TST-0074]
---

# Contract: docker-spec-lifecycle

> **Spec:** SPEC-0021 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Beschreibt das beobachtbare Verhalten von `sdd start`, `sdd dev exec` und
`sdd dev close` beim Verwalten isolierter Docker-Entwicklungscontainer pro Spec.

Diese Befehle sind explizit **von `sdd start` getrennt** (SPEC-0019/CON-0060):
- `sdd start SPEC-XXXX` → TDD-Statusübergang: `draft → in-progress` (SPEC-0019)
- `sdd start SPEC-XXXX` → Docker-Container + Git-Branch für isolierte Entwicklung

> **Noch offen:** G-05 und G-06 sowie die zugehoerigen Szenarien beschreiben
> `sdd dev exec` und `sdd dev close` — ebenfalls mit SPEC-0044 entfernt. Anders
> als bei `start` gibt es dafuer keinen Nachfolgebefehl: der Container-Lebenszyklus
> laeuft intern ueber `sdd start`, `sdd finalize` und `sdd orchestrate`. Ob diese
> Garantien auf die internen Aufrufe umgeschrieben oder gestrichen werden,
> ist nicht entschieden und bleibt hier unangetastet.
>
> **v0.3.0 (2026-09-09):** Der Contract war durchgehend fuer `sdd start`
> geschrieben — ein Befehl, den SPEC-0044 entfernt hat. Das Verhalten liegt
> seither bei `sdd start`, das die Garantien geerbt hat, ohne dass das je
> entschieden wurde. Der Wortlaut ist entsprechend nachgezogen, und G-01 zweigt
> nicht mehr fest von `main` ab (siehe Begruendung dort).

**Branch-Ownership:** `sdd start` erstellt den Branch für interaktive
Entwicklung. Der Orchestrator (CON-0012) verwaltet eigene Branches im autonomen
Pfad. Beide sind orthogonal — `sdd start` ist ausschließlich für den
interaktiven Level-2/3-Entwicklungspfad.

## Garantien

- **G-01:** `sdd start SPEC-XXXX` erzeugt Branch `dev/SPEC-XXXX` **aus dem
  aktuellen HEAD** UND startet Container `sdd-dev-spec-xxxx` atomar — bei Fehler
  in einem Schritt wird der andere zurückgerollt.

  **Warum nicht mehr aus `main` (v0.3.0):** Baut eine Spec auf einer noch nicht
  gemergten Vorgängerin auf, entstand der Entwicklungszweig ohne deren Arbeit.
  Zweite Folge: `sdd start` schreibt vor dem Branchwechsel den Spec-Status und
  das `audit.log`; wer nicht auf `main` stand, scheiterte am Wechsel auf einen
  fremden Baum — an Änderungen, die der Befehl selbst erzeugt hatte.

  `docker.base_branch` setzt den festen Abzweigpunkt wieder, wo er richtig ist.
- **G-02:** Container startet mit Volume-Mount und Env-Variablen gemäß
  `.sdd/config.yaml` (`docker.mount`, `docker.env`). Defaults:
  `$(pwd):/workspace`, `SPEC_ID`, `GIT_BRANCH`.
- **G-03:** `sdd start` mit bereits aktivem Container gibt eine Warnung aus
  und startet keinen zweiten Container (Idempotenz).
- **G-04:** Ein gestoppter (nicht entfernter) Container wird durch `sdd start`
  wieder gestartet — kein neuer Container wird erstellt.
- **G-05:** `sdd dev exec SPEC-XXXX <befehl>` führt den Befehl via `docker exec`
  im laufenden Container aus und gibt Exit-Code und Output 1:1 zurück.
- **G-06:** `sdd dev close SPEC-XXXX` stoppt und entfernt den Container.
  Mit `--delete-branch` wird auch der Git-Branch `dev/SPEC-XXXX` gelöscht.

## Invarianten

- **INV-01:** Container-Name ist deterministisch: `sdd-dev-{spec-id-lowercase}`
  → `sdd-dev-spec-0021`.
- **INV-02:** Branch-Name ist deterministisch: `dev/{SPEC-ID}` → `dev/SPEC-0021`.
- **INV-03:** Der main-Branch wird durch `sdd start`, `sdd dev exec` oder
  `sdd dev close` nie verändert.
- **INV-04:** `sdd start` und `sdd start` (SPEC-0019) sind unabhängige Befehle
  mit getrennten Zuständen — ein `sdd start` setzt den Spec-Status nicht auf
  `in-progress`.

## Szenarien

```gherkin
Feature: Docker Container Lifecycle für Spec-Entwicklung

  Background:
    Given ein SDD-Projekt mit gültiger .sdd/config.yaml
    And docker ist installiert und läuft
    And kein Container "sdd-dev-spec-0021" existiert
    And kein Branch "dev/SPEC-0021" existiert

  Scenario: Normaler Start – Container und Branch werden erzeugt
    Given SPEC-0021 existiert
    When der Nutzer "sdd start SPEC-0021" ausführt
    Then wird Branch "dev/SPEC-0021" aus dem aktuellen HEAD erzeugt
    And Container "sdd-dev-spec-0021" wird gestartet
    And Container hat Volume-Mount und Env-Variablen gemäß config.yaml
    And Spec-Status bleibt unverändert (kein in-progress-Übergang)
    And der Exit-Code ist 0

  Scenario: Idempotenz – Container läuft bereits
    Given Container "sdd-dev-spec-0021" ist aktiv (status: running)
    When der Nutzer "sdd start SPEC-0021" erneut ausführt
    Then wird eine Warnung ausgegeben: "Container sdd-dev-spec-0021 läuft bereits"
    And kein zweiter Container wird gestartet
    And der Exit-Code ist 0

  Scenario: Gestoppter Container wird wieder gestartet
    Given Container "sdd-dev-spec-0021" existiert aber ist gestoppt
    And Branch "dev/SPEC-0021" existiert bereits
    When der Nutzer "sdd start SPEC-0021" ausführt
    Then wird Container "sdd-dev-spec-0021" gestartet (docker start, kein docker run)
    And kein neuer Container wird erstellt
    And der Exit-Code ist 0

  Scenario: Atomarer Rollback – Docker-Fehler nach Branch-Erstellung
    Given docker run schlägt fehl (Image nicht gefunden)
    When der Nutzer "sdd start SPEC-0021" ausführt
    Then wird Branch "dev/SPEC-0021" wieder gelöscht (Rollback)
    And eine Fehlermeldung beschreibt den Docker-Fehler
    And der Exit-Code ist ungleich 0

  Scenario: sdd dev exec – Befehl im Container ausführen
    Given Container "sdd-dev-spec-0021" ist aktiv
    When der Nutzer "sdd dev exec SPEC-0021 pytest tests/ -x" ausführt
    Then wird "docker exec sdd-dev-spec-0021 pytest tests/ -x" ausgeführt
    And Output und Exit-Code werden 1:1 weitergeleitet

  Scenario: sdd dev exec – Container nicht aktiv
    Given Container "sdd-dev-spec-0021" ist nicht aktiv
    When der Nutzer "sdd dev exec SPEC-0021 pytest tests/" ausführt
    Then erscheint Fehler: "Container sdd-dev-spec-0021 läuft nicht. Führe 'sdd start SPEC-0021' aus."
    And der Exit-Code ist ungleich 0

  Scenario: sdd dev close – Container stoppen und entfernen
    Given Container "sdd-dev-spec-0021" ist aktiv
    When der Nutzer "sdd dev close SPEC-0021" ausführt
    Then wird "docker stop sdd-dev-spec-0021" ausgeführt
    And wird "docker rm sdd-dev-spec-0021" ausgeführt
    And Branch "dev/SPEC-0021" bleibt erhalten
    And der Exit-Code ist 0

  Scenario: sdd dev close --delete-branch – Container und Branch entfernen
    Given Container "sdd-dev-spec-0021" ist aktiv
    And Branch "dev/SPEC-0021" ist nicht ausgecheckt
    When der Nutzer "sdd dev close SPEC-0021 --delete-branch" ausführt
    Then wird Container gestoppt und entfernt
    And Branch "dev/SPEC-0021" wird gelöscht
    And der Exit-Code ist 0
```

## Begriffe

| Begriff | Definition |
|---|---|
| atomar | Beide Operationen (Docker + Git) gelingen oder keine wird dauerhaft angewendet |
| Idempotenz | Mehrfaches Ausführen desselben Befehls führt zum selben Ergebnis ohne Fehler |
| sdd-dev-spec-0021 | Container-Name: `sdd-dev-{spec-id-lowercase}` |
| dev/SPEC-0021 | Branch-Name: `dev/{SPEC-ID}` (getrennt vom Orchestrator-Branch `spec/SPEC-XXXX`) |
