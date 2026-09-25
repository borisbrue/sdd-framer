---
id: CON-0192
title: "Quality-Config: Sonden, Normierung und Suppressions in .sdd/quality.yaml"
type: data
format: json-schema
spec: SPEC-0054
version: 0.1.0
status: draft
artifact: ".sdd/contracts/data/quality-config-sonden-normierung-und-suppressions-in-sdd-quality-yaml.schema.json"
tests: ["TST-0221"]
---

# Contract: Quality-Config: Sonden, Normierung und Suppressions in .sdd/quality.yaml

> **Spec:** SPEC-0054 · **Typ:** Daten (JSON Schema) · **Status:** draft

## Zweck

Beschreibt `.sdd/quality.yaml`, die einzige Stelle, an der ein Projekt festlegt, **welche Werkzeuge**
seine Qualität messen (SPEC-0054 FR-01, FR-02, FR-08, FR-13). sdd liest die Datei bei
`sdd quality measure|doctor`, bei `sdd test run` (Sonde `tests`, FR-03) und schreibt sie nur bei
`sdd quality init` (als Kopie eines Presets bzw. `.new`).

## Invarianten

- **INV-01:** Jeder Sondenbefehl enthält den Platzhalter `{out}`. Die Sonde schreibt ihr Ergebnis
  ausschließlich dorthin; stdout/stderr gelten nur als Diagnose.
- **INV-02:** Eine Sonde mit dem reservierten Namen `tests` hat `format: junit` und ein
  `fr_marker`. Nur sie speist die Anforderungserfüllung.
- **INV-03:** `fr_marker` ist nur bei `format: junit` erlaubt.
- **INV-04:** `format` ist eines von `junit`, `sarif`, `cobertura`, `lcov`, `sdd-deps`,
  `sdd-metrics`, `sdd-findings`. Werkzeugnamen kommen im Schema nicht vor.
- **INV-05:** Für jede `metric`, die eine Sonde speist und die nicht eingebaut ist
  (`lint_per_kloc`, `type_errors`, `suppressions`, `test_ratio`), existiert ein Eintrag in
  `normalization`. Das prüft `sdd quality doctor` (Laufzeitprüfung, nicht im Schema ausdrückbar).
- **INV-06:** `normalization.<m>.good ≠ bad`. `good < bad` bedeutet „kleiner ist besser“,
  `good > bad` „größer ist besser“ (Laufzeitprüfung; Formel in CON-0196).
- **INV-07:** Kein Sondenbefehl und kein Glob verweist auf `.sdd/holdout/`. Ein solcher Eintrag
  macht die Sonde `n/a` mit Grund „Holdout-Pfad verboten“ (Laufzeitprüfung).
- **INV-08:** `timeout_seconds` gilt pro Sondenaufruf, Default 600. Überschreitung ist ein
  Sondenausfall (CON-0196).

## Platzhalter

| Platzhalter | Wert |
|-------------|------|
| `{out}`     | Absoluter Pfad einer temporären Ergebnisdatei je Sondenaufruf |
| `{paths}`   | Leerzeichengetrennte, shell-quotierte Liste der gemessenen Dateien. Ohne `--diff` oder bei `diff_scoped: false` sind das alle Projektdateien nach `exclude`. |

## Beispiele

**Gültig:**
```yaml
version: 1
preset: python
probes:
  tests: { command: "pytest -q --junitxml={out}", format: junit, fr_marker: property }
  lint:  { command: "ruff check --output-format sarif --output-file {out} {paths}", format: sarif,
           metric: lint_per_kloc, diff_scoped: true, version_command: "ruff --version" }
  complexity: { command: "lizard --xml {paths} | python .sdd/quality/lizard_to_metrics.py > {out}",
                format: sdd-metrics }
normalization:
  complexity_max: { good: 10, bad: 30 }
suppressions:
  "**/*.py": ['#\s*noqa']
exclude: ["vendor/**"]
```

**Ungültig (und warum):**
```yaml
version: 1
probes:
  tests: { command: "pytest -q", format: sarif }
```
→ Verstößt gegen INV-01 (kein `{out}`) und INV-02 (`tests` ist nicht `junit`, kein `fr_marker`).

## Validierung

- Schema: `.sdd/contracts/data/quality-config-sonden-normierung-und-suppressions-in-sdd-quality-yaml.schema.json`
  (JSON Schema Draft 2020-12), angewendet auf die geparste YAML-Datei.
- INV-05 bis INV-07 prüft `sdd quality doctor` bzw. `ProbeRun` zur Laufzeit.
