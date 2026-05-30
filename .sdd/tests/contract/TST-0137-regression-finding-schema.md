---
id: TST-0137
project: ""
title: "Regression Finding Schema"
level: contract
spec: SPEC-0030
contract: CON-0118
status: planned
framework: "pytest+jsonschema"
artifact: "tests/contract/test_tst_0137_regression_finding_schema.py"
tags: []
---

# Test: Regression Finding Schema

> **Level:** contract · **Spec:** SPEC-0030 · **Contract:** CON-0118 · **Status:** planned

## Was wird geprüft?

Ob das JSON-Schema in `.sdd/contracts/data/regression-finding-schema.schema.json`
alle Invarianten aus CON-0118 korrekt durchsetzt: Pflichtfelder, Enum-Werte für
`type`, `severity` und `prefix`, sowie Null-Abweisung.

## Vorbedingungen

- Das Schema-Artifact `.sdd/contracts/data/regression-finding-schema.schema.json` existiert
- `jsonschema`-Bibliothek ist installiert (`pip install jsonschema`)

## Ablauf

1. Gültiges Finding-Objekt (alle 7 Pflichtfelder, gültige Enums) gegen Schema validieren
2. Je eines der 7 Pflichtfelder weglassen → je eine Validierung
3. Je ein Pflichtfeld auf `null` setzen → je eine Validierung
4. `type` auf ungültigen Wert (`"duplicate"`) setzen → Validierung
5. `severity` auf ungültigen Wert (`"critical"`) setzen → Validierung
6. `prefix` auf ungültigen Wert (`"manual"`) setzen → Validierung
7. Stufe-1-Befund mit `"prefix": "rule"` validieren → gültig
8. Stufe-2-Befund mit `"prefix": "llm"` validieren → gültig

## Erwartetes Ergebnis

- Schritt 1: Validierung erfolgreich, kein Fehler
- Schritte 2–3: Jede Variante löst `jsonschema.ValidationError` aus
- Schritt 4: `ValidationError` wegen ungültigem `type`-Wert
- Schritt 5: `ValidationError` wegen ungültigem `severity`-Wert
- Schritt 6: `ValidationError` wegen ungültigem `prefix`-Wert
- Schritte 7–8: Validierung jeweils erfolgreich

## Negativfälle / Edge Cases

- Leeres Objekt `{}` → `ValidationError` (alle Pflichtfelder fehlen)
- Zusätzliches, nicht definiertes Feld → falls Schema `additionalProperties: false` setzt: `ValidationError`; sonst akzeptiert (dokumentieren welches Verhalten erwartet wird)
- `description` als leerer String `""` → prüfen ob Schema `minLength: 1` erzwingt

## Verknüpfung mit Contract

Dieser Test prüft konkret folgende Punkte aus CON-0118:

- [ ] INV-01: Alle 7 Pflichtfelder sind required; fehlendes oder null-Feld → Fehler
- [ ] INV-02: `type` ∈ {overlap, conflict, redundancy} — kein anderer Wert erlaubt
- [ ] INV-03: `severity` ∈ {error, warning, info} — kein anderer Wert erlaubt
- [ ] INV-04: `prefix` ∈ {rule, llm} — kein anderer Wert erlaubt

## Hinweise zur Implementierung

Framework: `pytest` + `jsonschema` (Schema ist JSON Schema Draft 2020-12).
Schema-Pfad: `.sdd/contracts/data/regression-finding-schema.schema.json` — relativ
zum Repo-Root laden.
Parameterisierung: `@pytest.mark.parametrize` für die 7 Pflichtfeld-Varianten
empfohlen, um Test-Duplikation zu vermeiden.
Zusatzprüfung für `additionalProperties: false` erst nach Erstellung des
Schema-Artifacts klären.
