---
id: TST-0014
title: "UI Theming – Theme-Auswahl und Persistenz"
level: acceptance
spec: SPEC-0003
contract: CON-0015
status: planned
framework: "playwright"
artifact: "tests/acceptance/TST-0014-ui-theming.spec.ts"
tags: ["ui", "theming", "localStorage"]
---

# Test: UI Theming – Theme-Auswahl und Persistenz

> **Level:** acceptance · **Spec:** SPEC-0003 · **Contract:** CON-0015 · **Status:** planned

## Was wird geprüft?

Alle fünf Invarianten aus CON-0015:
- INV-01: Genau ein Theme ist zu jedem Zeitpunkt aktiv
- INV-02: Theme-Wahl überlebt Browser-Reload (localStorage)
- INV-03: Standard-Theme für neue User ist `dark`
- INV-04: Aktives Theme wird als `data-theme` auf `<html>` gesetzt
- INV-05: Kein Theme-spezifischer Inline-Style in Komponenten

## Vorbedingungen

- Web-UI läuft unter `http://localhost:5173`
- localStorage ist leer (frische Browser-Session)

## Ablauf

1. Seite öffnen → `html[data-theme]` ist `dark` (INV-03, INV-04)
2. Einstellungsseite aufrufen → drei Theme-Optionen sichtbar (`dark`, `light`, `cyberpunk`)
3. Theme `light` wählen → `html[data-theme]` wechselt auf `light` (INV-01, INV-04)
4. `dark` und `cyberpunk` haben kein `data-theme` mehr (INV-01)
5. Seite neu laden → `html[data-theme]` ist weiterhin `light` (INV-02)
6. DOM-Scan: kein Element hat einen Theme-spezifischen Inline-Style (INV-05)
7. Theme `cyberpunk` wählen → `html[data-theme]` wechselt auf `cyberpunk` (INV-01)
8. Seite neu laden → `html[data-theme]` ist `cyberpunk` (INV-02)
