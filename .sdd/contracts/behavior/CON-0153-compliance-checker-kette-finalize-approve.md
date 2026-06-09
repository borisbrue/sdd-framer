---
id: CON-0153
title: ComplianceChecker-Kette — Enforcement in finalize und spec_approve
type: behavior
format: markdown
spec: SPEC-0041
version: 0.1.0
status: approved
tests:
- TST-0180
- TST-0181
---
`sdd finalize` und `sdd spec approve` rufen die vollständige
`ComplianceChecker`-Kette auf bevor der Status `implemented` bzw.
`spec-approved` gesetzt wird. Bei mindestens einem `ComplianceIssue`
mit `severity: error` wird der Vorgang abgebrochen.

**Garantien**

- `sdd finalize` ruft `FrCoverageChecker`, `TypeAwareTestChecker` und
  `RouteRegistrationChecker` auf bevor `_mark_implemented()` ausgeführt wird.
- `sdd spec approve` ruft dieselbe vollständige Checker-Kette auf
  (`FrCoverageChecker`, `TypeAwareTestChecker`, `RouteRegistrationChecker`)
  bevor die Gate-Phase `spec-approved` markiert wird — kein Command
  prüft weniger als das andere.
- Bei `severity: error` in mindestens einem Issue: Exit-Code 2, keine
  Statusänderung, strukturierte Fehlerliste im Terminal mit konkretem
  Hinweis (welches FR, welcher Befehl hilft).
- Alle Checks können in `.sdd/config.yaml` unter `compliance:` einzeln
  deaktiviert werden; deaktivierte Checks produzieren keine Issues.
- Specs mit `status: implemented` werden nicht erneut geprüft.
