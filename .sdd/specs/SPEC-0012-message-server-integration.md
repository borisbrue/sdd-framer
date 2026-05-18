---
id: SPEC-0012
title: Nachrichtenserver-Anbindung – Bidirektionale Kommunikation mit dem SDD-System
status: draft
owner: Boris
created: 2026-05-14
updated: 2026-05-14
version: 0.1.0
priority: medium
tags:
- messaging
- mqtt
- websocket
- notifications
- obsidian
- communication
depends_on:
- SPEC-0009
contracts:
  - CON-0079
tests:
  - TST-0110
adrs: []
---
# Nachrichtenserver-Anbindung – Bidirektionale Kommunikation mit dem SDD-System

> **Status:** draft · **Owner:** Boris · **Version:** 0.1.0

## 1. Kontext & Motivation

Das SDD-System ist aktuell rein CLI-getrieben: Aktionen werden synchron ausgeführt,
Rückmeldungen kommen direkt in die Shell. Für asynchrone Workflows und die Integration
mit externen Tools (insbesondere Obsidian, SPEC-0009) ist ein Nachrichtenkanal nötig.

**Konkrete Anwendungsfälle:**
1. **Obsidian→SDD:** Der Entwickler schreibt in einer Obsidian-Notiz eine Anweisung
   (z.B. `@sdd review SPEC-0005`) und schickt sie ab – SDD führt sie aus.
2. **SDD→Entwickler:** SDD benachrichtigt den Entwickler wenn ein LLM-Task abgeschlossen ist
   (Orchestrator fertig, Contract-Review bereit).
3. **Remote-Steuerung:** Ein CI-Job oder ein Mobilgerät kann SDD-Befehle absetzen.

Der Nachrichtenserver soll einfach zu betreiben sein (Selbst-hosting, kein Cloud-Zwang),
auf einem Standard-Protokoll basieren und in die vorhandene Konfigurationsstruktur passen.

## 2. Zielsetzung

**Primärziel:**
Über einen konfigurierten Nachrichtenkanal (MQTT oder WebSocket) können SDD-Befehle
abgesetzt und Ergebnis-Notifications empfangen werden – auch aus Obsidian heraus.

**Erfolgskriterien (messbar):**
- [ ] `sdd daemon` startet einen Worker-Prozess, der auf eingehende Nachrichten lauscht und SDD-Befehle ausführt
- [ ] `sdd send "review SPEC-0005"` sendet einen Befehl über den konfigurierten Kanal
- [ ] Nach Abschluss eines LLM-Tasks wird eine Notification über den Kanal publiziert
- [ ] MQTT (z.B. Mosquitto lokal) und WebSocket werden als Transport-Backends unterstützt
- [ ] Aus Obsidian kann über ein konfigurierbares Callout-Format (`> [!sdd] review SPEC-0005`) ein Befehl abgesetzt werden

**Nicht-Ziele (explizit):**
- Kein eigener MQTT-Broker – das System verbindet sich mit einem externen (z.B. `localhost:1883`)
- Keine End-to-End-Verschlüsselung auf Nachrichtenebene (TLS auf Transport-Ebene optional)
- Kein Authentifizierungssystem (Nutzername/Passwort aus config.yaml, keine OAuth)
- Keine Cloud-Messaging-Dienste (kein AWS SNS, kein Firebase)
- Kein Obsidian-Plugin-Code (nur Konvention: Obsidian-Dateien mit Callouts werden gescannt)

## 3. Transport-Backends

### 3.1 MQTT (empfohlen für lokale Setups)

- **Topics:**
  - `sdd/commands` – eingehende Befehle (SDD lauscht)
  - `sdd/notifications` – ausgehende Notifications (SDD publiziert)
  - `sdd/status` – periodischer Heartbeat (alle 30 s)
- **Payload-Format:** JSON `{"command": "...", "args": {...}, "request_id": "uuid4"}`
- **QoS:** Level 1 (at least once) für Commands; Level 0 für Heartbeat

### 3.2 WebSocket

- **Endpunkt:** `ws://localhost:{port}/sdd/ws` (Port konfigurierbar, Default: 8765)
- **Payload-Format:** identisch zu MQTT
- **Client-Multiplexing:** mehrere gleichzeitige WebSocket-Clients unterstützt

### 3.3 Obsidian-Callout-Konvention

SDD scannt beim `obsidian import` (SPEC-0009) alle Markdown-Dateien im Vault nach
Callout-Blöcken:

```markdown
> [!sdd] review SPEC-0005
> Bitte Contract-Coverage prüfen und fehlende Tests generieren.
```

Erkannte Callouts werden in den Befehlskanal eingespeist (als wäre ein `sdd review-contract`
aufgerufen worden). Nach Ausführung wird der Callout-Block mit einem Ergebnis-Footer ergänzt:

```markdown
> [!sdd-result] ✓ 2026-05-14 14:32
> TST-0041 wurde generiert und mit CON-0007 verknüpft.
```

## 4. Funktionale Anforderungen

### Daemon

- **FR-01:** `sdd daemon [--transport mqtt|websocket]` startet einen Worker-Prozess, der auf
  dem konfigurierten Transport lauscht und eingehende Befehle sequenziell ausführt.
  PID wird in `.sdd/daemon.pid` gespeichert.
- **FR-02:** `sdd daemon --stop` sendet SIGTERM an den laufenden Daemon (via `.sdd/daemon.pid`).
- **FR-03:** Der Daemon führt ausschließlich eine Whitelist erlaubter Befehle aus:
  `review-contract`, `review-pending`, `status-check`, `validate`, `estimate`, `obsidian export/import`.
  Unbekannte Befehle werden mit einer Fehler-Notification beantwortet, nicht ausgeführt.
- **FR-04:** Jede Befehlsausführung loggt Startzeit, Befehl, Ergebnis-Status und Dauer in
  `.sdd/daemon.log`.

### Senden und Empfangen

- **FR-05:** `sdd send "BEFEHL"` publiziert einen Befehl auf `sdd/commands` (MQTT) oder sendet
  ihn an den WebSocket-Endpunkt. Wartet auf Antwort mit Timeout (Default: 60 s).
- **FR-06:** Nach Abschluss eines LLM-Tasks (Evaluator, Orchestrator, Analyzer, review-contract)
  wird automatisch eine Notification publiziert:
  `{"event": "task_complete", "spec_id": "...", "component": "...", "result_summary": "..."}`
- **FR-07:** `sdd listen [--timeout SECS]` gibt eingehende Notifications auf stdout aus
  (nützlich zum Debuggen).

### Konfiguration

- **FR-08:** `.sdd/config.yaml` erhält eine neue Sektion:
  ```yaml
  messaging:
    transport: mqtt         # mqtt | websocket | none (Default: none)
    mqtt:
      host: localhost
      port: 1883
      topic_prefix: sdd     # Basis für Topics (sdd/commands, sdd/notifications)
      # username: ~         # Optional
      # password: ~         # Optional; oder "${ENV_VAR}"
    websocket:
      host: localhost
      port: 8765
    obsidian_callouts: true  # Callout-Scanning beim obsidian import; Default: false
  ```
- **FR-09:** Bei `transport: none` (Default) sind alle Messaging-Befehle disabled und geben
  eine informative Meldung aus. Kein Fehler.

### Obsidian-Callout-Integration

- **FR-10:** `sdd obsidian import` (SPEC-0009) sucht in importierten Vault-Dateien nach
  `[!sdd]`-Callout-Blöcken, wenn `obsidian_callouts: true` konfiguriert ist.
- **FR-11:** Erkannte Callouts werden in die Befehls-Queue des Daemons eingespeist oder –
  wenn kein Daemon läuft – direkt im Import-Prozess ausgeführt.
- **FR-12:** Die Vault-Datei wird nach Ausführung mit dem `[!sdd-result]`-Footer aktualisiert
  (direkt im Vault, kein erneuter Export nötig).

## 5. Nicht-funktionale Anforderungen

| Kategorie     | Anforderung                                                                                       |
|---------------|---------------------------------------------------------------------------------------------------|
| Sicherheit    | Whitelist der erlaubten Befehle (FR-03); kein Shell-Injection-Risiko (Befehle werden als Liste geparst, nicht als Shell-String ausgeführt) |
| Robustheit    | Daemon bleibt bei Befehlsfehler aktiv (kein Crash bei Ausführungsfehler)                         |
| Portabilität  | `paho-mqtt` (MQTT) und `websockets` (WebSocket) als optionale Dependencies                       |
| Observability | Alle eingehenden Befehle und ausgehenden Notifications in `.sdd/daemon.log`                      |
| Testbarkeit   | Transport-Layer ist austauschbar (Interface wie SPEC-0008 LLM-Provider) → vollständig mockbar    |

## 6. Akzeptanzkriterien (Gherkin)

```gherkin
Feature: Nachrichtenserver-Kommunikation

  Scenario: Befehl über MQTT empfangen und ausführen
    Given sdd daemon läuft mit transport: mqtt
    And Mosquitto läuft auf localhost:1883
    When auf Topic sdd/commands publiziert wird: {"command": "validate", "args": {}}
    Then führt der Daemon `sdd validate` aus
    And publiziert das Ergebnis auf sdd/notifications

  Scenario: Unbekannter Befehl wird abgelehnt
    Given sdd daemon läuft
    When auf sdd/commands publiziert wird: {"command": "rm -rf /", "args": {}}
    Then wird keine Befehlsausführung gestartet
    And eine Fehler-Notification mit "Befehl nicht erlaubt" wird publiziert

  Scenario: Obsidian-Callout wird erkannt und ausgeführt
    Given obsidian_callouts: true in config.yaml
    And eine Vault-Datei enthält "> [!sdd] review-contract CON-0007"
    When `sdd obsidian import` ausgeführt wird
    Then wird `sdd review-contract CON-0007` ausgeführt
    And die Vault-Datei wird mit [!sdd-result] Footer aktualisiert

  Scenario: transport: none gibt informative Meldung
    Given messaging.transport: none in config.yaml
    When `sdd send "validate"` ausgeführt wird
    Then wird "Messaging deaktiviert – konfiguriere messaging.transport in .sdd/config.yaml" ausgegeben
    And der Exit-Code ist 0

  Scenario: Daemon-Stop
    Given sdd daemon läuft und .sdd/daemon.pid existiert
    When `sdd daemon --stop` ausgeführt wird
    Then wird der Daemon-Prozess beendet
    And .sdd/daemon.pid wird gelöscht
```

## 7. Edge Cases & Fehlerfälle

- **E-01:** MQTT-Broker nicht erreichbar beim Start → Daemon gibt Fehlermeldung aus, Exit-Code 2.
- **E-02:** MQTT-Verbindung bricht während des Betriebs ab → Daemon versucht Reconnect mit Backoff (1 s, 2 s, 4 s, max 60 s), ohne laufende Aufgaben zu unterbrechen.
- **E-03:** Mehrere gleichzeitige Befehle → Befehle werden sequenziell ausgeführt (Queue), nicht parallel.
- **E-04:** `.sdd/daemon.pid` existiert aber Prozess ist nicht mehr aktiv → `sdd daemon` überschreibt die PID-Datei nach Prüfung.
- **E-05:** Callout-Parsing: malformatierter Callout-Block → Warnung, kein Ausführungsversuch.
- **E-06:** Shell-Injection-Versuch im Befehlsfeld → Whitelist-Prüfung (FR-03) blockt, kein `subprocess.shell=True`.

## 8. Contracts (was wird garantiert)

| Contract-ID | Typ      | Was wird garantiert?                                            |
|-------------|----------|-----------------------------------------------------------------|
| TBD         | data     | JSON-Schema der Command- und Notification-Payloads              |
| TBD         | behavior | Whitelist der erlaubten Befehle und Ablehnungslogik             |
| TBD         | data     | Schema der `messaging`-Konfigurationssektion                    |
| TBD         | behavior | Callout-Parsing-Konvention und Result-Footer-Format             |

## 9. Tests (wie wird verifiziert)

| Test-ID | Level    | Was prüft der Test?                                                                    |
|---------|----------|----------------------------------------------------------------------------------------|
| TBD     | unit     | Whitelist-Prüfung: erlaubte Befehle pass, unbekannte Befehle fail                     |
| TBD     | unit     | Shell-Injection: `; rm -rf /` in Befehlsfeld → abgelehnt                              |
| TBD     | unit     | Callout-Parser: korrekte Extraktion von Befehl und Optionen aus Markdown-Block        |
| TBD     | unit     | Result-Footer-Schreibung in Vault-Datei ohne Body-Überschreibung                      |
| TBD     | unit     | Transport-Interface: Mock-Transport empfängt und bestätigt Befehle                    |
| TBD     | contract | Command/Notification-Payload gegen JSON-Schema validiert                              |
| TBD     | acceptance | Gherkin-Szenarien aus §6 vollständig durchgespielt                                 |

## 10. Offene Fragen

- [ ] Welches MQTT-Broker-Setup wird für die Entwicklungsumgebung empfohlen? Mosquitto via Docker?
- [ ] Soll `sdd daemon` als systemd-Service installierbar sein (`sdd install-service`)?
- [ ] Sollen Notifications auch an Mobile (ntfy.sh, Gotify) weitergeleitet werden können?
- [ ] Wie wird mit sensitiven Daten in Notifications umgegangen (z.B. Spec-Inhalte)?

## 11. Änderungshistorie

| Datum      | Version | Autor | Änderung              |
|------------|---------|-------|-----------------------|
| 2026-05-14 | 0.1.0   | Boris | Initiale Erstellung   |
