---
id: SPEC-0044
title: "Angebotskalkulation für Großkunden"
status: approved
---

# SPEC-0044: Angebotskalkulation für Großkunden

## 1. Kontext

Der Druckerei-Shop berechnet Angebote für Firmenkunden aus Artikelpreis, Menge und Kundentyp.

## 2. Funktionale Anforderungen

- **FR-01:** Ein Angebot besteht aus Positionen (Artikel, Menge ≥ 1); der Nettobetrag einer
  Position ist Einzelpreis × Menge.
- **FR-02:** Artikelpreise werden aus `preise.csv` gelesen; unbekannte Artikel lehnen das
  Angebot mit Fehlermeldung ab.
- **FR-03:** Staffelrabatt je Position: ab 100 Stück 5 %, ab 500 Stück 10 %, ab 1000 Stück
  15 % (Grenzen jeweils einschließlich).
- **FR-04:** Beträge werden erst am Ende je Position kaufmännisch auf Cent gerundet.
- **FR-05:** Das Angebot wird als JSON mit Positionen, Rabatt je Position und Gesamtsumme
  ausgegeben.
