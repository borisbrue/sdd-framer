---
id: CON-0217
title: "Golden Case case.yaml"
type: data
format: json-schema
spec: SPEC-0055
version: 0.1.0
status: draft
artifact: ".sdd/contracts/data/golden-case-case-yaml.schema.json"
tests: ["TST-0246"]
---

# Contract: Golden Case case.yaml

> **Spec:** SPEC-0055 · **Typ:** Daten (JSON Schema) · **Status:** draft

## Zweck

Beschreibt `case.yaml`, die Beschreibung eines Golden Case (SPEC-0055 FR-01), und die Struktur seines Verzeichnisses.

## Garantien

Das Schema im Artifact ist verbindlich; `sdd validate` und `sdd role eval` lehnen ungültige Fälle ab.

## Invarianten

- **INV-01:** Ein Fall liegt in genau einem Verzeichnis `<ID>-<slug>/` entweder unter `.sdd/roles/<rolle>/cases/` (sichtbar) oder unter `.sdd/holdout/roles/<rolle>/` (Holdout); ein Holdout-Flag in `case.yaml` gibt es nicht. `role` stimmt mit dem Verzeichnis überein.
- **INV-02:** Die ID hat das Präfix der Rolle (`DEC-` decomposer, `TAU-` test_author, `IMP-` implementer, `REV-` reviewer, `SUP-` supervisor, `JDG-` judge) und ist über beide Orte eindeutig. Nur `sdd role case new` und `capture` vergeben IDs.
- **INV-03:** Das Verzeichnis enthält `input/` (eingefrorener Snapshot der Rolleneingaben). Je nach Checks kommen hinzu: `reference/` (Referenzlösung), `hidden/` (versteckte Tests), `mutants/*.patch` (einzeln anwendbare Patches gegen `reference/`) und `expected/` (erwartete Entscheidung oder Befunde, JSON). Ein Check, dessen benötigter Bestandteil fehlt, macht den Fall ungültig.
- **INV-04:** `expect.checks` nennt jeden Check genau mit seinen Parametern (ein Objekt je Eintrag); Name und Parameter werden gegen die Registry (CON-0219 INV-01) geprüft. `test_command` ist Pflicht, sobald ein ausführungsbasierter Check vorkommt.
- **INV-05:** `weights.checks + weights.rubric = 1`; fehlt `weights`, gilt 1/0 ohne Rubrik und 0,8/0,2 mit Rubrik. Der Fall-Score ist `checks × Mittel der Check-Scores + rubric × (Mittel der Rubrikwerte − 1) / 4`.
- **INV-06:** `draft: true` (z. B. nach `capture`) zählt in keinem Score und keiner Ratchet-Entscheidung.

## Beispiele

**Gültig:**
```yaml
id: DEC-001
role: decomposer
origin: blueprint
expect:
  checks:
    - fr_coverage: {min: 1.0}
    - task_count: {min: 4, max: 9}
  rubric:
    - {id: granularity, question: "Ist jeder Task einzeln testbar?"}
weights: {checks: 0.8, rubric: 0.2}
```

**Ungültig:** `id: X-1` (Präfix), `holdout: true` (unbekanntes Feld), `hidden_tests_pass` ohne
`test_command`.
