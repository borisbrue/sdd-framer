---
id: SPEC-0103
title: Slugs für Artikeltitel
status: approved
---
# SPEC-0103: Slugs für Artikeltitel

## 4. Funktionale Anforderungen
- **FR-01:** `slugify(titel)` liefert einen Slug aus Kleinbuchstaben, Ziffern und Bindestrichen;
  Folgen anderer Zeichen werden zu genau einem Bindestrich, am Anfang und Ende steht keiner.
- **FR-02:** Deutsche Umlaute und ß werden transliteriert, nicht entfernt: ä→ae, ö→oe, ü→ue,
  Ä→ae, Ö→oe, Ü→ue, ß→ss. Andere Buchstaben mit diakritischen Zeichen verlieren ihr Zeichen
  (é→e).
- **FR-03:** Slugs sind höchstens 60 Zeichen lang; gekürzt wird an einer Bindestrich-Grenze.
