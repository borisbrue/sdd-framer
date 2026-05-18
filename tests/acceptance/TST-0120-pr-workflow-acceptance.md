---
id: TST-0120
title: "PR-Workflow End-to-End (Acceptance)"
level: acceptance
spec: SPEC-0026
contract: CON-0101
status: draft
---

# TST-0120: PR-Workflow End-to-End

## Zu prüfendes Verhalten

Der `SddOrchestrator` führt den vollständigen PR-Workflow gemäß CON-0101 aus:
Branch → Commits → PR → Tests → Merge → Spec-Update → Cleanup.

## Voraussetzungen

- Git-Repo mit main-Branch
- Mindestens ein Task im Status committed
- Mock für Test-Suite (simuliert pass/fail)
- Mock für GitHub/Gitea PR-API

## Testfälle

- T01: Alle Tasks committed → Branch existiert, PR wird erstellt, Tests grün → Merge → status=implemented
- T02: Gemischte Tasks (committed + blocked) → PR wird erstellt, PR-Body listet blockierte Tasks, kein Auto-Merge
- T03: Nur blockierte Tasks → kein PR wird erstellt (INV-04), Fehlermeldung ausgegeben
- T04: Test-Suite schlägt fehl → kein Merge (INV-02), Status bleibt "in-progress"
- T05: Nach Merge → alle Container des Specs entfernt (CON-0099)
- T06: Nach Merge → Spec-Status == "implemented" (INV-03: nicht vorher)
- T07: Branch `spec/SPEC-XXXX` existiert genau einmal (INV-01)
- T08: Jeder committed Task hat genau einen Commit auf dem Branch
