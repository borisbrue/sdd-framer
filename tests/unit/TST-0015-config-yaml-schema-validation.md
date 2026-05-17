---
id: TST-0015
project: ""
title: "config.yaml-Schema-Validierung"
level: unit
spec: SPEC-0004
contract: CON-0016
status: planned
framework: "pytest"
artifact: "tests/unit/test_config_yaml_schema.py"
tags: ["config", "schema", "dark-factory", "evaluator"]
---

# Test: config.yaml-Schema-Validierung

> **Level:** unit · **Spec:** SPEC-0004 · **Contract:** CON-0016 · **Status:** planned

## Was wird geprüft?

Die Pflichtfelder und Defaults der `.sdd/config.yaml`-Sektion gemäß CON-0016:
- `evaluator.*`-Defaults werden korrekt angewendet wenn Sektion fehlt (G-02)
- `runs_per_scenario ≥ pass_threshold` wird geprüft (INV-03)
- `auto_merge_strategy` ist `"label"` oder `"direct"` (G-03)
- `SddConfig.raw` gibt konfigurierte Werte zurück; Defaults greifen bei fehlenden Keys

## Vorbedingungen

- `sdd-cli` installiert
- `pytest` mit `tmp_path`-Fixture
- Kein externer Service nötig

## Ablauf

### TC-01: Evaluator-Defaults korrekt

1. Erstelle `.sdd/config.yaml` ohne `evaluator`-Sektion
2. Lade Konfiguration über `load_config()`
3. Prüfe: `raw.get("evaluator", {}).get("runs_per_scenario", 3) == 3`
4. Prüfe: `raw.get("evaluator", {}).get("pass_threshold", 2) == 2`
5. Prüfe: `raw.get("evaluator", {}).get("cost_alert_usd", 1.00) == 1.00`

### TC-02: Überschriebene Evaluator-Werte

1. Erstelle `config.yaml` mit `evaluator.runs_per_scenario: 5` und `evaluator.pass_threshold: 4`
2. Lade Konfiguration
3. Prüfe: Werte aus Datei werden zurückgegeben

### TC-03: auto_merge_strategy Validierung

1. `auto_merge_strategy: label` → gültiger Wert
2. `auto_merge_strategy: direct` → gültiger Wert
3. Ungültiger Wert: Evaluator-Code verwendet Default-Strategie (kein Absturz)

### TC-04: Orchestrator-Defaults

1. Fehlt `orchestrator`-Sektion → `auto_merge: false`, `max_retries: 3`
2. `orchestrator.auto_merge: true` → korrekt gelesen

### TC-05: maintenance.stale_after_weeks Default

1. Fehlt `maintenance`-Sektion → Default 4 Wochen
2. `maintenance.stale_after_weeks: 8` → korrekt gelesen

## Erwartetes Ergebnis

Alle 5 Test-Cases bestehen. `SddConfig` liest Werte aus `config.yaml` korrekt
aus; fehlende Sektionen führen zu keinem Absturz.

## Verknüpfung mit Contract

- CON-0016 G-02: Evaluator-Defaults (TC-01, TC-02)
- CON-0016 G-03: auto_merge_strategy (TC-03)
- CON-0016 INV-03: pass_threshold ≤ runs_per_scenario (TC-02)

## Hinweise zur Implementierung

```python
from sdd_cli.config import SddConfig, load_config

@pytest.fixture
def cfg_with(tmp_path, yaml_content):
    sdd = tmp_path / ".sdd"
    sdd.mkdir()
    (sdd / "config.yaml").write_text(yaml_content)
    return SddConfig(root=tmp_path, raw=yaml.safe_load(yaml_content) or {})

def test_evaluator_defaults(tmp_path):
    (tmp_path / ".sdd").mkdir()
    (tmp_path / ".sdd" / "config.yaml").write_text("version: '1.0.0'\n")
    cfg = SddConfig(root=tmp_path, raw={})
    ev = cfg.raw.get("evaluator", {})
    assert ev.get("runs_per_scenario", 3) == 3
    assert ev.get("pass_threshold", 2) == 2
```
