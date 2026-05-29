---
id: TST-0131
spec: SPEC-0029
contract: CON-0112
title: "/sdd-review – Alle drei Review-Schritte dokumentiert (SOLID + Pattern + Regression)"
level: acceptance
status: draft
artifact: tests/acceptance/test_tst_0131.py
---

# Test: /sdd-review – Dreistufiger Review-Flow im Skill dokumentiert

## Was wird geprüft

Der `/sdd-review`-Skill muss alle drei Unterschritte enthalten:
`sdd solid-check`, `sdd pattern-suggest` und `sdd regression-check`.
Die Reihenfolge muss SOLID → Pattern → Regression sein.
Bei fehlendem `sdd regression-check` muss ein `[WARN]`-Hinweis dokumentiert sein (CON-0112).

## Testfälle

| ID    | FR     | Beschreibung                                                              | Erwartet                                                   |
|-------|--------|---------------------------------------------------------------------------|------------------------------------------------------------|
| TC-01 | FR-02  | Skill enthält `sdd solid-check`                                           | String `sdd solid-check` im Skill-Text vorhanden           |
| TC-02 | FR-02  | Skill enthält `sdd pattern-suggest`                                       | String `sdd pattern-suggest` im Skill-Text vorhanden       |
| TC-03 | FR-02  | Skill enthält `sdd regression-check`                                      | String `sdd regression-check` im Skill-Text vorhanden      |
| TC-04 | FR-02  | Reihenfolge ist SOLID → Pattern → Regression                              | Position solid-check < pattern-suggest < regression-check  |
| TC-05 | INV-02 | Skill dokumentiert interaktive Bestätigung für Pattern-Vorschläge         | "Annehmen" oder äquivalente Formulierung vorhanden         |
| TC-06 | INV-03 | Skill dokumentiert Warnung bei error-Severity im Regression-Check         | `error`-Handling + Nutzerentscheidung dokumentiert         |
| TC-07 | CON-0112 | Precondition auf fehlenden `sdd regression-check` mit `[WARN]` dokumentiert | WARN-Hinweis für nicht verfügbaren Befehl vorhanden      |
| TC-08 | INV-01   | Alle drei Schritte sind vorhanden — fehlt einer, schlägt der Test fehl           | Test schlägt fehl wenn solid-check, pattern-suggest oder regression-check fehlt |

## Testablauf

```
1. Lese .claude/commands/sdd-review.md
2. TC-01–03: Prüfe Vorhandensein der drei Befehlsstrings (assert jeder einzeln)
3. TC-04: Bestimme Position jedes Befehls im Text; prüfe aufsteigende Reihenfolge
4. TC-05: Prüfe dass interaktive Bestätigung für Pattern-Vorschläge beschrieben ist
5. TC-06: Prüfe dass error-Severity-Handling im Regression-Abschnitt dokumentiert ist
6. TC-07: Prüfe dass ein [WARN]-Fallback für fehlenden sdd regression-check vorhanden ist
7. TC-08: Kombinierter Vollständigkeits-Assert — schlägt fehl wenn irgendeiner der
          drei Pflichtschritte fehlt (INV-01: kein Schritt darf fehlen)
```

## Test-Datei

`tests/acceptance/test_tst_0131.py`
