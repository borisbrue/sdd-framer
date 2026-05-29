---
id: CON-0059
title: "sdd-skill-config-schema"
type: data
format: json-schema
spec: SPEC-0020
version: 0.1.0
status: draft
artifact: ""
tests: [TST-0065]
---

# Contract: SDD Skill – Konfigurationsschema

> **Spec:** SPEC-0018 · **Typ:** Data · **Status:** draft

## Zweck

Definiert das Schema der Skill-Konfiguration in `.sdd/config.yaml` für SDD-Slash-Commands.

## Felder

- `skill.enabled` (boolean): Skill aktiviert/deaktiviert
- `skill.default_model` (string): Standard-Modell für LLM-Aufrufe
- `skill.holdout_isolation` (boolean): Holdout-Verzeichnis isolieren (default: true)
