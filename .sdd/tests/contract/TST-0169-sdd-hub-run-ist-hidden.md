---
id: TST-0169
title: "sdd hub run erscheint nicht in sdd hub --help"
level: contract
spec: SPEC-0039
contract: CON-0146
status: planned
framework: pytest
artifact: "tests/contract/test_tst_0169.py"
tags: []
---

# Test: sdd hub run erscheint nicht in sdd hub --help

## Was wird geprüft?

G-01/G-02/G-03 und INV-01 aus CON-0146: `run` fehlt in der Help-Ausgabe;
`sdd hub run --help` funktioniert trotzdem; hidden via Click-Flag.

## Vorbedingungen

- Click-App aus `main.py` importierbar

## Ablauf

1. `sdd hub --help` aufrufen (CliRunner), prüfen dass "run" nicht in Commands
2. `sdd hub run --help` aufrufen, prüfen dass Hilfe erscheint (Exit 0)
3. Click-Kommando-Objekt direkt prüfen: `hidden=True` gesetzt

## Erwartetes Ergebnis

- `sdd hub --help` enthält "run" nicht
- `sdd hub run --help` gibt Exit 0 zurück
- `hub_run.hidden == True`

## Negativfälle

- `start` muss in `sdd hub --help` sichtbar sein (Regression-Schutz)

## Verknüpfung mit Contract

- [ ] G-01: `run` nicht in `sdd hub --help`
- [ ] G-02: `sdd hub run --help` → Exit 0
- [ ] G-03: `sdd hub run` startet hub/app.py (funktional äquivalent zu start)
- [ ] INV-01: hidden=True im Click-Objekt
