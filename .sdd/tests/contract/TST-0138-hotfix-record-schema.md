---
id: TST-0138
project: ""                # PRJ-XXXX
title: "Hotfix Record Schema"
level: contract
spec: SPEC-0031
contract: CON-0119
status: planned
framework: "pytest+jsonschema"
artifact: "tests/contract/test_tst_0138_hotfix_record_schema.py"
tags: []
---

# Test: Hotfix Record Schema

> **Level:** contract · **Spec:** SPEC-0031 · **Contract:** CON-0119 · **Status:** planned

## Was wird geprüft?

Ob das JSON-Schema in `.sdd/contracts/data/hotfix-record-schema.schema.json`
alle 5 Invarianten aus CON-0119 korrekt durchsetzt: Pflichtfelder, Status-Enum,
ID-Format, commit-Feld-Semantik und additionalProperties-Sperre.

## Vorbedingungen

- Schema-Artifact `.sdd/contracts/data/hotfix-record-schema.schema.json` existiert
- `jsonschema`-Bibliothek ist installiert

## Ablauf

1. Gültigen offenen Record (alle Felder, `status: open`, `commit: ""`) validieren
2. Gültigen abgeschlossenen Record (`status: done`, `commit`: 40-Zeichen-Hash) validieren
3. Je eines der 5 Pflichtfelder weglassen → je eine Validierung
4. `status` auf ungültigen Wert (`"fixed"`) setzen → Validierung
5. `id` mit falschem Format (`"HF-1"`, `"hotfix-0001"`) setzen → Validierung
6. `commit` auf `null` setzen → Validierung
7. `commit` nicht-leer bei `status: open` → prüfen ob Schema dies ablehnt
8. Extra-Feld (`"priority": "high"`) hinzufügen → Validierung

## Erwartetes Ergebnis

- Schritte 1–2: Validierung erfolgreich
- Schritt 3: Jede Variante → `ValidationError`
- Schritt 4: `ValidationError` wegen ungültigem Status-Wert
- Schritt 5: `ValidationError` wegen ID-Format-Verletzung
- Schritt 6: `ValidationError` wegen null-commit
- Schritt 7: `ValidationError` falls Schema `commit: ""` bei `open` erzwingt (sonst dokumentieren)
- Schritt 8: `ValidationError` wegen `additionalProperties: false`

## Negativfälle / Edge Cases

- Leeres Objekt `{}` → `ValidationError`
- `created` kein ISO-8601-Timestamp → `ValidationError` (falls Schema Format-Validierung aktiviert)
- `id` mit 3- oder 5-stelliger Zahl → `ValidationError`

## Verknüpfung mit Contract

Dieser Test prüft konkret folgende Punkte aus CON-0119:

- [ ] INV-01: Alle 5 Pflichtfelder required; fehlendes Feld → Fehler
- [ ] INV-02: `status` ∈ {open, done, aborted} — kein anderer Wert erlaubt
- [ ] INV-03: `id` Format HF-XXXX (4-stellig) durchgesetzt
- [ ] INV-04: `commit` leer bei open; 40-Zeichen-Hash bei done
- [ ] INV-05: Extra-Felder → Fehler (additionalProperties: false)

## Hinweise zur Implementierung

Framework: `pytest` + `jsonschema` (JSON Schema Draft 2020-12).
`@pytest.mark.parametrize` für die 5 Pflichtfeld-Varianten empfohlen.
Schritt 7 (commit nicht-leer bei open) erfordert ggf. `if/then`-Konstrukt im Schema.
