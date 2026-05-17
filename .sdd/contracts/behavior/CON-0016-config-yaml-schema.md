---
id: CON-0016
project: ""
title: "config.yaml-Schema-Contract"
type: behavior
format: markdown
spec: SPEC-0004
version: 0.1.0
status: active
artifact: ""
tests: ["TST-0015"]
---

# Contract: config.yaml-Schema-Contract

> **Spec:** SPEC-0004 · **Typ:** Verhalten · **Status:** active

## Zweck

Dieser Contract spezifiziert das vollständige Schema der Konfigurationsdatei
`.sdd/config.yaml`, wie es für das Dark Factory Pattern benötigt wird.
Die Konfiguration steuert Evaluator, Orchestrator, Auto-Merge und Autonomy Level.

## Vollständiges Schema

```yaml
version: "1.0.0"                 # Pflicht — Schema-Version

project:
  name: "<PROJECT_NAME>"          # Pflicht
  description: "<DESCRIPTION>"   # Optional
  owners:
    - "<TEAM_OR_PERSON>"          # Optional

ids:
  spec_prefix: "SPEC"
  contract_prefix: "CON"
  test_prefix: "TST"
  adr_prefix: "ADR"
  holdout_prefix: "HOL"
  padding: 4

spec_lifecycle:
  - draft
  - review
  - approved
  - implemented
  - deprecated

contract_formats:
  api:
    - openapi
    - asyncapi
    - graphql
    - grpc
  data:
    - json-schema
    - avro
    - protobuf
  behavior:
    - gherkin
    - markdown
  performance:
    - slo-yaml

validation:
  require_contract_per_spec: true
  require_test_per_contract: true
  fail_on_orphans: true
  check_agents_md: true
  allowed_statuses_for_implementation: ["approved", "implemented"]

traceability:
  output_format: "markdown"
  output_path: "docs/traceability.md"

# Evaluator-Sektion (Dark Factory Pattern §3.2)
evaluator:
  model: claude-sonnet-4-6          # überschreibbar; Default: Sonnet
  base_url: http://localhost:8000   # Pflicht für sdd evaluate
  timeout_per_scenario: 60          # Sekunden; Run gilt als failed wenn überschritten
  runs_per_scenario: 3              # Anzahl Runs pro HOL-Szenario
  pass_threshold: 2                 # von runs_per_scenario müssen bestehen
  cost_alert_usd: 1.00              # Hard-Stop bei Überschreitung

# Orchestrator-Sektion (Dark Factory Pattern §3.4)
orchestrator:
  build_command: ""                 # Shell-Befehl für Build + Tests
  auto_merge: false                 # true: PR labeln/mergen wenn Pass-Rate ≥ 90 %
  auto_merge_strategy: label        # "label" (Default) | "direct"
  max_retries: 3                    # Maximale Retry-Versuche

# Maintenance-Sektion (Dark Factory Pattern §3.8)
maintenance:
  stale_after_weeks: 4              # Spec gilt als veraltet nach N Wochen
```

## Garantien

### G-01: Pflichtfelder

`version` und `project.name` sind Pflicht. Fehlt `version`, schlägt `sdd validate` fehl.

### G-02: Evaluator-Defaults

Alle `evaluator`-Felder haben Defaults (wie oben dokumentiert). Fehlt die gesamte
`evaluator`-Sektion, verwendet `sdd evaluate` diese Defaults.

| Feld                    | Default                 | Typ     |
|-------------------------|-------------------------|---------|
| `model`                 | `claude-sonnet-4-6`     | string  |
| `base_url`              | `http://localhost:8000` | string  |
| `timeout_per_scenario`  | `60`                    | int     |
| `runs_per_scenario`     | `3`                     | int     |
| `pass_threshold`        | `2`                     | int     |
| `cost_alert_usd`        | `1.00`                  | float   |

### G-03: Auto-Merge-Strategie

`auto_merge_strategy: label` (Standard) setzt das Label `sdd:approved` am PR.
`auto_merge_strategy: direct` ruft direkt `gh pr merge` auf.
Voraussetzung: GitHub Bot/App mit den in SPEC-0004 §3.6 dokumentierten Permissions.

### G-04: Evaluator-Kosten-Hard-Stop

Überschreitet der kumulative `total_cost_usd` aller Szenario-Runs innerhalb eines
`sdd evaluate`-Aufrufs den Wert `cost_alert_usd`:
1. Laufender Evaluations-Run wird abgebrochen
2. Bereits abgeschlossene Ergebnisse werden in `evaluations.db` gespeichert
3. PR erhält Label `sdd:cost-limit`
4. GitHub Issue wird geöffnet

### G-05: GitHub-Token

`SDD_GITHUB_TOKEN` muss als Umgebungsvariable (GitHub Secret) hinterlegt sein,
wenn `auto_merge: true` oder GitHub-Issue-Erstellung genutzt wird.
Die Variable wird vom GitHub Actions Workflow-Template referenziert.

## Invarianten

- **INV-01:** `auto_merge: true` ist nur wirksam wenn `autonomy_level ≥ 3` im Projekt-YAML.
- **INV-02:** `cost_alert_usd` wird nach jedem Szenario kumuliert geprüft (nicht erst am Ende).
- **INV-03:** `runs_per_scenario` und `pass_threshold` müssen die Bedingung
  `pass_threshold ≤ runs_per_scenario` erfüllen; sonst Fehler beim Start von `sdd evaluate`.

## Begriffe

| Begriff              | Definition                                                         |
|----------------------|--------------------------------------------------------------------|
| Hard-Stop            | Sofortiger Abbruch des Evaluations-Laufs bei Kostenlimit           |
| `sdd:approved`       | GitHub-Label, das Auto-Merge auslöst (label-Strategie)             |
| `sdd:cost-limit`     | GitHub-Label, das nach Hard-Stop gesetzt wird                      |
| `sdd:failed`         | GitHub-Label nach Erschöpfung aller Retries                        |
| `SDD_GITHUB_TOKEN`   | GitHub App/Bot-Token mit PR-write + issues-write Permissions       |
