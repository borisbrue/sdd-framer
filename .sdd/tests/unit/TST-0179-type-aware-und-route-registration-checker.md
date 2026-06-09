---
id: TST-0179
title: TypeAwareTestChecker + RouteRegistrationChecker — Tag-basierte Pflichtprüfung
spec: SPEC-0041
contract: CON-0154
level: unit
status: draft
---
## Was wird geprüft?

`TypeAwareTestChecker` und `RouteRegistrationChecker` erkennen fehlende
Integration-Tests bzw. nicht registrierte Routen korrekt.

## Test-Cases TypeAwareTestChecker

1. **Spec mit Tag `webui`, kein contract/integration-Test** →
   `ComplianceIssue(severity="error")`

2. **Spec mit Tag `api`, hat Test unter `tests/contract/`** →
   kein Issue

3. **Spec ohne webui/api-Tag, kein Integration-Test** →
   kein Issue (Checker ist nicht zuständig)

4. **Spec mit Tag `frontend`, Test mit `stufe: integration` im Frontmatter** →
   kein Issue

## Test-Cases RouteRegistrationChecker

5. **Router-Datei angelegt, aber nicht in route_entry_point** →
   `ComplianceIssue(severity="error")`

6. **Router in main.py via `include_router` eingebunden** →
   kein Issue

7. **route_entry_point-Pfad existiert nicht** →
   Check wird stillschweigend übersprungen, kein Issue

8. **compliance.route_registration_check: false in Config** →
   kein Issue unabhängig vom Zustand von main.py
