---
id: CON-0198
title: "Architektur-Baseline"
type: data
format: json-schema
spec: SPEC-0054
version: 0.1.0
status: approved
artifact: ".sdd/contracts/data/architektur-baseline.schema.json"
tests: ["TST-0227"]
---


# Contract: Architektur-Baseline

> **Spec:** SPEC-0054 · **Typ:** Daten (JSON Schema) · **Status:** approved

## Zweck

Beschreibt `.sdd/quality/arch-baseline.json`: bekannte Architekturverstöße, die bis zu ihrer
Behebung nur als `warn` gelten (SPEC-0054 FR-07). So kann ein Projekt mit Altlasten Regeln sofort
einführen, ohne dass `sdd arch check` dauerhaft rot ist. Neue Verstöße bleiben `error`. Die Baseline
ändert sich aus anderen Gründen als die Regeln (CON-0194): Sie schrumpft mit jedem Fix.

## Invarianten

- **INV-01:** Ein Eintrag passt auf einen Verstoß genau dann, wenn `rule`, `file` und `symbol` dem
  Verstoß-Schlüssel (CON-0194 INV-09) entsprechen. Die Zeilennummer spielt keine Rolle.
- **INV-02:** Ein passender Verstoß wird auf `warn` herabgestuft und im Report mit
  `baselined: true` markiert. Er zählt nicht zu `count.architecture.errors` (CON-0196).
- **INV-03:** Ein Eintrag ohne passenden Verstoß ist veraltet. Er zählt als
  `stale_baseline_entries` und wird gemeldet, hat aber keine Wirkung auf den Score.
- **INV-04:** Jeder Eintrag hat einen nicht leeren `reason`. `fixed_by` nennt, sofern bekannt, die
  Spec, die den Verstoß beheben soll.
- **INV-05:** Die Datei wird nur von `sdd arch check --write-baseline` erzeugt oder ergänzt, sonst
  von Hand gepflegt. Beim Schreiben bleiben vorhandene Einträge mit ihrem `reason` erhalten; neue
  bekommen `reason: "TODO"`.

## Beispiele

**Gültig:**
```json
{ "version": 1, "entries": [
  { "rule": "ARCH-03", "file": "tool/sdd_cli/decompose.py", "symbol": "ClaudeCliCompletionProvider",
    "reason": "Decomposer hart auf Claude verdrahtet", "fixed_by": "SPEC-0053" } ] }
```

**Ungültig (und warum):**
```json
{ "version": 1, "entries": [ { "rule": "ARCH-03", "file": "tool/sdd_cli/decompose.py", "symbol": "" } ] }
```
→ Verstößt gegen das Schema (`symbol` darf nicht leer sein, weil der Verstoß-Schlüssel nach
CON-0194 INV-09 immer ein Symbol hat) und gegen INV-04 (`reason` fehlt).

## Validierung

- Schema: `.sdd/contracts/data/architektur-baseline.schema.json` (JSON Schema Draft 2020-12).
- INV-01 bis INV-03 und INV-05 prüft TST-0227.
