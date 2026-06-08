---
id: CON-0150
project: ''
title: Offline-Verhalten und Aktionssperre
type: behavior
format: gherkin
spec: SPEC-0040
version: 0.1.0
status: draft
artifact: contracts/behavior/offline-verhalten-und-aktionssperre.feature
tests:
- TST-0173
---
Dieser Contract definiert das beobachtbare Verhalten der PWA bezüglich Offline-Zuständen und der damit verbundenen Aktionssperre für Start- und Stopp-Befehle an Projektserver.

**Zweck**

Die PWA muss zu jeder Zeit transparent kommunizieren, ob eine aktive Verbindung zum Hub besteht. Bei Verbindungsverlust dürfen keine Steuerbefehle abgesetzt oder zwischengespeichert werden. Stattdessen wird der zuletzt bekannte Projektstatus angezeigt und der Nutzer klar über den Offline-Zustand informiert.

**Garantien**

- Solange der Hub nicht erreichbar ist, sind alle Start- und Stopp-Schaltflächen deaktiviert und nicht interaktiv.
- Die PWA zeigt bei Verbindungsverlust den zuletzt erfolgreich abgerufenen Projektstatus zusammen mit einem klar sichtbaren Offline-Indikator und dem Zeitstempel des letzten Abrufs an.
- Keine Aktion wird im Offline-Zustand zwischengespeichert oder verzögert ausgeführt (keine Phantomaktionen).
- Die PWA erkennt Verbindungsänderungen aktiv (Heartbeat oder Auswertung fehlgeschlagener API-Aufrufe) und wechselt selbstständig zwischen Online- und Offline-Modus.
- Kehrt die Hub-Verbindung zurück, werden die Schaltflächen reaktiviert, der aktuelle Status neu abgerufen und der Offline-Indikator entfernt.

**Geltungsbereich**

Dieser Contract gilt für alle Interaktionspunkte der PWA, an denen Projektserver-Aktionen (Start/Stopp) ausgelöst werden können, sowie für die Statusanzeige in der Projektliste. Er deckt die funktionalen Anforderungen FR-05 (Aktionssperre bei fehlender Hub-Verbindung), FR-06 (Offline-Anzeige mit letztem bekannten Status) und FR-08 (Verbindungsstatus überwachen) der übergeordneten Spec ab.