---
id: CON-0036
project: PRJ-0001
title: "Obsidian Config Schema – obsidian-Sektion in config.yaml"
type: data
format: json-schema
spec: SPEC-0009
version: 0.1.0
status: draft
artifact: "contracts/data/obsidian-config.schema.json"
tests: ["TST-0046"]
---

# Contract: Obsidian Config Schema

> **Spec:** SPEC-0009 · **Typ:** Daten (JSON Schema) · **Status:** draft

## Zweck

Definiert das Schema der `obsidian:`-Sektion in `.sdd/config.yaml`.
Konsumenten: `sdd obsidian export`, `sdd obsidian import`, `sdd obsidian watch`.

## Invarianten

- **INV-01:** `vault_path` ist ein Pflichtfeld wenn kein `--vault`-Flag
  übergeben wird. Darf nicht leer sein.
- **INV-02:** `subfolder` ist optional; Default `"SDD"`.
- **INV-03:** `watch_interval_secs` ist optional; Default `5`; muss ≥ 1 sein.
- **INV-04:** `auto_wiki_links` ist optional; Default `true`.

## Schema (kompakt)

```yaml
obsidian:
  vault_path: "~/Documents/MyVault"   # Pflicht ohne --vault
  subfolder: "SDD"                    # Optional; Default "SDD"
  watch_interval_secs: 5              # Optional; Default 5; min 1
  auto_wiki_links: true               # Optional; Default true
```

## Feldspezifikation

| Feld                  | Typ    | Pflicht | Default | Constraint  |
|-----------------------|--------|---------|---------|-------------|
| `vault_path`          | string | nein*   | —       | nicht leer  |
| `subfolder`           | string | nein    | `"SDD"` | nicht leer  |
| `watch_interval_secs` | int    | nein    | `5`     | ≥ 1         |
| `auto_wiki_links`     | bool   | nein    | `true`  | —           |

\* Pflicht wenn kein `--vault`-Flag übergeben wird (CLI-Validierung, nicht Schema).
