---
id: CON-0065
title: "docker-spec-lifecycle"
type: behavior
format: gherkin
spec: SPEC-0021
version: 0.4.0
status: draft
tests: [TST-0074]
---

# Contract: docker-spec-lifecycle

> **Spec:** SPEC-0021 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Beschreibt das beobachtbare Verhalten des Dev-Containers einer Spec: `sdd start`
legt Branch und Container an, die Finalisierung räumt ihn auf. Das gilt für
`sdd finalize` und für jeden Pfad, der die Finalisierung nutzt.

Eigene Container-Befehle (`sdd dev start|exec|close`) gibt es seit SPEC-0044
nicht mehr. `sdd start` erledigt Statusübergang (SPEC-0019), Branch und
Container in einem Aufruf; `--no-container` lässt den Container weg.

> **v0.4.0 (2026-09-11):** Zwei Probleme behoben (#121).
>
> G-05/G-06 beschrieben `sdd dev exec` und `sdd dev close --delete-branch`,
> Befehle, die SPEC-0044 entfernt hat. In v0.3.0 standen sie als „noch offen".
> Jetzt steht hier, was der Code tut: G-05 entfällt, weil Befehle im Container
> direkt über die Runtime laufen, und G-06 beschreibt das Aufräumen durch die
> Finalisierung. `DevContainerManager.exec_cmd()` und `close(delete_branch=True)`
> erreichten nur noch Tests und sind entfernt.
>
> Dazu kommt ein Widerspruch aus v0.3.0 (#78). Die mechanische Umbenennung
> `sdd dev start` → `sdd start` hatte dort, wo beide Befehle gegeneinander
> abgegrenzt waren, zweimal denselben Namen hinterlassen: INV-04 hieß
> „`sdd start` und `sdd start` sind unabhängige Befehle", und ein Szenario
> behauptete „kein in-progress-Übergang". Laut SPEC-0019 setzt `sdd start` den
> Status aber auf `in-progress`.
>
> Das `artifact`-Feld zeigte auf eine nie angelegte `.feature`-Datei und ist
> entfernt. Die Szenarien stehen unten.

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
- **G-05:** *entfallen (v0.4.0).* Befehle im laufenden Container werden direkt
  über die Runtime ausgeführt: `docker exec sdd-dev-<spec-id-klein> <befehl>`
  bzw. `podman exec …`. So beschreiben es die Skills (`/sdd-implement`).
- **G-06:** Die Finalisierung entfernt den Container, **nachdem die Tests darin
  grün waren**. Nach roten Tests oder einem gescheiterten Build (CON-0012,
  Schritt 5) bleibt er stehen, damit man hineinschauen kann. Ein erneutes
  `sdd start` findet ihn dann vor (G-03). Der Branch `dev/SPEC-XXXX` bleibt in
  jedem Fall erhalten. Mit `docker.compose_file` fasst die Finalisierung den
  Stack nicht an.

## Invarianten

- **INV-01:** Container-Name ist deterministisch: `sdd-dev-{spec-id-lowercase}`
  → `sdd-dev-spec-0021`.
- **INV-02:** Branch-Name ist deterministisch: `dev/{SPEC-ID}` → `dev/SPEC-0021`.
- **INV-03:** Der main-Branch wird durch `sdd start` und die Finalisierung nie
  verändert.
- **INV-04:** `sdd start` ist **ein** Befehl mit zwei Wirkungen: den
  Statusübergang `approved → in-progress` (SPEC-0019; eine Spec, die schon
  `in-progress` ist, ist kein Fehler) und Branch + Container (G-01).
  `--no-container` lässt den zweiten Teil weg.

## Szenarien

```gherkin
Feature: Docker Container Lifecycle für Spec-Entwicklung

  Background:
    Given ein SDD-Projekt mit gültiger .sdd/config.yaml
    And docker ist installiert und läuft
    And kein Container "sdd-dev-spec-0021" existiert
    And kein Branch "dev/SPEC-0021" existiert

  Scenario: Normaler Start – Status, Container und Branch
    Given SPEC-0021 ist approved
    When der Nutzer "sdd start SPEC-0021" ausführt
    Then wechselt der Spec-Status von approved auf in-progress
    And wird Branch "dev/SPEC-0021" aus dem aktuellen HEAD erzeugt
    And Container "sdd-dev-spec-0021" wird gestartet
    And Container hat Volume-Mount und Env-Variablen gemäß config.yaml
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

  Scenario: Finalisierung nach grünen Tests räumt den Container auf
    Given Container "sdd-dev-spec-0021" ist aktiv
    And die Tests im Container sind grün
    When "sdd finalize SPEC-0021" ausgeführt wird
    Then wird Container "sdd-dev-spec-0021" gestoppt und entfernt
    And Branch "dev/SPEC-0021" bleibt erhalten

  Scenario: Finalisierung nach roten Tests lässt den Container stehen
    Given Container "sdd-dev-spec-0021" ist aktiv
    And die Tests im Container schlagen fehl
    When "sdd finalize SPEC-0021" ausgeführt wird
    Then läuft Container "sdd-dev-spec-0021" weiter
    And die Finalisierung meldet den Fehlschlag

  Scenario: Gescheiterter Build lässt den Container ebenfalls stehen
    Given Container "sdd-dev-spec-0021" ist aktiv
    And orchestrator.build_command ist gesetzt und schlägt fehl
    When "sdd finalize SPEC-0021" ausgeführt wird
    Then laufen keine Tests
    And läuft Container "sdd-dev-spec-0021" weiter
```

## Begriffe

| Begriff | Definition |
|---|---|
| atomar | Beide Operationen (Docker + Git) gelingen oder keine wird dauerhaft angewendet |
| Idempotenz | Mehrfaches Ausführen desselben Befehls führt zum selben Ergebnis ohne Fehler |
| sdd-dev-spec-0021 | Container-Name: `sdd-dev-{spec-id-lowercase}` |
| dev/SPEC-0021 | Branch-Name: `dev/{SPEC-ID}` (getrennt vom Orchestrator-Branch `spec/SPEC-XXXX`) |
| Finalisierung | `SpecFinalizer.run()` — gemeinsam für `sdd finalize`, `/sdd-implement`, `sdd orchestrate`, `sdd distribute` |
