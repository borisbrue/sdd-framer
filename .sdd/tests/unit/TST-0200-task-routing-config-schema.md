---
id: TST-0200
project: PRJ-0001
title: "task_routing Konfigurationsschema – Defaults, Validation, SPEC-0008-Integration"
level: unit
spec: SPEC-0045
contract: CON-0174
status: draft
framework: pytest
artifact: "tests/unit/test_tst_0200.py"
tags:
  - task-routing
  - config
  - schema
  - spec-0008
---

# Test: task_routing Konfigurationsschema

> **Level:** unit · **Spec:** SPEC-0045 · **Contract:** CON-0174

## Was wird geprüft?

Prüft das Konfigurationsschema: Defaults, Pflichtfelder, Randbedingungen und
Integration mit der SPEC-0008-Factory-Hierarchie.

## Vorbedingungen

- `load_task_routing_config(raw_config)` aus `tool/sdd_cli/task_routing/config.py`
  existiert
- `get_completion_provider(config, "local_llm")` aus SPEC-0008 ist nutzbar

## Ablauf

1. Verschiedene `config.yaml`-Varianten als dict instanziieren
2. `load_task_routing_config()` aufrufen
3. Zurückgegebene Config und Fehler prüfen

## Verknüpfung mit Contract (CON-0174)

- [x] INV-01: enabled=true ohne llm.local_llm → verhält sich wie enabled=false
- [x] INV-02: fehlender task_routing-Block → alle Defaults korrekt
- [x] INV-03: complexity_threshold außerhalb 0–100 → ValueError
- [x] INV-04: llm.local_llm.provider nur openai-compat in v0.1.0
- [x] INV-05: llm.local_llm erbt fehlende Felder vom llm.completion-Default (SPEC-0008)
