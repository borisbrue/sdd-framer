---
id: CON-0128
project: ""
title: "local_agent Konfigurationsschema"
type: data
format: json-schema
spec: SPEC-0036
version: 0.1.0
status: deprecated
artifact: ".sdd/contracts/data/local-agent-config.schema.json"
tests: ["TST-0150"]
deprecated_reason: "mit SPEC-0036 abgelöst: Lokaler Agent und DagScheduler nie angebunden; abgelöst durch die Rollen-Pipeline"
---

# Contract: local_agent Konfigurationsschema

> **Spec:** SPEC-0036 · **Typ:** Daten (JSON Schema) · **Status:** draft

## Zweck

Beschreibt das Schema der `local_agent`-Sektion in `.sdd/config.yaml` (§5 SPEC-0036,
FR-10, FR-11). Definiert Pflichtfelder, optionale Felder und Fallback-Verhalten.

## Invarianten

- **INV-01:** Fehlt die `local_agent`-Sektion vollständig, verhält sich das System
  identisch zu `enabled: false` — kein Fehler, transparenter Fallback auf Cloud-Only.
- **INV-02:** `proxy_url` muss eine gültige HTTP/HTTPS-URL sein (Pflicht wenn `enabled: true`).
- **INV-03:** `context_window` muss eine positive ganze Zahl sein (> 0).
- **INV-04:** `max_parallel_local` und `max_parallel_cloud` müssen ganze Zahlen ≥ 1 sein.
- **INV-05:** `api_key` kann als Env-Var-Referenz `${ENV_VAR}` angegeben werden;
  die Factory löst den Wert via `os.environ` auf.

## Schema-Artifact

Siehe: `local-agent-config.schema.json`
