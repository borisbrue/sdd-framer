---
id: TST-0132
spec: SPEC-0029
contract: CON-0113
title: "/sdd-implement – Vollständiger Auto-Flow im Skill dokumentiert"
level: acceptance
status: draft
artifact: tests/acceptance/test_tst_0132.py
---

# Test: /sdd-implement – Auto-Flow im Skill dokumentiert

## Was wird geprüft

Der `/sdd-implement`-Skill muss den vollständigen Auto-Flow dokumentieren:
`sdd start`, Feature-Branch-Erstellung, `sdd decompose` als Planungsgrundlage,
TDD-Zyklus und `sdd finalize`. Außerdem: expliziter Fehler bei fehlendem Container,
`--skip-container` als Workaround beim 3. Versuch, Holdout-Isolation (CON-0113).

## Testfälle

| ID    | FR/INV | Beschreibung                                                                | Erwartet                                                        |
|-------|--------|-----------------------------------------------------------------------------|-----------------------------------------------------------------|
| TC-01 | FR-06  | Skill dokumentiert automatischen `sdd start`-Aufruf                        | `sdd start` im Skill-Text vorhanden                             |
| TC-02 | FR-07  | Skill dokumentiert Feature-Branch-Erstellung (`feat/SPEC-XXXX`)             | Branch-Erstellung + `feat/` Prefix dokumentiert                 |
| TC-03 | FR-08  | Skill dokumentiert `sdd decompose` als Planungsgrundlage (nicht distribute)  | `sdd decompose` vorhanden; kein `sdd distribute` im selben Kontext |
| TC-04 | FR-09  | Skill dokumentiert `sdd finalize`-Aufruf am Ende                           | `sdd finalize` im Skill-Text vorhanden                          |
| TC-05 | FR-10  | Skill dokumentiert expliziten Fehler wenn kein Container läuft              | Fehlermeldung mit Container-Hinweis dokumentiert                |
| TC-06 | FR-10  | Skill dokumentiert `--skip-container` als Workaround beim 3. Versuch       | `--skip-container` + "3" oder "dritten" im Skill-Text           |
| TC-07 | FR-10  | Skill dokumentiert Warnung bei `--skip-container`-Nutzung                  | Warnung ("⚠" oder "warning") beim Skip-Container-Flow          |
| TC-08 | INV-01 | Skill enthält Holdout-Isolation-Hinweis (`.sdd/holdout/` nie lesen)        | Holdout-Verbot explizit im Skill dokumentiert                   |
| TC-09 | INV-04 | Skill dokumentiert dass decompose nur als Plan genutzt wird (kein distribute) | `distribute` wird nicht von `/sdd-implement` aufgerufen        |
| TC-10 | FR-08  | Skill dokumentiert Fehlerfall bei leerer Decompose-Liste (0 Tasks)           | Fehlermeldung + Flow-Stopp für leere Task-Liste dokumentiert    |

## Testablauf

```
1. Lese .claude/commands/sdd-implement.md
2. TC-01–04: Prüfe Vorhandensein der vier Kern-Schritte als Textstrings
3. TC-05: Prüfe dass Container-Fehler-Handling dokumentiert ist
4. TC-06: Prüfe dass --skip-container beim dritten Versuch dokumentiert ist
5. TC-07: Prüfe dass eine Warnung beim --skip-container-Flow ausgegeben wird
6. TC-08: Prüfe Holdout-Isolations-Klausel (`.sdd/holdout/` oder "NIEMALS")
7. TC-09: Prüfe dass `sdd distribute` nicht im sdd-implement-Flow steht
8. TC-10: Prüfe dass leere Decompose-Liste (0 Tasks) als Fehlerfall dokumentiert ist
```

## Test-Datei

`tests/acceptance/test_tst_0132.py`
