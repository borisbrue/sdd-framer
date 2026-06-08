---
id: SPEC-0040
title: PWA um Hub erweitern
type: feature
status: implemented
owner: Boris
created: 2026-06-08
updated: '2026-06-08'
version: 0.1.0
priority: medium
tags: []
depends_on: []
contracts:
- CON-0147
- CON-0148
- CON-0149
- CON-0150
- CON-0151
tests:
- TST-0170
- TST-0171
- TST-0172
- TST-0173
- TST-0174
- TST-0175
adrs: []
started_at: '2026-06-08T20:30:01Z'
---
# PWA um Hub erweitern

> **Status:** draft · **Owner:** Boris · **Version:** 0.1.0

## 1. Kontext & Motivation

Die PWA soll eine direkte Verbindung zum Hub aufbauen, um Projekte zu verwalten und Projektserver zu steuern. Konkret soll die PWA bei hinterlegten Projekten immer den aktuellen Projektstatus vom Hub abrufen und bei Bedarf einen Projektserver starten können.

## 2. Zielsetzung
**Primärziel:**
Nutzer können direkt aus der PWA heraus den aktuellen Status ihrer hinterlegten Projekte einsehen sowie Projektserver starten und stoppen — ohne die Hub-Oberfläche öffnen zu müssen.

**Erfolgskriterien (messbar):**
- [ ] Der Projektstatus wird innerhalb von ≤ 2 Sekunden nach dem Öffnen der PWA vom Hub abgerufen und angezeigt.
- [ ] Start- und Stopp-Aktionen lösen eine sichtbare Statusänderung in der PWA innerhalb von ≤ 5 Sekunden aus.
- [ ] Bei Verbindungsverlust zum Hub zeigt die PWA den zuletzt bekannten Status und einen klaren Offline-Hinweis.
- [ ] 100 % der hinterlegten Projekte sind in der Projektliste sichtbar und einzeln steuerbar.
- [ ] Die Aktionen Start/Stopp sind nur ausführbar, wenn der Hub erreichbar ist (keine Phantomaktionen).

**Nicht-Ziele (explizit):**
- Neue Projekte anlegen, konfigurieren oder löschen (nur Steuerung bestehender Projekte)
- Ersetzen der vollständigen Hub-Verwaltungsoberfläche
- Anzeige oder Auswertung von Projekt-Logs und -Metriken
- Verwaltung von Nutzern, Rollen oder Hub-Systemeinstellungen
- Offline-Steuerung von Projektservern ohne aktive Hub-Verbindung
## 3. User Stories
| ID    | Als ...           | möchte ich ...                                                                 | um ...                                                                                      |
|-------|-------------------|--------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------|
| US-01 | Nutzer            | den aktuellen Status aller meiner hinterlegten Projekte in der PWA sehen       | ich ohne Öffnen der Hub-Oberfläche auf einen Blick weiß, welche Projektserver aktiv sind    |
| US-02 | Nutzer            | einen Projektserver direkt aus der PWA starten                                 | ich eine Entwicklungsumgebung schnell hochfahren kann, ohne die Hub-Oberfläche zu öffnen   |
| US-03 | Nutzer            | einen laufenden Projektserver direkt aus der PWA stoppen                       | ich Ressourcen freigeben kann, ohne zur Hub-Oberfläche wechseln zu müssen                  |
| US-04 | Nutzer            | bei fehlender Hub-Verbindung den zuletzt bekannten Status und einen Offline-Hinweis sehen | ich informiert bleibe und keine falschen Annahmen über den tatsächlichen Serverzustand treffe |
| US-05 | Nutzer            | Start- und Stopp-Schaltflächen nur dann bedienen können, wenn der Hub erreichbar ist | keine Aktionen ins Leere laufen und ich stets verlässliches Feedback über das Ergebnis erhalte |
## 4. Funktionale Anforderungen
- **FR-01: Projektstatus abrufen** — Die PWA ruft beim Öffnen sowie periodisch den aktuellen Status aller hinterlegten Projekte über die Hub-API ab und zeigt ihn in der Projektliste an. Der initiale Abruf muss innerhalb von ≤ 2 Sekunden abgeschlossen sein.

- **FR-02: Projektliste darstellen** — Alle im Hub hinterlegten Projekte werden vollständig in einer Liste aufgeführt. Jeder Eintrag zeigt mindestens: Projektname und aktuellen Serverstatus (z. B. `running`, `stopped`, `starting`, `stopping`).

- **FR-03: Projektserver starten** — Für jedes Projekt mit Status `stopped` bietet die PWA eine Schaltfläche zum Starten des Projektservers. Die Aktion wird als API-Aufruf an den Hub übermittelt; eine sichtbare Statusänderung erfolgt innerhalb von ≤ 5 Sekunden.

- **FR-04: Projektserver stoppen** — Für jedes Projekt mit Status `running` bietet die PWA eine Schaltfläche zum Stoppen des Projektservers. Die Aktion wird als API-Aufruf an den Hub übermittelt; eine sichtbare Statusänderung erfolgt innerhalb von ≤ 5 Sekunden.

- **FR-05: Aktionssperre bei fehlender Hub-Verbindung** — Start- und Stopp-Schaltflächen sind deaktiviert (nicht interaktiv), solange der Hub nicht erreichbar ist. Es werden keine Aktionen in die Warteschlange gelegt oder verzögert ausgeführt.

- **FR-06: Offline-Anzeige mit letztem bekannten Status** — Bei Verbindungsverlust zum Hub zeigt die PWA den zuletzt erfolgreich abgerufenen Projektstatus sowie einen klar sichtbaren Offline-Hinweis (z. B. Banner oder Icon mit Zeitstempel des letzten Abrufs).

- **FR-07: Statusaktualisierung nach Aktion** — Nach einer erfolgreichen Start- oder Stopp-Aktion aktualisiert die PWA den angezeigten Status des betroffenen Projekts unmittelbar (optimistisch oder per erneutem Abruf) ohne vollständigen Seitenneuladevorgang.

- **FR-08: Verbindungsstatus überwachen** — Die PWA erkennt aktiv, ob der Hub erreichbar ist (z. B. per Heartbeat oder durch Auswertung fehlgeschlagener API-Aufrufe), und wechselt selbstständig zwischen Online- und Offline-Modus.
## 5. Nicht-funktionale Anforderungen
| Kategorie     | Anforderung |
|---------------|-------------|
| Performance   | Der Projektstatus wird innerhalb von ≤ 2 s nach PWA-Öffnen vom Hub geladen (vgl. Erfolgskriterium). Start-/Stopp-Aktionen spiegeln sich innerhalb von ≤ 5 s in der UI wider. Der initiale PWA-Load (First Contentful Paint) beträgt ≤ 3 s in einem moderaten Netz (4G). Polling- oder Push-Intervall für Statusupdates: ≤ 10 s, um Ressourcen zu schonen. |
| Security      | Alle Anfragen an den Hub laufen ausschließlich über HTTPS/WSS. Auth-Token werden nur im `sessionStorage` oder einem sicheren Cookie gehalten, nie im `localStorage`. Die PWA sendet keine Steuerbefehle ohne gültige, nicht abgelaufene Sitzung. Verbindungsaufbau zum Hub erfordert eine explizite Authentifizierung (Token/OAuth). |
| Accessibility | Die Projektliste und alle Steuerflächen sind vollständig per Tastatur bedienbar. Statusänderungen werden als ARIA-Live-Region angekündigt, sodass Screen-Reader-Nutzer unmittelbar informiert werden. Schaltflächen im deaktivierten Zustand (Hub nicht erreichbar) erhalten `aria-disabled` und einen Tooltip-Text. Farbkontraste entsprechen WCAG 2.1 Level AA (Kontrastverhältnis ≥ 4,5 : 1 für Fließtext). |
| Observability | Verbindungsstatus-Änderungen (online/offline, Auth-Fehler) werden client-seitig geloggt und können im Browser-Konsolenprotokoll nachvollzogen werden. Fehlgeschlagene Start-/Stopp-Aktionen werden mit HTTP-Statuscode und Zeitstempel erfasst. Ein sichtbarer Verbindungsindikator in der UI zeigt jederzeit den aktuellen Hub-Erreichbarkeitsstatus an. |
| Datenschutz   | Es werden keine personenbezogenen Nutzerdaten an Drittdienste übertragen. Projektbezeichnungen und Serverstatus verbleiben ausschließlich im Arbeitsspeicher der Sitzung; es findet kein persistentes Caching sensibler Metadaten statt. Die PWA setzt keine Tracking-Cookies und bindet keine externen Analytics-Bibliotheken ein. |
## 6. Akzeptanzkriterien (Gherkin)
```gherkin
Feature: PWA Hub-Verbindung

  Background:
    Angenommen der Nutzer hat die PWA geöffnet
    Und im Hub sind Projekte hinterlegt

  Szenario: Projektstatus wird beim Öffnen der PWA abgerufen (FR-01, FR-02)
    Angenommen der Hub ist erreichbar
    Wenn die PWA geladen wird
    Dann sind alle hinterlegten Projekte in der Projektliste sichtbar
    Und jeder Eintrag zeigt den aktuellen Serverstatus (z. B. „running" oder „stopped")
    Und der initiale Statusabruf ist innerhalb von 2 Sekunden abgeschlossen

  Szenario: Nutzer startet einen gestoppten Projektserver (FR-03, FR-07)
    Angenommen der Hub ist erreichbar
    Und Projekt „my-app" hat den Status „stopped"
    Wenn der Nutzer die Schaltfläche „Starten" für „my-app" betätigt
    Dann wird ein Start-Aufruf an den Hub gesendet
    Und der angezeigte Status von „my-app" wechselt innerhalb von 5 Sekunden auf „running" oder „starting"
    Und kein vollständiger Seitenneulade erfolgt

  Szenario: Nutzer stoppt einen laufenden Projektserver (FR-04, FR-07)
    Angenommen der Hub ist erreichbar
    Und Projekt „my-app" hat den Status „running"
    Wenn der Nutzer die Schaltfläche „Stoppen" für „my-app" betätigt
    Dann wird ein Stopp-Aufruf an den Hub gesendet
    Und der angezeigte Status von „my-app" wechselt innerhalb von 5 Sekunden auf „stopped" oder „stopping"
    Und kein vollständiger Seitenneulade erfolgt

  Szenario: Aktionsschaltflächen sind bei fehlender Hub-Verbindung deaktiviert (FR-05)
    Angenommen der Hub ist nicht erreichbar
    Wenn die Projektliste angezeigt wird
    Dann sind alle Start- und Stopp-Schaltflächen deaktiviert und nicht interaktiv
    Und es werden keine Aktionen zwischengespeichert oder verzögert ausgeführt

  Szenario: Offline-Anzeige mit zuletzt bekanntem Status (FR-06, FR-08)
    Angenommen die PWA hat den Projektstatus zuletzt um 14:00 Uhr erfolgreich abgerufen
    Wenn die Verbindung zum Hub unterbrochen wird
    Dann zeigt die PWA den zuletzt abgerufenen Status jedes Projekts
    Und ein deutlicher Offline-Hinweis (Banner oder Icon) ist sichtbar
    Und der Zeitstempel des letzten erfolgreichen Abrufs wird angezeigt

  Szenario: PWA wechselt zurück in den Online-Modus nach Wiederverbindung (FR-08)
    Angenommen die PWA befindet sich im Offline-Modus
    Wenn die Verbindung zum Hub wiederhergestellt wird
    Dann verschwindet der Offline-Hinweis
    Und die PWA ruft den aktuellen Projektstatus erneut vom Hub ab
    Und die Start- und Stopp-Schaltflächen sind wieder aktiv
```
## 7. Edge Cases & Fehlerfälle
- **EC-01: Hub beim Start nicht erreichbar** — Die PWA öffnet sich, bevor der Hub antwortet oder während er offline ist. Es sind keine Projektdaten verfügbar; die PWA zeigt einen leeren Zustand mit Offline-Hinweis statt einer leeren Liste ohne Kontext.

- **EC-02: Verbindung bricht während einer laufenden Aktion ab** — Der Hub ist zum Zeitpunkt des Klicks auf Start/Stopp erreichbar, verliert aber die Verbindung bevor die Antwort eintrifft. Der tatsächliche Serverstatus ist unbekannt; die PWA darf keinen optimistischen Endzustand annehmen, sondern muss einen Fehlerhinweis zeigen und beim nächsten Verbindungsaufbau den echten Status neu abrufen.

- **EC-03: Übergangsstatusе `starting` / `stopping` beim Öffnen** — Ein Projektserver befindet sich bereits in einem Übergangszustand. Die PWA zeigt diesen Zustand korrekt an und deaktiviert Start- und Stopp-Schaltflächen, solange der Übergang andauert.

- **EC-04: Schnelles Mehrfachklicken auf Start/Stopp** — Mehrere Klicks innerhalb kurzer Zeit führen nicht zu mehrfachen API-Aufrufen. Die Schaltfläche wird nach dem ersten Klick sofort deaktiviert bis eine Statusänderung bestätigt ist.

- **EC-05: Start-Aktion schlägt serverseitig fehl** — Der Hub nimmt den Aufruf an (HTTP 2xx), der Projektserver startet aber nicht (z. B. Port-Konflikt, fehlende Ressourcen). Der Status bleibt `stopped` oder wechselt auf `error`; die PWA zeigt eine klare Fehlermeldung und setzt keinen optimistischen Endzustand dauerhaft.

- **EC-06: Hub gibt unbekannten Statuswert zurück** — Die Hub-API liefert einen Statuswert, den die PWA nicht kennt (z. B. `crashed`, `paused`). Die PWA rendert ihn als neutralen Unbekannt-Zustand und deaktiviert beide Aktionsschaltflächen.

- **EC-07: Keine Projekte im Hub hinterlegt** — Die API antwortet erfolgreich mit einer leeren Liste. Die PWA zeigt einen aussagekräftigen Leer-Zustand statt einer leeren Liste ohne Erklärung.

- **EC-08: Projekt wird im Hub gelöscht während die PWA offen ist** — Ein Projekt, das zuvor in der Liste war, taucht beim nächsten Poll nicht mehr auf. Die PWA entfernt es stillschweigend aus der Anzeige ohne Fehler.

- **EC-09: Auth-Token läuft während der Session ab** — Polling oder eine Aktion schlägt mit HTTP 401/403 fehl. Die PWA erkennt den Authentifizierungsfehler, unterscheidet ihn von einem allgemeinen Verbindungsfehler und zeigt einen entsprechenden Hinweis (z. B. „Sitzung abgelaufen – bitte neu anmelden").

- **EC-10: Flatterende Verbindung (Intermittent Connectivity)** — Der Hub wechselt in schneller Folge zwischen erreichbar und nicht erreichbar. Die PWA wechselt nicht im Sekundentakt zwischen Online- und Offline-Modus, sondern verwendet eine Entprelllogik (z. B. zwei aufeinanderfolgende fehlgeschlagene Heartbeats bevor Offline-Modus aktiv wird).

- **EC-11: PWA-Start aus Service-Worker-Cache (vollständig offline)** — Die PWA startet ohne Netzwerk aus dem Cache. Zwischengespeicherte Projektdaten werden mit Zeitstempel und Offline-Hinweis angezeigt; es wird kein Abruf simuliert oder ein veralteter Timestamp als „aktuell" dargestellt.

- **EC-12: API-Antwort überschreitet Timeout** — Ein einzelner Statusabruf oder Aktionsaufruf antwortet nicht innerhalb des definierten Timeouts. Die PWA bricht den Request ab, zeigt einen Timeout-Hinweis und versucht beim nächsten regulären Poll-Intervall erneut, anstatt den Request unbegrenzt offen zu halten.
## 8. Contracts (was wird garantiert)

| Contract-ID | Typ | Was wird garantiert? |
|-------------|-----|----------------------|

## 9. Tests (wie wird verifiziert)

| Test-ID  | Level | Was prüft der Test? |
|----------|-------|---------------------|

## 10. Offene Fragen

- [ ]

## 11. Änderungshistorie

| Datum      | Version | Autor | Änderung             |
|------------|---------|-------|----------------------|
| 2026-06-08 | 0.1.0   | Boris | Initiale Erstellung  |
