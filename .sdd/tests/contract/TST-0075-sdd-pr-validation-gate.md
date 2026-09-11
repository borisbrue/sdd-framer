---
id: TST-0075
project: PRJ-0001
title: "Tests: sdd dev pr – Validierungsgatter (entfallen)"
contract: CON-0066
contracts: ["CON-0066"]
spec: SPEC-0021
level: contract
status: skipped
---

# Test: sdd dev pr Validierungsgatter (entfallen)

> **Contract:** CON-0066 (deprecated) · **Typ:** Contract-Test · **Status:** skipped

## Stand

**Entfallen (#123).** `sdd dev pr` ist mit SPEC-0044 weggefallen, CON-0066 ist
deprecated. Die fünf Testfälle prüften `DevContainerManager.pr()`, das seitdem
nur noch Tests erreichten. Mit der Methode ist `tests/unit/test_tst_0075.py`
entfernt worden.

Das Schema kennt kein `deprecated` für Tests, deshalb steht der Status auf
`skipped`. Das Dokument bleibt stehen, weil SPEC-0021 und CON-0066 darauf
verweisen.

## Wo das Verhalten heute geprüft wird

Das PR-Gate liegt in der Finalisierung (siehe CON-0066, v0.3.0):

- `tests/unit/test_finalize_container.py`: rote Tests, kein Aufräumen, kein PR-Pfad
- `tests/unit/test_finalize_push.py`: Push vor dem PR, Reihenfolge
- `tests/unit/test_finalize_build.py`: gescheiterter Build, keine Tests, kein PR

## Ehemalige Testfälle

| ID | Szenario | Erwartetes Ergebnis |
|---|---|---|
| TC-01 | Tests grün + validate sauber | PR-Dokument erstellt, Merge-Anleitung ausgegeben |
| TC-02 | Tests fehlgeschlagen | Gate blockiert, kein PR-Dokument |
| TC-03 | `sdd validate` Fehler | Gate blockiert, Fehler ausgegeben |
| TC-04 | Uncommitted changes | Warnung, Gate fährt fort, PR-Dokument erstellt |
| TC-05 | Kein Test-Ergebnis vorhanden | Gate blockiert mit Hinweis |
