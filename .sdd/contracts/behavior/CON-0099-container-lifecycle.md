---
id: CON-0099
title: "Container-Lifecycle – Erstellung, Task-Zuweisung und Cleanup"
type: behavior
format: gherkin
spec: SPEC-0026
version: 0.1.0
status: draft
artifact: "contracts/behavior/container-lifecycle.feature"
tests:
- TST-0118
---

# Contract: Container-Lifecycle – Erstellung, Task-Zuweisung und Cleanup

> **Spec:** SPEC-0026 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Legt fest, wie Container erstellt, mit Tasks befüllt, gestartet, gestoppt und
nach Abschluss entfernt werden (FR-07/16). Ein Container kapselt den
Code-Stand zum Zeitpunkt der Task-Verteilung und isoliert die Ausführung
vollständig vom Host-System.

## Garantien

- Container werden aus dem aktuellen Git-Stand (HEAD) gebaut (`git archive` + Dockerfile).
- Ein oder mehrere Tasks können einem Container zugewiesen werden (flexibler Zuschnitt).
- Container laufen ohne Netzwerkzugang zu Produktionssystemen.
- Nach Abschluss aller Tasks im Container (committed oder blocked) wird er entfernt.
- Bei Abbruch (SIGINT, Fehler) werden alle laufenden Container ebenfalls entfernt.

## Invarianten

- **INV-01:** Ein Container enthält mindestens einen Task.
- **INV-02:** Der Code-Stand im Container entspricht dem Git-HEAD zum Zeitpunkt des `sdd distribute`-Aufrufs (kein Live-Mount).
- **INV-03:** Container-Namen folgen dem Schema `sdd-SPEC-XXXX-<uuid>`.
- **INV-04:** Nach `container.remove()` existiert kein Docker-/Podman-Objekt mehr mit dieser ID.

## Szenarien (Gherkin)

```gherkin
Feature: Container-Lifecycle

  Scenario: Container mit einem Task erstellen und starten
    Given Git-HEAD ist commit "abc123"
    And ein Task T1 für SPEC-0026
    When container.create([T1]) aufgerufen wird
    Then existiert ein Container "sdd-SPEC-0026-<uuid>"
    And der Code-Stand im Container entspricht commit "abc123"

  Scenario: Mehrere Tasks in einem Container
    Given drei Tasks T1, T2, T3 mit complexity="low"
    When container.create([T1, T2, T3]) aufgerufen wird
    Then sind alle drei Tasks dem selben Container zugewiesen

  Scenario: Cleanup nach Abschluss
    Given Container C1 mit Task T1 (status: committed)
    When container.remove(C1) aufgerufen wird
    Then existiert kein Container mit ID C1 mehr (INV-04)

  Scenario: Cleanup bei Abbruch
    Given zwei laufende Container C1, C2
    When der Prozess SIGINT empfängt
    Then werden C1 und C2 entfernt bevor der Prozess endet

  Scenario: Netzwerk-Isolation
    Given ein laufender Container
    When eine ausgehende HTTP-Anfrage an eine externe URL gesendet wird
    Then wird die Anfrage blockiert (kein Produktionszugang)
```

## Begriffe

| Begriff | Definition |
|---|---|
| Git-Snapshot | `git archive HEAD` als Basis für den Container-Build |
| Netzwerk-Isolation | Container hat kein Default-Network-Binding außer einem internen Task-Channel |
