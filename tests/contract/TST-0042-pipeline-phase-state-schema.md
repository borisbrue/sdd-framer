---
id: TST-0042
title: "Pipeline Phase State JSON Schema"
level: contract
spec: SPEC-0014
contract: CON-0030
status: implemented
framework: pytest
artifact: "tests/contract/test_con_0030.py"
tags: [schema, json-schema, pipeline, gate]
---

# Test: Pipeline Phase State JSON Schema (CON-0030)

> **Level:** contract · **Spec:** SPEC-0014 · **Contract:** CON-0030

## Was wird geprüft?

Valide und invalide Pipeline-Phase-State-Dokumente gegen das JSON-Schema in `contracts/data/pipeline-phase-state.schema.json` validiert.

## Vorbedingungen

- `contracts/data/pipeline-phase-state.schema.json` vorhanden
- `jsonschema` installiert

## Ablauf

1. Minimal-valides Dokument (phase=null) besteht Validierung
2. Vollständiges Dokument mit allen 8 Phasen besteht
3. Alle 9 gültigen Pipeline-Phasen werden akzeptiert
4. `phase_history`-Eintrag ohne `result` → Fehler
5. `result` mit ungültigem Wert → Fehler
6. `override` ohne `reason` → Fehler
7. `override` mit leerem `reason` → Fehler

## Verknüpfung mit Contract

- [x] `pipeline_phase` enum: 9 gültige Phasen + null
- [x] `phase_history[].result` enum: ok/failed
- [x] `override.reason` non-empty string erforderlich
