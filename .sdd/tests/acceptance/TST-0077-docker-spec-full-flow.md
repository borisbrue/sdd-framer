---
id: TST-0077
project: PRJ-0001
title: "Acceptance Test: Docker-Spec-Flow"
contract: CON-0065
contracts: ["CON-0065"]
spec: SPEC-0021
level: acceptance
status: draft
artifact: "tests/unit/test_tst_0077.py"
---

# Acceptance Test: Docker-Spec-Flow

> **Contract:** CON-0065 · **Typ:** Acceptance-Test · **Status:** draft

## Abgedeckte Erfolgskriterien (SPEC-0021)

- Projekt automatisch in Container geladen
- Das Testergebnis wird festgehalten und lässt sich wieder lesen
- Container wird nach grünen Tests entfernt, der Branch bleibt

## Test-Datei

`tests/unit/test_tst_0077.py`

## Testablauf

```
1. sdd start SPEC-0021
   → Branch dev/SPEC-0021 erstellt
   → Container sdd-dev-spec-0021 gestartet

2. podman exec sdd-dev-spec-0021 pytest …   (bzw. docker exec)
   → im Test simuliert: Ergebnis wird gespeichert und wieder gelesen

3. close() — so, wie die Finalisierung es nach grünen Tests aufruft
   → Container gestoppt + entfernt
   → Branch bleibt erhalten
```

Bis #121/#123 gehörten `sdd exec`, `sdd pr` und `sdd close --delete-branch` zum
Ablauf. Diese Befehle gibt es seit SPEC-0044 nicht mehr. Den PR legt heute die
Finalisierung an. Das prüfen `test_finalize_push.py` und
`test_finalize_container.py`, CON-0066 ist deprecated.

## Akzeptanzkriterien

- [ ] Container und Branch folgen CON-0065 INV-01/INV-02
- [ ] Das gespeicherte Testergebnis ist wieder lesbar (`passed`, 4/4)
- [ ] Nach `close()` sind Container gestoppt und entfernt, der Branch unberührt
