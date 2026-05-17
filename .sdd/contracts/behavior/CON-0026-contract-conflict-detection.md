---
id: CON-0026
project: PRJ-0001
title: "Contract Conflict Detection – Analyse-Verhalten"
type: behavior
format: gherkin
spec: SPEC-0014
version: 0.1.0
status: draft
artifact: "contracts/behavior/contract-conflict-detection.feature"
tests: ["TST-0038"]
---

# Contract: Contract Conflict Detection – Analyse-Verhalten

> **Spec:** SPEC-0014 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Definiert das Verhalten der Contract-Konflikt-Analyse (Phase 5). Legt fest,
was als Konflikt gilt, wie der Analyse-Prozess abläuft, welche Informationen
im Konfliktbericht stehen und unter welchen Bedingungen Phase 5 als bestanden gilt.

## Garantien

Die im Artifact hinterlegten Szenarien sind **ausführbare Spezifikation**.
Jedes Szenario MUSS durch einen automatisierten Test abgedeckt sein.

## Invarianten

- **INV-01:** Die Analyse prüft neue Contracts gegen **alle** Contracts im
  Workspace mit `status: active` oder `status: draft`.
- **INV-02:** Jeder erkannte Konflikt erhält eine eindeutige ID nach Schema
  `CF-{SPEC-ID}-{NNN}` (z.B. `CF-0014-001`).
- **INV-03:** Phase 5 gilt erst als bestanden wenn alle Konflikte den Status
  `resolved` oder `acknowledged` haben — nie automatisch.
- **INV-04:** Das Konfliktbericht-JSON wird nach
  `.sdd/conflict-reports/{spec-id}-conflicts.json` geschrieben.
- **INV-05:** Workspace-Contract-Extraktion wird gecacht; Invalidierung erfolgt
  bei jeder inhaltlichen Änderung einer Contract-Datei (Datei-Hash-basiert).
- **INV-06:** Die Analyse läuft in < 30 s für ≤ 50 Contracts im Workspace.
- **INV-07:** `sdd conflict acknowledge` ohne `--reason` wird abgelehnt.

## Konflikttypen

| Typ                    | Beschreibung |
|------------------------|--------------|
| `endpoint-overlap`     | Zwei API-Contracts definieren dieselbe HTTP-Methode + Pfad-Kombination |
| `field-contradiction`  | Zwei Data-Contracts definieren dasselbe Feld mit inkompatiblen Typen oder Constraints |
| `behavior-contradiction` | Zwei Behavior-Contracts definieren dasselbe Szenario mit unterschiedlichem Ergebnis |
| `scope-overlap`        | Zwei Contracts adressieren denselben fachlichen Bereich ohne klare Abgrenzung |
| `dependency-gap`       | Contract referenziert externe Schnittstelle ohne eigenen abdeckenden Contract |

## Auflösungsaktionen

| Aktion     | Bedeutung |
|------------|-----------|
| `refactor` | Konflikt durch Umstrukturierung eines Contracts behoben |
| `extend`   | Bestehender Contract wird erweitert statt neuen zu erstellen |
| `version`  | Endpunkt / Feld wird versioniert (v2, v3) |
| `split`    | Contract wird in zwei klar abgegrenzte Contracts aufgeteilt |

## Begriffe

| Begriff          | Definition |
|------------------|------------|
| Workspace-Scan   | Laden aller Contract-Dateien aus `contracts/` des aktuellen Projekts |
| Impact-Score     | Anzahl betroffener SPECs × Schweregrad-Gewicht (high=3, medium=2, low=1) |
| CF-ID            | Eindeutige Konflikt-ID: `CF-{SPEC-ID ohne Prefix}-{NNN}`, z.B. `CF-0014-001` |
