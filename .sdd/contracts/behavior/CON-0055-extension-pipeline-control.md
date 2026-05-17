---
id: CON-0055
title: "extension-pipeline-control"
type: behavior
format: gherkin
spec: SPEC-0017
version: 0.1.0
status: draft
artifact: "contracts/behavior/extension-pipeline-control.feature"
tests: [TST-0062]
---

# Contract: extension-pipeline-control

> **Spec:** SPEC-0017 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Beschreibt das beobachtbare Verhalten der Execute-, Abort- und Monitoring-
Funktionen für den Orchestrator-Pipeline aus der VS Code Extension heraus.
Dieses Contract erweitert die in CON-0020 (SPEC-0007) definierten
HTTP-Verträge um die VS Code-seitige Bedienlogik.

## Garantien

- **G-01:** `SDD: Execute Current Spec` liest die Spec-ID aus dem YAML-Frontmatter
  des aktiven Editors – kein manuelles Eingeben der ID nötig.
- **G-02:** Kein Execute-Request wird gesendet, wenn `status != approved` oder
  der Server nicht läuft.
- **G-03:** Pipeline-Fortschritt wird im Output Channel geloggt und als
  `vscode.window.withProgress`-Notification angezeigt.
- **G-04:** Bei terminalem Status erscheint exakt eine abschließende Message
  (Information bei Erfolg, Error bei Fehlschlag) – kein Polling danach.

## Invarianten

- **INV-01:** Gleichzeitig kann maximal eine Pipeline pro Spec laufen
  (identisch zu CON-0020: HTTP 409 wird als Warnung an den Nutzer weitergeleitet).
- **INV-02:** Polling stoppt spätestens wenn ein terminaler Status empfangen wird
  (`labeled | merged | failed | aborted | dry_run`).
- **INV-03:** Die Extension pollt nicht im Idle-Betrieb – nur während eines aktiven Runs.

## Szenarien

```gherkin
Feature: SDD Pipeline Execute aus VS Code

  Background:
    Given ein SDD-Projekt ist im Workspace geöffnet
    And ein SDD-Server läuft auf einem dynamischen Port

  Scenario: Execute Current Spec – approved
    Given die aktive Editor-Datei enthält Frontmatter mit id: SPEC-0007, status: approved
    When der Nutzer "SDD: Execute Current Spec" ausführt
    Then wird POST /api/orchestrate { spec_id: "SPEC-0007" } gesendet
    And eine withProgress-Notification erscheint: "Pipeline läuft – SPEC-0007"
    And der Output Channel zeigt den aktuellen current_step alle 5 s
    And die TreeView-Node für SPEC-0007 zeigt Spinner-Icon + current_step

  Scenario: Execute Current Spec – nicht approved
    Given die aktive Editor-Datei hat status: draft
    When der Nutzer "SDD: Execute Current Spec" ausführt
    Then wird kein HTTP-Request gesendet
    And erscheint eine Warning Message "Spec hat Status 'draft' – nur approved Specs können ausgeführt werden"

  Scenario: Execute Current Spec – Server gestoppt
    Given kein Server läuft
    And die aktive Datei hat status: approved
    When der Nutzer "SDD: Execute Current Spec" ausführt
    Then erscheint eine Information Message "SDD-Server läuft nicht. Jetzt starten?"
    And bei Bestätigung: Server wird gestartet, danach Execute ausgeführt

  Scenario: Execute Current Spec – kein Frontmatter
    Given der aktive Editor hat keine SDD-Frontmatter (kein id-Feld)
    When der Nutzer "SDD: Execute Current Spec" ausführt
    Then öffnet sich ein Quick Pick mit allen Specs die status: approved haben
    And nach Auswahl startet der Execute-Request

  Scenario: Execute Spec per Quick Pick
    Given der Nutzer führt "SDD: Execute Spec" aus
    Then öffnet sich ein Quick Pick mit allen approved Specs
    And nach Auswahl: POST /api/orchestrate { spec_id: "<AUSGEWÄHLT>" }
    And Fortschritts-Notification erscheint

  Scenario: Pipeline laufend – Fortschritts-Update
    Given SPEC-0007 Pipeline-Run ist aktiv (status: running)
    When das Polling GET /api/pipeline/{run_id} current_step: "Code wird generiert…" liefert
    Then zeigt die Notification "Pipeline läuft – SPEC-0007 · Attempt 1/3 · Code wird generiert…"
    And Output Channel loggt "[HH:MM:SS] Code wird generiert…"

  Scenario: Pipeline erfolgreich – labeled
    Given SPEC-0007 Pipeline-Run pollt
    When GET /api/pipeline/{run_id} status: labeled, pr_url: "https://github.com/org/repo/pull/42" liefert
    Then stoppt das Polling
    And erscheint eine Information Message "SPEC-0007 implementiert – PR: https://github.com/org/repo/pull/42"
    And die Message enthält einen klickbaren "PR öffnen"-Button
    And die TreeView-Node zeigt ✓-Icon

  Scenario: Pipeline fehlgeschlagen
    Given SPEC-0007 Pipeline-Run pollt
    When GET /api/pipeline/{run_id} status: failed, reason: "HOL-0003 failed" liefert
    Then stoppt das Polling
    And erscheint eine Error Message "SPEC-0007 Pipeline fehlgeschlagen: HOL-0003 failed"
    And TreeView-Node zeigt ✗-Icon

  Scenario: Pipeline Abort aus VS Code
    Given SPEC-0007 Pipeline-Run ist aktiv
    When der Nutzer "SDD: Abort Pipeline" ausführt
    Then öffnet sich Quick Pick mit dem laufenden Run "SPEC-0007 (Attempt 1/3)"
    And nach Auswahl: POST /api/pipeline/{run_id}/abort
    And Notification wird geschlossen
    And TreeView-Node zeigt ⊘-Icon (aborted)

  Scenario: Mehrere gleichzeitige Runs – 409
    Given SPEC-0007 Pipeline-Run läuft bereits
    When der Nutzer "SDD: Execute Current Spec" nochmals für SPEC-0007 ausführt
    Then antwortet der Server mit HTTP 409
    And erscheint eine Warning Message "Pipeline für SPEC-0007 läuft bereits"

Feature: TreeView Pipeline-Status-Anzeige

  Scenario: Approved-Spec zeigt Execute-Inline-Action
    Given SPEC-0007 hat status: approved
    When der Nutzer über die SPEC-0007-Node im TreeView hovt
    Then erscheint ein ▶-Button als Inline-Action ("Execute")
    And ein Klick auf ▶ führt SDD: Execute Current Spec für SPEC-0007 aus

  Scenario: Laufende Pipeline – Spinner in TreeView
    Given SPEC-0007 Pipeline-Run ist aktiv (status: running, current_step: "Test läuft")
    Then zeigt die TreeView-Node für SPEC-0007:
      - Spinner-Animations-Icon
      - Description: "Test läuft · Attempt 1/3"

  Scenario: Terminale Pipeline – persistentes Icon
    Given SPEC-0007 Pipeline ist mit status: labeled abgeschlossen
    Then zeigt die TreeView-Node für SPEC-0007:
      - ✓-Icon (grün)
      - Tooltip: "PR: https://github.com/org/repo/pull/42"
    And bleibt so bis zum nächsten TreeView-Refresh

Feature: CLI-Wrapper-Commands

  Scenario: Review Contract
    Given der Nutzer führt "SDD: Review Contract" aus
    Then erscheint eine Input Box "Contract-ID eingeben (z.B. CON-0001)"
    And nach Eingabe von "CON-0012": sdd review-contract CON-0012 wird als Subprocess ausgeführt
    And Output erscheint im Output Channel

  Scenario: Estimate Current Spec
    Given die aktive Datei hat id: SPEC-0007
    When der Nutzer "SDD: Estimate Current Spec" ausführt
    Then wird sdd estimate SPEC-0007 ausgeführt
    And eine Information Message zeigt die Kurzform: "SPEC-0007: ~$0.14 (±20%)"
    And der volle Report erscheint im Output Channel
```

## Begriffe

| Begriff              | Definition                                                                           |
|----------------------|--------------------------------------------------------------------------------------|
| withProgress         | VS Code API für Fortschritts-Notifications unten rechts (Location.Notification)      |
| Inline-Action        | Button der in TreeView-Node bei Hover erscheint (contributes.menus: view/item/inline)|
| Polling              | Zyklisches Abfragen von GET /api/pipeline/{run_id} alle `sdd.pipeline.pollInterval` ms|
| terminaler Status    | `labeled`, `merged`, `failed`, `aborted`, `dry_run` – Polling stoppt danach          |
