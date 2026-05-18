---
id: TST-XXXX
project: ""                # PRJ-XXXX
title: "<Test-Name>"
level: contract            # unit | integration | contract | acceptance | performance | property
spec: SPEC-XXXX
contract: CON-XXXX
status: planned            # planned | implemented | passing | failing | skipped
framework: ""              # z.B. pytest, vitest, schemathesis, behave – frei wählbar
artifact: "tests/<level>/<name>.test.<ext>"
tags: []
---

# Test: {{title}}

> **Level:** {{level}} · **Spec:** {{spec}} · **Contract:** {{contract}} · **Status:** {{status}}

## Was wird geprüft?

<!-- Welche Aussage der Spec / welche Garantie des Contracts wird hier verifiziert? -->

## Vorbedingungen

- ...

## Ablauf

1. ...
2. ...
3. ...

## Erwartetes Ergebnis

- ...

## Negativfälle / Edge Cases

- ...

## Verknüpfung mit Contract

Dieser Test prüft konkret folgende Punkte aus {{contract}}:

- [ ] ...

## Hinweise zur Implementierung

<!-- Frameworkspezifische Hinweise, Fixtures, Testdaten -->
