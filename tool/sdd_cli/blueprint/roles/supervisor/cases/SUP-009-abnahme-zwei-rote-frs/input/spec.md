---
id: SPEC-0106
title: Adressbuch-Export
status: in-progress
---
# SPEC-0106: Adressbuch-Export

## 4. Funktionale Anforderungen
- **FR-01:** `lese_kontakte(pfad)` liest eine CSV-Datei mit Kopfzeile `name,email,telefon`.
- **FR-02:** Als Trennzeichen sind Komma und Semikolon zulässig; es wird an der Kopfzeile erkannt.
- **FR-03:** Kontakte ohne gültige E-Mail-Adresse werden verworfen und im Protokoll gezählt.
- **FR-04:** `exportiere_vcard(kontakte, ziel)` schreibt eine vCard-Datei in UTF-8, Umlaute bleiben
  erhalten.
- **FR-05:** `adressbuch export <csv> <vcf>` verbindet Einlesen, Prüfen und Export und endet bei
  Fehlern mit Exit-Code 2.
