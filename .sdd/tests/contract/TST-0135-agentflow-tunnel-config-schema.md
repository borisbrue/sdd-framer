---
id: TST-0135
project: ""
title: "AgentFlow Tunnel Config Schema"
level: contract
spec: SPEC-0032
contract: CON-0116
status: planned
framework: "pytest + jsonschema"
artifact: "tests/contract/test_tunnel_config_schema.py"
tags: []
---

# Test: AgentFlow Tunnel Config Schema

> **Level:** contract · **Spec:** SPEC-0032 · **Contract:** CON-0116 · **Status:** planned

## Was wird geprüft?

Das JSON-Schema aus CON-0116 (`agentflow-tunnel-config-schema.schema.json`) validiert
korrekt gültige und ungültige `tunnel`-Konfigurationen aus `.sdd/config.yaml`.
Alle drei Invarianten (INV-01 HTTPS, INV-02 kein trailing slash,
INV-03 keine zusätzlichen Properties) werden durchgesetzt.

## Vorbedingungen

- `jsonschema`-Bibliothek verfügbar (`pip install jsonschema`)
- Schema-Datei `.sdd/contracts/data/agentflow-tunnel-config-schema.schema.json` vorhanden

## Ablauf

1. Schema aus Datei laden
2. Gültige Instanzen gegen Schema validieren (kein Fehler erwartet)
3. Jede Negativinstanz einzeln validieren (je ein `ValidationError` erwartet)
4. Prüfen dass `additionalProperties` in `tunnel` tatsächlich abgelehnt werden

## Erwartetes Ergebnis

**Gültige Instanzen — kein Fehler:**
- `{"tunnel": {"url": "https://sdd.example.com"}}`
- `{"tunnel": {"url": "https://my-sdd.trycloudflare.com"}}`

**Ungültige Instanzen — `ValidationError` erwartet:**
- `{"tunnel": {"url": "http://sdd.example.com"}}` → INV-01 (kein HTTPS)
- `{"tunnel": {"url": ""}}` → INV-01 (leerer String)
- `{"tunnel": {"url": "https://sdd.example.com/"}}` → INV-02 (trailing slash, pattern-Verletzung)
- `{"tunnel": {"url": "https://ok.com", "extra": "x"}}` → INV-03 (additionalProperties)
- `{"tunnel": {}}` → `url` fehlt (required)
- `{}` → `tunnel` fehlt (required)

## Negativfälle / Edge Cases

- Schema-Datei fehlt → Test schlägt mit `FileNotFoundError` fehl (kein Silentfail)
- `tunnel.url` mit IP + Port `https://192.168.1.1:8000` → gültig (URI-Format)
- `tunnel.url` ohne Schema (`sdd.example.com`) → ungültig (kein `https://`-Prefix)

## Verknüpfung mit Contract

Dieser Test prüft konkret folgende Punkte aus CON-0116:

- [x] INV-01: `url` muss `https://` beginnen — HTTP und leerer String abgelehnt
- [x] INV-02: `url` darf keinen trailing slash haben — Pattern `^https://` + manuelle Prüfung
- [x] INV-03: keine zusätzlichen Properties in `tunnel`
- [x] `url` ist Pflichtfeld im `tunnel`-Objekt
- [x] `tunnel` ist Pflichtfeld im Root-Objekt

## Hinweise zur Implementierung

```python
import json
import pytest
from pathlib import Path
from jsonschema import validate, ValidationError

SCHEMA_PATH = Path(".sdd/contracts/data/agentflow-tunnel-config-schema.schema.json")

@pytest.fixture
def schema():
    return json.loads(SCHEMA_PATH.read_text())

@pytest.mark.parametrize("instance", [
    {"tunnel": {"url": "https://sdd.example.com"}},
    {"tunnel": {"url": "https://my-sdd.trycloudflare.com"}},
    {"tunnel": {"url": "https://192.168.1.1:8000"}},
])
def test_valid_instances(schema, instance):
    validate(instance=instance, schema=schema)  # kein Error erwartet

@pytest.mark.parametrize("instance", [
    {"tunnel": {"url": "http://sdd.example.com"}},
    {"tunnel": {"url": ""}},
    {"tunnel": {"url": "https://sdd.example.com/"}},
    {"tunnel": {"url": "https://ok.com", "extra": "x"}},
    {"tunnel": {}},
    {},
])
def test_invalid_instances(schema, instance):
    with pytest.raises(ValidationError):
        validate(instance=instance, schema=schema)
```
