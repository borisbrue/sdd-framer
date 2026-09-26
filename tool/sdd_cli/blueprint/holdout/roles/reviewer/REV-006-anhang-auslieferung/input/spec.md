---
id: SPEC-0007
title: "Anhänge an Belegen"
status: approved
---

# SPEC-0007: Anhänge an Belegen

## 1. Kontext

Das Belegarchiv speichert Rechnungen mehrerer Mandanten. Anhänge (PDF, Bilder) liegen im
Dateisystem unter `<ablage>/<mandant>/<dateiname>`. Die Mandanten-ID stammt aus dem
angemeldeten Benutzer, der Dateiname aus der URL `GET /belege/anhang/<name>`.

## 2. Funktionale Anforderungen

- **FR-01:** Hochgeladene Anhänge werden unter ihrem bereinigten Dateinamen im Verzeichnis des
  Mandanten abgelegt (bereits umgesetzt, SPEC-0006).
- **FR-02:** `lade_anhang(ablage, mandant, name)` liefert Inhalt und MIME-Typ eines Anhangs aus
  dem Verzeichnis des Mandanten. Ein Benutzer darf unter keinen Umständen Dateien außerhalb
  seines Mandantenverzeichnisses erhalten: Namen mit Pfadanteilen (`/`, `\`, `..`), absolute
  Pfade und Namen, die mit `.` beginnen, werden mit `UngueltigerName` (HTTP 400) abgewiesen.
  Unbekannte Namen ergeben `NichtGefunden` (HTTP 404).
- **FR-03:** Anhänge über 20 MiB werden nicht ausgeliefert (`UngueltigerName`, HTTP 400).

## 3. Nicht-funktionale Anforderungen

- Sicherheitsrelevanter Code (Mandantentrennung) braucht Tests für die Abweisungsfälle.
