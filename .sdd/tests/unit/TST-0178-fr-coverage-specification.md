---
id: TST-0178
title: FrCoverageSpecification — covered/uncovered Fixtures
spec: SPEC-0041
contract: CON-0152
level: unit
status: draft
---
## Was wird geprüft?

`FrCoverageSpecification.is_satisfied_by()` klassifiziert FRs korrekt als
covered oder uncovered anhand von Task-Definitionen und fr_test_map.

## Test-Cases

1. **Happy Path:** Spec mit FR-01 bis FR-03, alle Tasks haben passendes FR
   in `description` und nicht-leere `test_ids` → `uncovered == []`

2. **Fehlender Test:** FR-05 existiert im Spec-Text, kein Task referenziert
   es mit `test_ids` → `uncovered == ["FR-05"]`

3. **fr_test_map Override:** FR-05 ist in `spec.frontmatter.fr_test_map`
   explizit auf `TST-0099` gemappt, kein Task nötig → `covered`

4. **implemented-Spec wird übersprungen:** Spec mit `status: implemented`
   und ungedecktem FR → `is_satisfied_by` gibt leeres Result zurück (kein
   Enforcement)

5. **FR außerhalb des Abschnitts:** FR-01 nur in Abschnitt „Kontext"
   erwähnt, nicht in „Funktionale Anforderungen" → wird nicht extrahiert,
   kein Issue

6. **Leere Task-Liste:** Spec hat FR-01, Tasks-Liste ist leer →
   `uncovered == ["FR-01"]`
