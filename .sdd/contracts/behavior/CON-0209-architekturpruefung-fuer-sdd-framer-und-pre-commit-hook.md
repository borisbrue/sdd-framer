---
id: CON-0209
title: "Architekturprüfung für sdd-framer und Pre-Commit-Hook"
type: behavior
format: gherkin
spec: SPEC-0059
version: 0.1.0
status: approved
artifact: ".sdd/contracts/behavior/architekturpruefung-fuer-sdd-framer-und-pre-commit-hook.feature"
tests: ["TST-0238"]
---

# Contract: Architekturprüfung für sdd-framer und Pre-Commit-Hook

> **Spec:** SPEC-0059 · **Typ:** Verhalten (Gherkin) · **Status:** approved

## Zweck

Legt fest, wie sich `sdd arch check` auf dem Repo-Stand von sdd-framer verhält (Regeln ARCH-01 bis
ARCH-04, Baseline, ADR-Bindung) und wie der Pre-Commit-Hook die Prüfung einbindet (SPEC-0059 FR-01
bis FR-07).

## Garantien

Die Szenarien im Artifact (`.sdd/contracts/behavior/architekturpruefung-fuer-sdd-framer-und-pre-commit-hook.feature`)
sind **ausführbare Spezifikation**. Jedes Szenario MUSS durch einen automatisierten Test (pytest)
abgedeckt sein. Szenarien, die einen Verstoß einbauen, arbeiten auf einer temporären Kopie des Repos,
nie im Arbeitsbaum.

## Invarianten

- **INV-01:** Auf dem Repo-Stand endet `sdd arch check` mit Exit 0; jeder Verstoß ist ein
  Baseline-Treffer (`warn (Baseline[, SPEC-XXXX]))`), `fixed_by` erscheint in der Ausgabe.
- **INV-02:** Ein neuer Verstoß, der nicht in der Baseline steht, führt zu Exit 1 und nennt Regel,
  Datei, Zeile, Symbol und ADR (CON-0194 INV-08/09).
- **INV-03:** Der Pre-Commit-Hook führt die Prüfung nur aus, wenn `.sdd/architecture.yaml`
  existiert, mindestens eine gestagte `.py`-Datei vorliegt und `quality.arch_pre_commit` nicht
  `false` ist. Exit 1 der Prüfung blockiert den Commit; Exit 2 (Abhängigkeiten nicht messbar) wird
  gemeldet, blockiert aber nicht.
- **INV-04:** Ohne `.sdd/architecture.yaml` verhält sich der Hook wie vor SPEC-0059.
- **INV-05:** `sdd arch check` braucht auf dem Repo-Stand weniger als 10 s.

## Begriffe

| Begriff | Definition |
|---------|------------|
| Baseline-Treffer | Verstoß, dessen Schlüssel `(rule, file, symbol)` in `.sdd/quality/arch-baseline.json` steht (CON-0198) |
| Repo-Stand | Arbeitsbaum von sdd-framer ohne zusätzliche Änderungen durch den Test |
