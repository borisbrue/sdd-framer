---
id: CON-0119
project: ""                # PRJ-XXXX
title: "Hotfix Record Schema"
type: data
format: json-schema
spec: SPEC-0031
version: 0.2.0
status: approved
artifact: ".sdd/contracts/data/hotfix-record-schema.schema.json"
tests: ["TST-0138"]
---

# Contract: Hotfix Record Schema

> **Spec:** SPEC-0031 · **Typ:** Daten (JSON Schema) · **Status:** approved

## Zweck

Beschreibt das Datenschema eines Hotfix-Records, der unter `.sdd/hotfixes/HF-XXXX.md`
gespeichert wird (FR-01/FR-02). Dient als Single Source of Truth für den Status eines
Hotfixes und wird von `sdd hotfix finalize` und `sdd hotfix list` gelesen.

## Invarianten

- **INV-01:** Pflichtfelder: `id`, `description`, `status`, `created`, `commit` — kein Feld darf fehlen oder `null` sein.
- **INV-02:** `status` ∈ {`open`, `done`, `aborted`} — kein anderer Wert erlaubt.
- **INV-03:** `id` muss dem Format `HF-XXXX` entsprechen (4-stellige Zahl, nullaufgefüllt).
- **INV-04:** `commit` ist ein leerer String (`""`) solange `status == open`; bei `status == done` enthält es den vollständigen 40-Zeichen-Git-Commit-Hash.
- **INV-05:** Ein Record darf keine zusätzlichen Felder enthalten (`additionalProperties: false`).
- **INV-06:** `created` ist ein Datum (`YYYY-MM-DD`) oder ein UTC-Zeitstempel
  (`YYYY-MM-DDTHH:MM:SSZ`). Records aus der Zeit vor #132 (`commit: null` bei `open`,
  7-stelliger Kurzhash bei `done`) verletzen INV-01/INV-04, bleiben aber lesbar: `sdd hotfix
  list` und `sdd status` zeigen sie unverändert. Neu geschriebene Records erfüllen INV-01 bis
  INV-05. Die Anzeige kürzt jeden Hash auf 7 Zeichen.

## Beispiele

**Gültig (offen):**
```json
{
  "id": "HF-0001",
  "description": "Falscher Defaultwert in sdd validate --strict",
  "status": "open",
  "created": "2026-05-30T10:10:19Z",
  "commit": ""
}
```

**Gültig (abgeschlossen):**
```json
{
  "id": "HF-0001",
  "description": "Falscher Defaultwert in sdd validate --strict",
  "status": "done",
  "created": "2026-05-30T10:10:19Z",
  "commit": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"
}
```

**Ungültig (und warum):**
```json
{
  "id": "HF-0001",
  "status": "fixed",
  "commit": null
}
```
→ Verstößt gegen INV-01 (`description`, `created` fehlen), INV-02 (`"fixed"` kein gültiger Status), INV-04 (`commit` darf nicht `null` sein).

## Validierung

- Schema unter `.sdd/contracts/data/hotfix-record-schema.schema.json` (JSON Schema Draft 2020-12)
- Validatoren je nach Sprache: `ajv` (JS), `jsonschema` (Python), etc.

## Änderungshistorie

| Datum      | Version | Änderung |
|------------|---------|----------|
| 2026-10-04 | 0.2.0   | Schema-Datei angelegt, INV-06 (Format von `created`, alte Records lesbar); Code an INV-01/INV-04 angeglichen (#132) |
