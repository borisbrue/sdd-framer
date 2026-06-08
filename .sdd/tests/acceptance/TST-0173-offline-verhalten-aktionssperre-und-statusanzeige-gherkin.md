---
id: TST-0173
project: ''
title: 'Offline-Verhalten: Aktionssperre und Statusanzeige (Gherkin)'
level: acceptance
spec: SPEC-0040
contract: CON-0150
status: planned
framework: ''
artifact: tests/unit/test_tst_0173.py
tags: []
---
## Was wird geprüft?

Dieser Akzeptanztest stellt sicher, dass die PWA bei Nichterreichbarkeit des Hubs alle interaktiven Steuerelemente (Start/Stopp) zuverlässig sperrt, den zuletzt bekannten Projektstatus weiterhin anzeigt, ein Offline-Banner mit Zeitstempel einblendet und nach Wiederherstellung der Verbindung alle Schaltflächen reaktiviert. Die vier Gherkin-Szenarien aus CON-0150 werden vollständig durchgespielt.

---

## Vorbedingungen

- Die PWA ist in einem Browser (oder PWA-Container) geöffnet und hat erfolgreich mindestens einen Status-Abruf vom Hub abgeschlossen (Online-Baseline vorhanden).
- Mindestens ein Projekt mit Status `running` und eines mit Status `stopped` sind im Hub hinterlegt.
- Die Testumgebung erlaubt es, die Netzwerkverbindung zum Hub gezielt zu unterbrechen (z. B. per Service-Worker-Mock, `cy.intercept` / Playwright `route.abort`, oder Netzwerk-Throttling im Browser-DevTool-Protokoll).
- Der letzte erfolgreiche Abruf-Zeitstempel ist in der Anwendung persistiert (z. B. im `localStorage` oder im App-State).

---

## Ablauf

Die Szenarien folgen den Gherkin-Definitionen aus CON-0150 und werden in dieser Reihenfolge ausgeführt:

```gherkin
Feature: Offline-Verhalten – Aktionssperre und Statusanzeige

  Background:
    Given die PWA ist geöffnet und hat den Hub erfolgreich kontaktiert
    And mindestens ein Projekt hat den Status "running"
    And mindestens ein Projekt hat den Status "stopped"

  Scenario: (1) Start-/Stopp-Schaltflächen werden bei Hub-Unerreichbarkeit deaktiviert
    Given der Hub ist erreichbar und die Schaltflächen sind aktiv
    When die Verbindung zum Hub unterbrochen wird
    Then sind alle Start-Schaltflächen deaktiviert (aria-disabled="true" oder disabled-Attribut gesetzt)
    And sind alle Stopp-Schaltflächen deaktiviert
    And löst ein Klick auf eine deaktivierte Schaltfläche keine API-Anfrage aus

  Scenario: (2) Zuletzt bekannter Status bleibt sichtbar
    Given der Hub war zuletzt erreichbar und hat Projektstatus geliefert
    When die Verbindung zum Hub unterbrochen wird
    Then zeigt die Projektliste weiterhin die zuletzt empfangenen Statuswerte
    And verändert sich kein angezeigter Projektstatus durch den Verbindungsabbruch

  Scenario: (3) Offline-Banner mit Zeitstempel des letzten erfolgreichen Abrufs wird angezeigt
    Given die Verbindung zum Hub wird unterbrochen
    When die PWA den Verbindungsverlust erkennt
    Then ist ein Offline-Banner sichtbar
    And enthält das Banner den Zeitstempel des letzten erfolgreichen Abrufs
    And ist der Zeitstempel maschinenlesbar (ISO 8601) und für den Nutzer lesbar formatiert

  Scenario: (4) Bei Wiederherstellung der Verbindung werden Buttons reaktiviert
    Given die Verbindung zum Hub war unterbrochen und Buttons waren deaktiviert
    When die Verbindung zum Hub wiederhergestellt wird
    And die PWA den Hub erfolgreich kontaktiert hat
    Then sind alle Start-/Stopp-Schaltflächen wieder aktiv
    And ist das Offline-Banner nicht mehr sichtbar
    And zeigt die Projektliste den aktuellen Status vom Hub
```

---

## Erwartetes Ergebnis

| Szenario | Erwartetes Verhalten |
|---|---|
| (1) Aktionssperre | Alle Start/Stopp-Buttons tragen `disabled` bzw. `aria-disabled="true"`; kein Netzwerk-Request wird ausgelöst |
| (2) Letzter Status | Projektstatus-Anzeige ist identisch mit dem letzten Online-Abruf; kein Reset auf einen Standardwert |
| (3) Offline-Banner | Banner ist DOM-präsent und sichtbar; enthält einen validen Zeitstempel im Format `DD.MM.YYYY, HH:MM` (o. ä.) |
| (4) Reaktivierung | Buttons sind wieder interaktiv; Banner verschwindet; Status entspricht dem neuen Hub-Abruf |

---

## Negativfälle / Edge Cases

- **Sofortiger Offline-Start:** Die PWA wird geöffnet, wenn der Hub von Anfang an nicht erreichbar ist. Erwartet: Banner erscheint sofort, Buttons sind von Anfang an deaktiviert, kein Crash oder leerer Zustand.
- **Kurze Verbindungsunterbrechung (< 1 s):** Ein einzelner fehlgeschlagener Heartbeat darf nicht sofort in den Offline-Modus wechseln, sofern CON-0150 eine Toleranzschwelle definiert (z. B. zwei aufeinanderfolgende Fehler). Verhalten gemäß Contract-Definition prüfen.
- **Klick auf disabled Button:** Ein programmatischer oder per Tab + Enter ausgeführter Klick darf keine API-Anfrage absetzen und keinen JS-Fehler erzeugen.
- **Zeitstempel-Formatierung bei langem Offline:** Liegt der letzte Abruf mehr als 24 Stunden zurück, muss der Zeitstempel trotzdem korrekt und vollständig (mit Datum) dargestellt werden.
- **Mehrfacher Verbindungswechsel:** Online → Offline → Online → Offline muss stabil funktionieren, ohne dass sich Banner-Zustände oder Button-Zustände gegenseitig blockieren (State-Management-Regression).

---

## Verknüpfung mit dem Contract

Dieser Test ist die direkte Ausführungsebene von **CON-0150** (Gherkin-Format). Jedes der vier Szenarien entspricht exakt einem Gherkin-Szenario aus dem Contract-Artefakt. Abweichungen in der Schrittformulierung sind nicht zulässig; bei Änderungen an CON-0150 muss TST-0173 synchron aktualisiert werden. Die Testausführung gilt als Verifikation der funktionalen Anforderungen **FR-05** (Aktionssperre) und **FR-06** (Offline-Anzeige) aus der übergeordneten Spec.

---

## Hinweise zur Implementierung

**Framework & Tools:**

- **Playwright** (empfohlen) oder **Cypress** als End-to-End-Testrunner; beide unterstützen netzwerkseitige Interception ohne Browser-Neustart.
- Netzwerk-Mock: `page.route('**/api/**', route => route.abort())` (Playwright) bzw. `cy.intercept` mit `{ forceNetworkError: true }` (Cypress) simulieren den Hub-Ausfall, ohne die Testumgebung zu verändern.
- **Accessibility-Check:** `disabled`-Attribut und `aria-disabled` sind getrennt zu prüfen — beides muss gesetzt sein, um Screen-Reader-Kompatibilität sicherzustellen (`expect(button).toBeDisabled()` + `expect(button).toHaveAttribute('aria-disabled', 'true')`).
- **Zeitstempel-Assertion:** Den Zeitstempel vor der Verbindungsunterbrechung auslesen (`localStorage.getItem('lastFetchedAt')` o. ä.) und nach Erscheinen des Banners mit dem angezeigten Wert vergleichen.
- **Retry-Logik:** Falls die PWA einen Heartbeat-Mechanismus mit Toleranzschwelle implementiert, muss der Test die entsprechende Wartezeit abdecken (z. B. `waitForTimeout` oder Polling auf das Banner-Element).
- **CI-Hinweis:** Tests in einer Umgebung mit deterministischer Netzwerkkontrolle ausführen (kein echtes Hub-Netzwerk); Playwright-`--project=chromium` genügt für Akzeptanztests auf dieser Ebene.