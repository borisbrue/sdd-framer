---
id: SPEC-0072
title: "Versionen der Rollen-Prompts"
status: approved
---
# SPEC-0072: Versionen der Rollen-Prompts

## 1. Kontext
Jede Rollen-Definition trägt eine SemVer-Version (`version: 1.4.2`). `sdd role bump <rolle>
--part minor` erhöht sie, bevor eine geänderte Rolle ausgerollt wird.

## 4. Funktionale Anforderungen

- **FR-01:** `bump(version, part)` erhöht bei `part="major"` die erste Stelle und setzt Minor und
  Patch auf 0, bei `"minor"` die zweite Stelle und setzt Patch auf 0, bei `"patch"` die dritte.
  Das Ergebnis hat immer die Form `MAJOR.MINOR.PATCH` (z. B. `bump("1.9.3", "minor")` →
  `"1.10.0"`). Umgebender Leerraum der Eingabe wird ignoriert.
- **FR-02:** Vorabversionen (`1.2.3-rc.1`): Das Suffix entfällt immer. Bei `"patch"` wird die
  Vorabversion nur freigegeben, die Patch-Stelle also nicht erhöht (`"1.2.3-rc.1"` → `"1.2.3"`);
  `"minor"` und `"major"` erhöhen wie in FR-01.
- **FR-03:** `ValueError` bei einem unbekannten `part` und bei Eingaben, die keine SemVer-Version
  sind: nicht genau drei durch Punkte getrennte Zahlen (`"1.2"`, `"1.2.3.4"`), Präfixe wie
  `"v1.2.3"`, führende Nullen (`"01.2.3"`), negative oder leere Teile.
