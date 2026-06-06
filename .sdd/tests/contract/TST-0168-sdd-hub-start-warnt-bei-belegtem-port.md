---
id: TST-0168
title: "sdd hub start gibt Warnung aus wenn Port belegt ist"
level: contract
spec: SPEC-0039
contract: CON-0145
status: planned
framework: pytest
artifact: "tests/contract/test_tst_0168.py"
tags: []
---

# Test: sdd hub start gibt Warnung aus wenn Port belegt ist

## Was wird geprüft?

G-01/G-02/G-03 und INV-01/INV-02 aus CON-0145: Warnung erscheint vor dem
Start wenn Port belegt; kein Hard-Stop; kein Warning wenn Port frei.

## Vorbedingungen

- Ein Socket der Port 4711 belegt (im Test via `socket.bind`)

## Ablauf

1. Port 4711 mit einem Test-Socket belegen
2. `hub_start()`-Logik der Port-Prüfung isoliert aufrufen (kein echter Hub-Start)
3. Ausgabe (stdout/stderr) auf Warnung prüfen
4. Dasselbe mit freiem Port: keine Warnung

## Erwartetes Ergebnis

- Port belegt → Warnung enthält "4711" und "belegt" (oder gleichwertig)
- Port frei → keine Warnung in der Ausgabe

## Negativfälle

- Port belegt, aber `--port 5000` übergeben: keine Warnung (anderer Port geprüft)

## Verknüpfung mit Contract

- [ ] G-01: Warnung erscheint bei belegtem Port
- [ ] G-02: Kein Exit-Code-Fehler durch die Warnung selbst
- [ ] G-03: Kein Warning bei freiem Port
- [ ] INV-01: Warnung erscheint vor uvicorn-Start
- [ ] INV-02: Warnung enthält Port-Nummer
