---
id: TST-0181
title: sdd spec approve blockiert bei fehlendem FR-Test
spec: SPEC-0041
contract: CON-0153
level: contract
status: draft
---
## Was wird geprüft?

`sdd spec approve` gibt Exit-Code 2 zurück wenn FRs ohne zugeordneten
Test-ID existieren — die bloße Existenz von Tests reicht nicht.

## Test-Cases

1. **Blockierung bei uncovered FR:** Spec hat Tests, aber FR-03 hat kein
   zugeordnetes `test_ids` in Tasks → Exit-Code 2, Gate-Phase
   `spec-approved` wird nicht markiert

2. **Bisheriger Check bleibt:** Spec ohne jeglichen Test → Exit-Code 2
   (bestehende Prüfung aus SPEC-0014 bleibt erhalten)

3. **Vollständige Abdeckung:** Alle FRs haben test_ids → `spec_approve`
   setzt Gate-Phase `spec-approved` korrekt

4. **compliance.fr_coverage_check: false:** uncovered FR, aber Check
   deaktiviert → `spec_approve` blockiert nicht
