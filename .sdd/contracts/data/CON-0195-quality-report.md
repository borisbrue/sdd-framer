---
id: CON-0195
title: "Quality-Report"
type: data
format: json-schema
spec: SPEC-0054
version: 0.3.0
status: approved
artifact: ".sdd/contracts/data/quality-report.schema.json"
tests: ["TST-0224"]
---

# Contract: Quality-Report

> **Spec:** SPEC-0054 · **Typ:** Daten (JSON Schema) · **Status:** approved

## Zweck

Legt die Ausgabe von `sdd quality measure --json|--out` fest (SPEC-0054 FR-12). Der Report ist die
Schnittstelle zu allen Verbrauchern: Pipeline-Gates und Supervisor (SPEC-0053), Rollen-Evals
(SPEC-0055), Benchmark (SPEC-0056) und `sdd finalize`. Der Score-Baum `tree` ist die Serialisierung
des Composite; wie die Werte berechnet werden, regelt CON-0196.

## Aufbau

Der Report ist bewusst **ein** Dokument für alle Verbraucher. `tree` trägt die Bewertung,
`requirements`, `architecture` und `probes` tragen die Belege dazu. Eine neue Qualitätsdimension ist
eine Spec-Änderung und erhöht `schema_version`.

## Abgrenzung zur Compliance-Kette (CON-0152/CON-0153)

Die Compliance-Kette beantwortet: *Ist jedem FR ein Test zugeordnet?* (Abdeckung, binär, schon vor
der Umsetzung prüfbar). Der Report beantwortet: *Sind die zugeordneten Tests grün?* (Erfüllung,
vier Status, nur nach einem Testlauf). Beide gelten nebeneinander: Die Kette blockiert
`sdd spec approve` und `sdd finalize` weiter bei fehlender Abdeckung, der Report wirkt über
`quality.gates` (CON-0196). Ein FR kann abgedeckt, aber nicht erfüllt sein, nie umgekehrt.
Beide lesen die FR-IDs mit demselben Parser. Hat die Spec keinen FR-Abschnitt, ist
`requirements` `null` mit Grund „Spec ohne FR“.

## Test-Status

| Status im Report | Herkunft |
|------------------|----------|
| `passed`, `failed`, `error`, `skipped` | Testfall im JUnit-Ergebnis (`<failure>` → `failed`, `<error>` → `error`, `<skipped>` → `skipped`) |
| `not_run` | Test ist dem FR über `fr_test_map` oder `Task.fr_ids` zugeordnet, kommt im JUnit-Ergebnis aber nicht vor |

## Invarianten

- **INV-01:** Jeder Score ist eine Zahl in [0, 1] oder `null`. `null` bedeutet `n/a` und ist nie
  gleichbedeutend mit 0.
- **INV-02:** `score` auf oberster Ebene ist gleich `tree.score`.
- **INV-03:** `incomplete` ist genau dann `true`, wenn mindestens ein Knoten oder eine Metrik im
  Baum `null` ist.
- **INV-04:** Jedes Element ohne Wert trägt einen `reason`: Knoten und Metriken mit `null`,
  Sonden mit `status: "n/a"`. `null` (bei Werten) und `"n/a"` (bei Sondenstatus) sind die einzigen
  beiden Darstellungen von „kein Messwert“.
- **INV-05:** `requirements.frs` enthält jede FR-ID, die der FR-Parser von sdd (`compliance.py`)
  für die Spec liefert, genau einmal, auch ohne zugeordnete Tests (`status: "fehlt"`,
  `tests: []`).
- **INV-06:** FR-Status `unbekannt` tritt genau dann auf, wenn die Sonde mit `role: tests` `n/a` ist. Dann
  sind alle FRs `unbekannt` und der Knoten `requirements` ist `null`.
- **INV-07:** Jeder Verstoß nennt `rule`, `adr` und `symbol` (Verstoß-Schlüssel, CON-0194 INV-09).
  `baselined: true` impliziert `severity: "warn"`.
- **INV-08:** Die Liste `probes` enthält jede in `quality.yaml` definierte Sonde genau einmal, in
  Deklarationsreihenfolge, mit dem **gerenderten** Befehl ohne Geheimnisse (Umgebungsvariablen
  werden nicht expandiert).
- **INV-09:** Der Report enthält keine Inhalte aus `.sdd/holdout/`; `holdout_pass_rate` stammt nur
  aus Ergebnisdateien.

## Beispiele

**Gültig (gekürzt):**
```json
{
  "schema_version": 1, "spec": "SPEC-0900", "git_sha": "abc1234",
  "generated_at": "2026-09-25T10:00:00Z", "duration_ms": 4210, "incomplete": true, "score": 0.8333,
  "tree": { "name": "total", "weight": 1, "score": 0.8333, "renormalized": true, "children": [
    { "name": "requirements", "weight": 0.5, "score": 1.0 },
    { "name": "architecture", "weight": 0.25, "score": 0.5 },
    { "name": "code_quality", "weight": 0.25, "score": null, "reason": "alle Metriken n/a",
      "metrics": [{ "name": "type_errors", "raw": null, "normalized": null,
                    "reason": "Sonde types: Befehl nicht gefunden" }] } ] },
  "requirements": { "frs": [{ "id": "FR-01", "status": "erfüllt",
    "tests": [{ "name": "test_measure_writes_report", "status": "passed", "source": "junit_property" }] }] },
  "architecture": { "violations": [], "rules_na": [], "unresolved_edges": 2 },
  "probes": [{ "name": "types", "command": "mypy --output json tool | …", "format": "sarif",
               "status": "n/a", "reason": "Befehl nicht gefunden", "exit_code": 127, "duration_ms": 3 }]
}
```

**Ungültig (und warum):**
```json
{ "…": "…", "incomplete": false,
  "tree": { "name": "total", "weight": 1, "score": 0.0, "children": [
    { "name": "code_quality", "weight": 0.25, "score": 0 } ] } }
```
→ Wäre `code_quality` wegen ausgefallener Sonden `n/a`, verstößt die 0 gegen INV-01; `incomplete`
müsste dann nach INV-03 `true` sein.

## Validierung

- Schema: `.sdd/contracts/data/quality-report.schema.json` (JSON Schema Draft 2020-12).
- INV-02, INV-03, INV-05, INV-06 und INV-08 sind Querbeziehungen und werden durch TST-0224 geprüft.
