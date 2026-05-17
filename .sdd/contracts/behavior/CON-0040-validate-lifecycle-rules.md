---
id: CON-0040
project: PRJ-0001
title: "sdd validate – Lifecycle-Fehlerregeln FR-10 und FR-11"
type: behavior
format: markdown
spec: SPEC-0010
version: 0.1.0
status: review
artifact: "contracts/behavior/validate-lifecycle-rules.md"
tests:
- TST-0054
---

# Contract: sdd validate – Lifecycle-Fehlerregeln FR-10 und FR-11

> **Spec:** SPEC-0010 · **Typ:** Verhalten · **Status:** review

## Zweck

Definiert verbindlich, welche neuen Validierungsregeln `sdd validate` ab
SPEC-0010-Implementierung enthält und welche Ausgabe dabei erzeugt wird.

## FR-10: Contract mit Status `review` ohne verknüpften Test → ERROR

**Bedingung:** `status: review` UND `tests: []` (oder `tests`-Feld fehlt)

**Fehlermeldung:**
```
✗ contracts/<subdir>/CON-XXXX-*.md: CON-XXXX hat Status 'review' aber keinen verknüpften Test (FR-10).
```

**Maschinenlesbare Anweisung (`--instruct`-Modus):**
```json
{
  "severity": "error",
  "message": "CON-XXXX hat Status 'review' aber keinen verknüpften Test (FR-10).",
  "instruction": "Run `sdd review-contract CON-XXXX` to auto-generate a test, ..."
}
```

## FR-11: Spec mit Status `approved` aber Contract mit Status `review` → WARNING

**Bedingung:** Spec hat `status: approved` UND mindestens eine ihrer
referenzierten Contract-IDs (`contracts: [...]`) hat `status: review`

**Warnungsmeldung:**
```
⚠ specs/SPEC-XXXX-*.md: SPEC-XXXX hat Status 'approved' aber CON-YYYY ist noch in 'review' (FR-11).
```

## Priorität

- FR-10 schlägt als **error** an (Exit-Code 1 ohne `--strict`)
- FR-11 schlägt als **warning** an (Exit-Code 0 ohne `--strict`, Exit-Code 1 mit `--strict`)
- Beide Regeln sind immer aktiv (kein config.yaml-Toggle)
