---
id: CON-0037
project: PRJ-0001
title: "Status-Übergangsregeln und Trigger-Bedingungen (SPEC-0010)"
type: behavior
format: markdown
spec: SPEC-0010
version: 0.1.0
status: review
artifact: "contracts/behavior/status-transition-rules.md"
tests:
- TST-0048
- TST-0049
- TST-0050
- TST-0051
- TST-0052
---

# Contract: Status-Übergangsregeln und Trigger-Bedingungen

> **Spec:** SPEC-0010 · **Typ:** Verhalten · **Status:** review

## Zweck

Definiert verbindlich, welche inhaltlichen Änderungen an Specs und Contracts
welche Statusübergänge auslösen und unter welchen Bedingungen diese Übergänge
als „Content-Änderung" gewertet werden.

## Zustandsübergangstabelle

| Auslöser | Von Status | Nach Status | Bedingung |
|---|---|---|---|
| `sdd new spec` / `sdd new contract` | – | `draft` | immer (Spec) |
| `sdd new contract` | – | `review` | immer (Contract) |
| Content-Hash-Änderung erkannt | `approved` | `review` | Body oder FM (außer `updated:`/`status:`) geändert |
| Content-Hash-Änderung erkannt | `implemented` | `review` | wie oben |
| `sdd approve SPEC-XXXX` | `draft` / `review` | `approved` | manuell durch Owner |
| `sdd implement SPEC-XXXX` | `approved` | `implemented` | manuell durch Owner |

## Content-Hash-Definition

Ein **Content-Hash** ist der SHA-256-Wert des Dateiinhalts, berechnet nach
Entfernung aller Zeilen, die mit `status:` oder `updated:` beginnen
(Whitespace vor dem Schlüssel wird ignoriert).

**Invariante:** Reine `status:`- oder `updated:`-Änderungen dürfen **keinen**
Statusübergang auslösen.

## Statusübergang-Rückschritt

Ein Rückschritt von `implemented` → `draft` ist via CLI nicht direkt möglich;
er erfordert eine explizite Begründung via ADR und manuellem Frontmatter-Edit.

## Audit-Pflicht

Jeder Statusübergang, der durch `sdd status-check --fix` oder
`sdd install-hooks`-Hook ausgelöst wird, erzeugt einen Eintrag in
`.sdd/audit.log` im Format:

```
{ISO-8601-Timestamp} {artifact_id} {old_status} → {new_status} [{reason}]
```

Beispiel:
```
2026-05-14T10:00:00Z SPEC-0001 approved → review [content-change-detected]
```
