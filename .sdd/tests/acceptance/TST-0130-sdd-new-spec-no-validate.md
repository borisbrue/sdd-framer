---
id: TST-0130
spec: SPEC-0029
contract: CON-0111
title: "/sdd-new spec – kein sdd validate nach dem Speichern"
level: acceptance
status: draft
artifact: tests/acceptance/test_tst_0130.py
---

# Test: /sdd-new spec – kein sdd validate nach dem Speichern

## Was wird geprüft

Der `/sdd-new spec`-Skill darf nach dem Speichern einer neuen Spec keinen
`sdd validate`-Aufruf enthalten. Außerdem muss ein Hinweis auf `/sdd-review`
mit der konkreten SPEC-ID ausgegeben werden (CON-0111, INV-01 + INV-02).

## Testfälle

| ID    | FR     | Beschreibung                                                                         | Erwartet                                                          |
|-------|--------|--------------------------------------------------------------------------------------|-------------------------------------------------------------------|
| TC-01 | FR-01  | `sdd validate` taucht nirgends im Spec-Erstellungs-Abschnitt (Schritt 2a) auf       | String `sdd validate` nicht im Spec-Erstellungs-Flow vorhanden   |
| TC-02 | FR-01  | Hinweis auf `/sdd-review SPEC-XXXX` erscheint nach dem Speicher-Block, nicht davor  | `/sdd-review`-Text steht nach dem letzten Speicher-Schritt        |
| TC-03 | INV-02 | Skill bricht ab wenn SPEC-ID nicht ermittelbar                                       | Fehlermeldung statt falscher ID dokumentiert                      |

## Testablauf

```
1. Lese .claude/commands/sdd-new.md
2. Isoliere den Abschnitt für "SPEC erstellen" (## Schritt 2a)
3. TC-01: Prüfe dass "sdd validate" nirgends im Spec-Erstellungs-Abschnitt vorkommt
4. TC-02: Bestimme Position des Speicher-Schritts und Position des "/sdd-review"-Hinweises;
          prüfe dass /sdd-review-Position > Speicher-Position
5. TC-03: Prüfe dass ein Abbruch-/Fehlerfall für nicht ermittelbare SPEC-ID dokumentiert ist
```

## Test-Datei

`tests/acceptance/test_tst_0130.py`
