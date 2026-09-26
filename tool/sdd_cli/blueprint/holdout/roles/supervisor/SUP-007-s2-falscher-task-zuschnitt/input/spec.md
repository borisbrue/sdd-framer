---
id: SPEC-0027
title: "Umsatzsteuer-ID auf Rechnungen"
status: approved
---

# SPEC-0027: Umsatzsteuer-ID auf Rechnungen

## 1. Kontext

Seit dem Wechsel auf Regelbesteuerung muss jede Rechnung die USt-IdNr. des ausstellenden
Mandanten tragen. Die Stammdaten des Mandanten (`Mandant` in `rechnung/models.py`) kennen das
Feld noch nicht.

## 2. Funktionale Anforderungen

- **FR-01:** Der Mandant erhält das optionale Feld `ust_id` (Format `DE` + 9 Ziffern, wird beim
  Setzen geprüft); die Migration ergänzt die Spalte.
- **FR-02:** Die Fußzeile des Rechnungs-PDFs zeigt „USt-IdNr.: <ust_id>“, wenn das Feld gesetzt
  ist; ist es leer, bricht die Rechnungserstellung mit einer klaren Meldung ab.
- **FR-03:** Die Mandanten-Einstellungsseite erlaubt das Bearbeiten des Felds.
