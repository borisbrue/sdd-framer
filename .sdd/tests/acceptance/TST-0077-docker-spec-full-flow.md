---
id: TST-0077
project: PRJ-0001
title: "Acceptance Test: Vollständiger Docker-Spec-Flow"
contract: CON-0065
contracts: ["CON-0065", "CON-0066", "CON-0067"]
spec: SPEC-0021
level: acceptance
status: draft
artifact: "tests/acceptance/test_docker_spec_full_flow.py"
---

# Acceptance Test: Vollständiger Docker-Spec-Flow

> **Contracts:** CON-0065, CON-0066, CON-0067 · **Typ:** Acceptance-Test · **Status:** draft

## Abgedeckte Erfolgskriterien (SPEC-0021)

- Projekt automatisch in Container geladen
- Spec wird im Container entwickelt (sdd exec)
- Tests laufen erfolgreich gegen Container
- PR-Dokument wird erstellt mit korrektem Merge-Befehl

## Test-Datei

`tests/acceptance/test_docker_spec_full_flow.py`

## Testablauf

```
1. sdd start SPEC-TEST-001
   → Branch spec/SPEC-TEST-001 erstellt
   → Container sdd-spec-test-001 gestartet

2. sdd exec SPEC-TEST-001 pytest tests/fixtures/sample_test.py -x
   → Tests laufen im Container durch (Exit 0)

3. sdd pr SPEC-TEST-001
   → Gate: Tests grün ✓, validate sauber ✓
   → .sdd/prs/PR-SPEC-TEST-001.md erstellt
   → Merge-Anleitung ausgegeben

4. sdd close SPEC-TEST-001 --delete-branch
   → Container gestoppt + entfernt
   → Branch gelöscht
```

## Akzeptanzkriterien

- [ ] Alle 4 Schritte beenden mit Exit-Code 0
- [ ] PR-Dokument enthält spec_id, branch, test_result: passed, merge_command
- [ ] main-Branch ist nach dem Test unverändert
- [ ] Kein verwaister Container oder Branch nach sdd close
