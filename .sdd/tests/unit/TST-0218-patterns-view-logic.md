---
id: TST-0218
project: PRJ-0001
title: "PatternsView – reine Anzeige-Logik"
level: unit
spec: SPEC-0049
contract: CON-0184
status: planned
framework: vitest
artifact: "web/ui/src/__tests__/patternsView.test.ts"
tags: [ui, web, patterns]
---

# Test: PatternsView – reine Anzeige-Logik

> **Level:** unit · **Spec:** SPEC-0049 · **Contract:** CON-0184 · **Status:** planned

## Was wird geprüft?

Die aus der React-Komponente extrahierte reine Logik (z. B. `patternsViewLogic.ts`), die die
API-Antwort für die Darstellung aufbereitet – ohne DOM (gemäß sdd-implement-Konvention).

## Testfälle

- **test_groups_specs_per_pattern:** mehrere Specs zu einem Pattern werden korrekt gebündelt
  dargestellt.
- **test_empty_state:** leere API-Antwort → Leer-Zustand-Flag/Hinweis (FR-06).
- **test_code_location_link_model:** je Fundstelle wird ein klickbares Link-Modell (file+line)
  für `OpenButton` erzeugt.

## Abdeckung
SPEC-0049 FR-06 (UI-Anzeige der von CON-0184 gelieferten Daten).
