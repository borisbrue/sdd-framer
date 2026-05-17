---
id: TST-0043
project: PRJ-0001
title: "Obsidian Wiki-Link-Konvertierung: ID → [[slug]] und zurück"
level: unit
spec: SPEC-0009
contract: CON-0034
status: draft
artifact: "tests/unit/test_obsidian.py::TestWikiLinks"
---

# Test: Obsidian Wiki-Link-Konvertierung

> **Spec:** SPEC-0009 · **Contract:** CON-0034 · **Level:** unit

## Vorbedingungen

- `sdd_cli.obsidian` Modul ist importierbar
- Keine Datei-I/O notwendig (pure Funktionen)

## Testfälle

| Test-ID | Eingabe | Erwartete Ausgabe |
|---------|---------|-------------------|
| T-01 | `"Siehe CON-0001"` + slug-map `{CON-0001: "login"}` | `"Siehe [[CON-0001-login]]"` |
| T-02 | `"SPEC-0001 referenziert CON-0001"` | `"[[SPEC-0001-user-login]] referenziert [[CON-0001-login]]"` |
| T-03 | Kein Match im Body | Body unverändert |
| T-04 | `"Siehe [[CON-0001-login]]"` → import | `"Siehe CON-0001"` |
| T-05 | Mehrfach gleiche ID im Body | alle Vorkommen werden konvertiert |
| T-06 | `auto_wiki_links=False` → export | Body unverändert |
| T-07 | Unbekannte ID (kein slug in map) | ID bleibt als Rohtext (kein `[[]]`) |

## Erwartetes Ergebnis

Alle Testfälle bestehen. Keine Exceptions bei normalen Eingaben.
