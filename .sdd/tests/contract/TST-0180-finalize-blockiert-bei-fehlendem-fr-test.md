---
id: TST-0180
title: sdd finalize blockiert bei fehlendem FR-Test
spec: SPEC-0041
contract: CON-0153
level: contract
status: draft
---
## Was wird geprüft?

`sdd finalize` gibt Exit-Code 2 zurück und setzt keinen `implemented`-Status
wenn eine Spec ein FR ohne zugeordneten Test hat.

## Test-Cases

1. **Blockierung bei uncovered FR:** Spec mit FR-01 (kein Task mit test_ids)
   → `sdd finalize` Exit-Code 2, Fehlermeldung enthält „FR-01",
   Spec-Status bleibt unverändert (nicht `implemented`)

2. **Durchlauf bei vollständiger Abdeckung:** Alle FRs haben test_ids,
   alle Tests grün → `sdd finalize` läuft durch, Status wird `implemented`

3. **compliance.fr_coverage_check: false:** FR ohne Test, aber Check
   deaktiviert → `sdd finalize` blockiert nicht, Status wird `implemented`

4. **Fehlermeldung ist handlungsweisend:** Ausgabe enthält konkreten
   `sdd new test`-Befehl als Hinweis
