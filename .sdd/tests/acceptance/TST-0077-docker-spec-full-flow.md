---
id: TST-0077
project: PRJ-0001
title: "Acceptance Test: Vollständiger Docker-Spec-Flow"
contract: CON-0065
contracts: ["CON-0065", "CON-0066", "CON-0067"]
spec: SPEC-0021
level: acceptance
status: draft
artifact: "tests/unit/test_tst_0077.py"
---

# Acceptance Test: Vollständiger Docker-Spec-Flow

> **Contracts:** CON-0065, CON-0066, CON-0067 · **Typ:** Acceptance-Test · **Status:** draft

## Abgedeckte Erfolgskriterien (SPEC-0021)

- Projekt automatisch in Container geladen
- Tests laufen im Container
- PR-Dokument wird erstellt mit korrektem Merge-Befehl
- Container wird nach grünen Tests entfernt, der Branch bleibt

## Test-Datei

`tests/unit/test_tst_0077.py`

## Testablauf

```
1. sdd start SPEC-0021
   → Branch dev/SPEC-0021 erstellt
   → Container sdd-dev-spec-0021 gestartet

2. podman exec sdd-dev-spec-0021 pytest …   (bzw. docker exec)
   → Tests laufen im Container; im Test wird das Ergebnis gespeichert

3. sdd pr SPEC-0021
   → Gate: Tests grün ✓
   → PR über die PR-Strategie erstellt

4. close() — so, wie die Finalisierung es nach grünen Tests aufruft
   → Container gestoppt + entfernt
   → Branch bleibt erhalten
```

Bis CON-0065 v0.4.0 (#121) liefen Schritt 2 und 4 über `sdd exec` und
`sdd close --delete-branch`. Beide Befehle gibt es seit SPEC-0044 nicht mehr.

## Akzeptanzkriterien

- [ ] Container und Branch folgen CON-0065 INV-01/INV-02
- [ ] PR-Strategie wird mit spec_id und Config aufgerufen
- [ ] Nach `close()` sind Container gestoppt und entfernt, der Branch unberührt
