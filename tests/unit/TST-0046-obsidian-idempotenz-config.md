---
id: TST-0046
project: PRJ-0001
title: "Obsidian Export Idempotenz und Config-Schema-Validierung"
level: unit
spec: SPEC-0009
contract: CON-0034
status: draft
artifact: "tests/unit/test_obsidian.py::TestIdempotenzAndConfig"
---

# Test: Obsidian Export Idempotenz und Config-Validierung

> **Spec:** SPEC-0009 · **Contract:** CON-0034, CON-0036 · **Level:** unit

## Vorbedingungen

- `sdd_cli.obsidian` Modul importierbar
- Temporäres Verzeichnis

## Testfälle

| Test-ID | Szenario | Erwartet |
|---------|----------|----------|
| T-01 | Zweiter Export ohne Änderungen | Identische Vault-Dateien (byte-gleich) |
| T-02 | `vault_path` ist Unterverzeichnis des SDD-Projekts | ValueError (Cycle-Prevention) |
| T-03 | `watch_interval_secs: 0` in config | ValueError (< 1) |
| T-04 | `vault_path` fehlt und kein --vault | RuntimeError / click.UsageError |
| T-05 | `obsidian_config()` gibt Defaults zurück wenn Sektion fehlt | subfolder="SDD", watch_interval=5, auto_wiki_links=True |

## Erwartetes Ergebnis

Idempotenz garantiert; Konfigurationsfehler werden korrekt abgefangen.
