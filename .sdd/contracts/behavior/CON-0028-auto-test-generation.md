---
id: CON-0028
project: PRJ-0001
title: "Auto Test Generation – Verhalten"
type: behavior
format: gherkin
spec: SPEC-0014
version: 0.1.0
status: draft
artifact: "contracts/behavior/auto-test-generation.feature"
tests: ["TST-0040"]
---

# Contract: Auto Test Generation – Verhalten

> **Spec:** SPEC-0014 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Definiert das Verhalten von `sdd test generate <SPEC-ID>` (Phase 6): Welche
Testdateien werden aus welchen Contract-Formaten generiert, welche Qualitäts-
anforderungen gelten, und wie sich der Befehl bei Fehlern und Re-Runs verhält.

## Garantien

Die im Artifact hinterlegten Szenarien sind **ausführbare Spezifikation**.
Jedes Szenario MUSS durch einen automatisierten Test abgedeckt sein.

## Invarianten

- **INV-01:** Jedes Gherkin-Scenario im Contract erzeugt mindestens eine
  Testfunktion in der generierten Datei.
- **INV-02:** Happy-Path und alle definierten Error-Cases sind abgedeckt
  (kein Scenario ohne Test).
- **INV-03:** Generierte Tests sind eigenständig lauffähig — kein globaler
  Shared State zwischen Testfunktionen.
- **INV-04:** Jede generierte Testdatei beginnt mit dem Header-Kommentar:
  `# AUTO-GENERATED from <CON-ID> via sdd test generate — do not delete`.
- **INV-05:** Bereits existierende Testdateien werden nicht überschrieben
  wenn sie manuell erweitert wurden (Änderungen nach Generierung bleiben erhalten).
- **INV-06:** `pytest --collect-only` auf generierte Dateien läuft ohne
  SyntaxError oder ImportError durch.
- **INV-07:** Generierte Tests dürfen nach Erstellung manuell ergänzt,
  aber nicht gelöscht werden.

## Zielpfad des generierten Codes

Der Pfad wird in dieser Rangfolge bestimmt:

1. **`artifact:` des zugehoerigen TST-Dokuments** (gefunden ueber dessen
   `contract:`-Feld). Nur so entsteht die Datei, die das Test-Dokument
   deklariert — sonst reisst die Kette Spec → Contract → Test → Code.
2. **`tests/<level>/test_{con_id_lower}.py`**, wenn das TST-Dokument kein
   `artifact:` traegt. Das `level:` des Dokuments entscheidet, nicht der
   Contract-Typ.
3. **Die Format-Tabelle unten**, wenn zu dem Contract gar kein TST-Dokument
   existiert.

Der ausfuehrbare Testcode liegt in allen drei Faellen unter `tests/`;
`.sdd/` haelt ausschliesslich die SDD-Dokumente.

## Generierungsstrategie pro Format (Rueckfall, siehe Punkt 3 oben)

| Contract-Format | Test-Framework  | Output-Pfad |
|-----------------|-----------------|-------------|
| `gherkin`       | pytest-bdd      | `tests/behavior/test_{con_id_lower}.py` |
| `openapi`       | pytest + httpx  | `tests/api/test_{con_id_lower}.py` |
| `json-schema`   | pytest + jsonschema | `tests/data/test_{con_id_lower}.py` |
| `slo-yaml`      | pytest + assertions | `tests/performance/test_{con_id_lower}.py` |
| `markdown`      | pytest (manuell) | `tests/behavior/test_{con_id_lower}.py` (Skeleton) |

## Begriffe

| Begriff         | Definition |
|-----------------|------------|
| Skeleton        | Generierte Testdatei mit leeren `pass`-Funktionen als Startpunkt |
| Re-Run          | Erneuter Aufruf von `sdd test generate` nach Änderung eines Contracts |
| CON-ID-lower    | Contract-ID in Kleinbuchstaben mit Bindestrich, z.B. `con-0025` |
