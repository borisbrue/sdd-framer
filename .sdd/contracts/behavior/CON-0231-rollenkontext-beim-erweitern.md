---
id: CON-0231
title: "Rollenkontext beim Erweitern"
type: behavior
format: gherkin
spec: SPEC-0065
version: 0.1.0
status: approved
artifact: ".sdd/contracts/behavior/rollenkontext-beim-erweitern.feature"
tests: ["TST-0260"]
---

# Contract: Rollenkontext beim Erweitern

> **Spec:** SPEC-0065 · **Typ:** Verhalten (Gherkin) · **Status:** approved

## Zweck

Legt fest, welchen Kontext Test-Autor und Implementer beim Erweitern bestehenden Codes bekommen,
und wie Prüf-Tasks zerlegt werden (SPEC-0065 FR-01 bis FR-05). Die Quellen sind in CON-0199
gelistet.

## Garantien

Die Szenarien im Artifact (`.sdd/contracts/behavior/rollenkontext-beim-erweitern.feature`) sind
**ausführbare Spezifikation**.

## Invarianten

- **INV-01:** Die Rolle `test_author` hat die Quellen `current_files` und `dependency_api`, die
  Rolle `implementer` zusätzlich zu `current_files` (HF-0012) die Quelle `dependency_api`.
  `current_files` enthält die vorhandenen Dateien aus den `allowed_paths` der Task ohne deren
  Testdatei, ohne `.sdd/` und ohne Holdouts.
- **INV-02:** `dependency_api` enthält je Abhängigkeits-Task (`dependencies`) im Zustand `done`
  die vorhandenen Dateien aus deren `allowed_paths` mit Pfad und den öffentlichen Definitionen
  ohne Rümpfe. Nicht erledigte Abhängigkeiten, Testdateien, `.sdd/` und Holdouts erscheinen nicht.
- **INV-03:** Signaturen liefert ein Extraktor aus einer Registry je Dateiendung (Python `.py`
  mitgeliefert). Für Dateien ohne Extraktor oder mit Syntaxfehler nennt `dependency_api` nur den
  Pfad mit Hinweis. Der Pipeline-Kern nennt keine Programmiersprache.
- **INV-04:** Jede Quelle wird nach dem Budget der Rolle gekürzt; eine gekürzte Quelle endet mit
  einem sichtbaren Hinweis. Budgets: `current_files` beim Test-Autor 8 000, `dependency_api` 4 000.
- **INV-05:** Die Rolle `decomposer` legt Tasks, die nur bestehendes Verhalten absichern und keinen
  Code ändern sollen, als Typ `test` an. Golden Case DEC-009 enthält eine solche Anforderung und
  erwartet eine Task vom Typ `test`. Für Tasks vom Typ `test` gibt es keine rote Phase: ihr Test
  muss sofort grün sein (Gate `test`, SPEC-0061 FR-06), danach folgt das Review ohne
  Implementer. Die Regel gilt für die Rolle `decomposer` der Pipeline; die Klassifikation von
  `sdd decompose` (CON-0097) bleibt unverändert.
- **INV-06:** Die Rolle `test_author` nennt in ihren Regeln: Tests verwenden nur Namen aus
  `current_files`, `dependency_api` oder der Task-Beschreibung; vorhandene Klassen des Projekts
  werden nicht durch Mocks ersetzt. Golden Case TAU-009 prüft das an einer Erweiterung mit
  vorhandenem Repository.
