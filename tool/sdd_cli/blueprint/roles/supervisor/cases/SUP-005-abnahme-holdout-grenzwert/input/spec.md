---
id: SPEC-0105
title: Preisberechnung im Warenkorb
status: in-progress
---
# SPEC-0105: Preisberechnung im Warenkorb

## 4. Funktionale Anforderungen
- **FR-01:** `zwischensumme(positionen)` summiert Menge × Einzelpreis aller Positionen; Beträge
  sind `Decimal` mit zwei Nachkommastellen.
- **FR-02:** Positionen mit Menge ≤ 0 werden mit `ValueError` abgelehnt.
- **FR-03:** Ab einem Warenwert von 100,00 € (einschließlich) gibt es 10 % Rabatt auf die
  Zwischensumme; darunter keinen.
- **FR-04:** `gesamt(positionen)` liefert Zwischensumme abzüglich Rabatt zuzüglich 4,90 €
  Versand; ab 50,00 € Warenwert (nach Rabatt) ist der Versand frei.
