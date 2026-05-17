---
id: CON-0015
project: ""
title: "UI Theming – Theme-Auswahl und Persistenz"
type: behavior
format: gherkin
spec: SPEC-0003
version: 0.2.0
status: active
artifact: "contracts/behavior/ui-theming.feature"
tests: ["TST-0014"]
---

# Contract: UI Theming – Theme-Auswahl und Persistenz

> **Spec:** SPEC-0003 · **Typ:** Verhalten (Gherkin) · **Status:** active

## Zweck

Definiert das beobachtbare Verhalten der Theme-Auswahl: welche Themes
verfügbar sind, wie der User zwischen ihnen wechselt, wie die Wahl persistiert
wird und dass immer genau ein Theme aktiv ist.

## Garantien

Die im Artifact (`contracts/behavior/ui-theming.feature`) hinterlegten
Szenarien sind **ausführbare Spezifikation**. Jedes Szenario MUSS durch einen
automatisierten Test abgedeckt sein.

## Invarianten

- **INV-01:** Genau eines der drei Themes ist zu jedem Zeitpunkt aktiv.
- **INV-02:** Die Theme-Wahl überlebt einen Browser-Reload (localStorage).
- **INV-03:** Das Standard-Theme für neue User ist `dark`.
- **INV-04:** Das aktive Theme wird als `data-theme`-Attribut auf `<html>` gesetzt.
- **INV-05:** Alle UI-Farben werden ausschließlich über CSS-Variablen definiert —
  kein Theme-spezifischer Inline-Style in Komponenten.

## Begriffe

| Begriff       | Definition                                                              |
|---------------|-------------------------------------------------------------------------|
| Theme         | Benannter Satz von CSS-Variablen (`dark` = Gruvbox Dark, `light`, `cyberpunk`) |
| aktives Theme | Theme, dessen `data-theme`-Wert aktuell auf `<html>` gesetzt ist       |
| Persistenz    | Speicherung der Theme-Wahl in `localStorage` unter dem Key `sdd-theme` |
| Einstellungsseite | Ansicht in der Web UI, auf der der User das Theme wählen kann      |
