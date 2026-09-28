---
id: CON-0192
title: "Quality-Config: Sonden, Normierung und Suppressions in .sdd/quality.yaml"
type: data
format: json-schema
spec: SPEC-0054
version: 0.3.0
status: approved
artifact: ".sdd/contracts/data/quality-config-sonden-normierung-und-suppressions-in-sdd-quality-yaml.schema.json"
tests: ["TST-0221"]
---

# Contract: Quality-Config: Sonden, Normierung und Suppressions in .sdd/quality.yaml

> **Spec:** SPEC-0054 · **Typ:** Daten (JSON Schema) · **Status:** approved

## Zweck

Beschreibt `.sdd/quality.yaml`, die einzige Stelle, an der ein Projekt festlegt, **welche Werkzeuge**
seine Qualität messen (SPEC-0054 FR-01, FR-02, FR-08, FR-13). sdd liest die Datei bei
`sdd quality measure|doctor`, bei `sdd test run` (Sonde mit `role: tests`, FR-03) und schreibt sie nur bei
`sdd quality init` (als Kopie eines Presets bzw. `.new`).

## Invarianten

- **INV-01:** Jeder Sondenbefehl enthält den Platzhalter `{out}`. Die Sonde schreibt ihr Ergebnis
  ausschließlich dorthin; stdout/stderr gelten nur als Diagnose.
- **INV-02:** Die Bedeutung einer Sonde für sdd ergibt sich aus ihrer `role`, nie aus ihrem Namen.
  `role: tests` verlangt `format: junit` und ein `fr_marker`; nur diese Sonde speist die
  Anforderungserfüllung. `role: deps` verlangt `format: sdd-deps`; nur diese Sonde liefert Kanten für
  Architekturregeln. Sonden ohne `role` liefern Metriken oder Befunde.
- **INV-03:** Je `role` gibt es höchstens eine Sonde (Laufzeitprüfung, Konfigurationsfehler bei
  Verstoß). `fr_marker` ist nur bei `role: tests` erlaubt.
- **INV-04:** `format` ist eines von `junit`, `sarif`, `cobertura`, `lcov`, `sdd-deps`,
  `sdd-metrics`, `sdd-findings`. Werkzeugnamen kommen im Schema nicht vor. Die Liste ist bewusst
  geschlossen. Werkzeuge ohne eines dieser Formate werden über Konverter auf `sdd-metrics` bzw.
  `sdd-findings` angebunden (CON-0193), ohne Änderung an diesem Contract.
- **INV-05:** Für jede `metric`, die eine Sonde speist und die nicht eingebaut ist
  (`lint_per_kloc`, `type_errors`, `suppressions`, `test_ratio`), existiert ein Eintrag in
  `normalization`. Das prüft `sdd quality doctor` (Laufzeitprüfung, nicht im Schema ausdrückbar).
- **INV-06:** `normalization.<m>.good ≠ bad`. `good < bad` bedeutet „kleiner ist besser“,
  `good > bad` „größer ist besser“ (Laufzeitprüfung; Formel in CON-0196).
- **INV-07:** Kein Sondenbefehl und kein Glob verweist auf `.sdd/holdout/` (Laufzeitprüfung,
  siehe INV-09).
- **INV-08:** `timeout_seconds` gilt pro Sondenaufruf, Default 600.
- **INV-09 (Sondenausfall):** Eine Sonde ist genau dann ausgefallen, wenn einer dieser Fälle eintritt.
  Ihr Ergebnis ist dann `n/a` mit dem angegebenen Grund:
  | Fall | Grund |
  |------|-------|
  | Befehl nicht gefunden (Exit-Code 127 bzw. Startfehler) | `Befehl nicht gefunden` |
  | `timeout_seconds` überschritten | `Zeitlimit überschritten` |
  | keine oder leere Datei unter `{out}` | `keine Ausgabe` |
  | Datei unter `{out}` genügt dem Format nicht | `Ausgabe nicht parsebar` |
  | Befehl oder Glob verweist auf `.sdd/holdout/` | `Holdout-Pfad verboten` |

  Ein Exit-Code ≠ 0 **mit** gültiger Ausgabe ist kein Ausfall, z. B. ein Linter mit Befunden oder
  Tests mit Fehlschlägen. Welche Folgen ein Ausfall für die Scores hat, regelt CON-0196.

## Platzhalter

| Platzhalter | Wert |
|-------------|------|
| `{out}`     | Absoluter Pfad einer temporären Ergebnisdatei je Sondenaufruf |
| `{paths}`   | Leerzeichengetrennte, shell-quotierte Liste der gemessenen Dateien: alle Dateien, die auf `paths` passen (Default: alle außer `.sdd/**`, `.git/**`), abzüglich `exclude`. Mit `--diff` und `diff_scoped: true` nur die geänderten davon. Dieselbe Dateimenge ist die Basis für Kennzahlen je 1000 Zeilen. |

## Beispiele

**Gültig:**
```yaml
version: 1
preset: python
probes:
  pytest: { command: "pytest -q --junitxml={out}", format: junit, role: tests, fr_marker: property }
  imports: { command: "python .sdd/quality/extract_deps.py {paths} > {out}", format: sdd-deps, role: deps }
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
  pytest: { command: "pytest -q", format: sarif, role: tests }
```
→ Verstößt gegen INV-01 (kein `{out}`) und INV-02 (`role: tests` ohne `junit` und ohne `fr_marker`).

## Validierung

- Schema: `.sdd/contracts/data/quality-config-sonden-normierung-und-suppressions-in-sdd-quality-yaml.schema.json`
  (JSON Schema Draft 2020-12), angewendet auf die geparste YAML-Datei.
- INV-03 und INV-05 bis INV-09 prüft `sdd quality doctor` bzw. `ProbeRun` zur Laufzeit.

## Seit SPEC-0057

`.sdd/quality.yaml` schreiben auch `sdd stack apply` (auch mit `--only quality`) und `sdd stack extract` (in eine Vorlage); überschrieben wird nie, abweichende Dateien entstehen als `.new` (CON-0229 INV-01). Das Feld `preset` bleibt optional.
