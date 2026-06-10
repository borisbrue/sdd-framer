---
id: TST-0192
project: PRJ-0001
title: "sdd-implement Schritt 5.5 Tier-Loop Inhalt"
level: unit
spec: SPEC-0042
contract: CON-0164
status: passing
framework: pytest
artifact: "tests/unit/test_tst_0192.py"
tags: []
---

# Test: sdd-implement Schritt 5.5 Tier-Loop Inhalt

> **Level:** unit · **Spec:** SPEC-0042 · **Contract:** CON-0164 · **Status:** passing

## Was wird geprüft?

Prüft dass `.claude/commands/sdd-implement.md` den tier-spezifischen Holdout-Loop
gemäß CON-0164 enthält: Schritte 5.5a/5.5b/5.5c mit `--tier`-Flags und
Container-Neustart-Anweisung bei critical-Fehlern.

## Vorbedingungen

- `.claude/commands/sdd-implement.md` existiert

## Ablauf

1. Datei einlesen
2. Prüfe Vorhandensein von "5.5a" / "Critical-Tier"
3. Prüfe Vorhandensein von "5.5b" / "Normal-Tier"
4. Prüfe Vorhandensein von "5.5c" / "Edge-Case-Tier"
5. Prüfe `--tier critical`, `--tier normal`, `--tier edge-case`
6. Prüfe "Container neu starten" im critical-Abschnitt

## Erwartetes Ergebnis

Alle 5 Assertions grün — sdd-implement.md enthält den vollständigen Tier-Loop.

## Verknüpfung mit Contract

- [x] Schritt 5.5a (critical) ist dokumentiert
- [x] Schritt 5.5b (normal) ist dokumentiert
- [x] Schritt 5.5c (edge-case) ist dokumentiert
- [x] `--tier`-Flag für alle drei Tiers vorhanden
- [x] Container-Neustart bei critical-Fehler dokumentiert
