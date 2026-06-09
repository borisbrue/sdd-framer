---
id: CON-0161
project: PRJ-0001
title: "sdd evaluate --tier CLI-Interface"
type: api
format: markdown
spec: SPEC-0042
version: 0.1.0
status: approved
artifact: "contracts/api/evaluate-tier-flag.md"
tests: ["TST-0189"]
---

# Contract: sdd evaluate --tier CLI-Interface

> **Spec:** SPEC-0042 · **Typ:** API · **Status:** draft

## Zweck

Definiert das CLI-Interface für das neue `--tier`-Flag des `sdd evaluate`-Befehls
sowie die Exit-Code-Semantik.

## Command-Signatur

```
sdd evaluate [--base-url URL] [--spec SPEC-ID] [--tier TIER] [--output-json]
             [--smoke] [--hol-ids HOL-ID ...]
```

### Neues Flag: `--tier`

| Parameter    | Typ    | Werte                          | Default |
|--------------|--------|--------------------------------|---------|
| `--tier`     | enum   | `critical`, `normal`, `edge-case` | (nicht gesetzt = alle Tiers) |

**Semantik:**
- Wenn `--tier` gesetzt: nur Holdouts dieser Priorität werden ausgeführt.
  Fail-Fast-Übersprünge aus anderen Tiers entfallen.
- Wenn nicht gesetzt: bisheriges Verhalten (alle Tiers, fail-fast).

### Neues Flag: `--smoke`

| Parameter  | Typ   | Beschreibung                                       |
|------------|-------|----------------------------------------------------|
| `--smoke`  | flag  | Deterministischer Selbsttest ohne HTTP/Container.  |

**Semantik:**
- Ignoriert `--base-url`, `--spec`, `--tier`, `--hol-ids`
- Läuft rein lokal (kein Netzwerk, kein LLM)
- Exit 0 wenn Selbsttest besteht, Exit 1 wenn nicht

## Exit-Codes

| Code | Bedeutung                                                   |
|------|-------------------------------------------------------------|
| 0    | Alle ausgeführten Holdouts bestanden (pass_rate ≥ 0.9)      |
| 1    | Mindestens ein Holdout fehlgeschlagen oder Smoke-Test failed |

## Kombinationsregeln

| Kombination                | Verhalten                                         |
|----------------------------|---------------------------------------------------|
| `--smoke` + beliebige Flags | `--smoke` hat Vorrang; andere Flags werden ignoriert |
| `--tier` + `--hol-ids`     | `--hol-ids` hat Vorrang; `--tier` wird ignoriert + Warning |
| `--tier` ohne Matches      | Exit 0; Meldung "0 Holdouts für tier=X gefunden"  |

## Invarianten

- `--tier` verändert nicht die interne Sortierung (PRIORITY_ORDER bleibt)
- `--tier` erzeugt keinen Container-Start (kein implizites `--start-container`)
- Fehlermeldungen gehen auf stderr, Report-Output auf stdout
