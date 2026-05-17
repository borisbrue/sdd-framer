---
id: CON-0070
title: "log-streamer"
type: behavior
format: gherkin
spec: SPEC-0022
version: 0.1.0
status: draft
artifact: "contracts/behavior/log-streamer.feature"
tests: [TST-0080]
---

# Contract: log-streamer

> **Spec:** SPEC-0022 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Beschreibt das beobachtbare Verhalten des `LogStreamer` und `LogEventBus`:
Attach/Detach von Container-Logs, Buffer-Verwaltung und WebSocket-Multicast.

## Garantien

- **G-01:** Nach `sdd dev up/start` startet `LogStreamer.attach(spec_id)` automatisch
  wenn `log_stream.enabled: true`.
- **G-02:** Neue Log-Zeilen werden innerhalb von 1 Sekunde an alle verbundenen
  WebSocket-Clients gesendet.
- **G-03:** Bei WebSocket-Verbindungsaufbau werden die letzten `log_stream.max_lines`
  Zeilen aus dem In-Memory-Buffer gesendet, danach Live-Zeilen.
- **G-04:** `LogStreamer.detach(spec_id)` stoppt den Log-Thread sauber (kein
  hängender Prozess nach `sdd dev down/close`).
- **G-05:** N gleichzeitige WebSocket-Clients für denselben `spec_id` empfangen
  alle Zeilen (Multicast via `LogEventBus`).

## Invarianten

- **INV-01:** Der In-Memory-Buffer ist auf `log_stream.max_lines` begrenzt (FIFO).
- **INV-02:** `LogStreamer` läuft in einem eigenen Thread — blockiert nicht den
  API-Server.
- **INV-03:** Ein Disconnect eines Clients stoppt nicht den Log-Stream für andere
  Clients.

## Szenarien

```gherkin
Feature: LogStreamer und LogEventBus

  Background:
    Given log_stream.enabled ist true
    And log_stream.max_lines ist 500

  Scenario: Automatischer Start nach sdd dev up
    Given Container "sdd-dev-spec-0022" wird gestartet
    When "sdd dev up SPEC-0022" erfolgreich abgeschlossen ist
    Then ist LogStreamer für SPEC-0022 aktiv
    And ein Thread liest "docker logs --follow sdd-dev-spec-0022"

  Scenario: Neue Log-Zeile erscheint im WebSocket < 1 s
    Given LogStreamer für SPEC-0022 ist aktiv
    And ein WebSocket-Client ist verbunden auf /ws/logs/SPEC-0022
    When Container "sdd-dev-spec-0022" eine neue Log-Zeile ausgibt
    Then empfängt der WebSocket-Client die Zeile innerhalb von 1 Sekunde

  Scenario: Verbindungsaufbau sendet Buffer-History
    Given LogStreamer hat 200 Zeilen im Buffer für SPEC-0022
    When ein neuer WebSocket-Client sich verbindet auf /ws/logs/SPEC-0022
    Then empfängt der Client zuerst die 200 gespeicherten Zeilen
    And danach neue Zeilen in Echtzeit

  Scenario: Buffer-Limit wird eingehalten
    Given der Buffer für SPEC-0022 enthält 500 Zeilen (max_lines)
    When Container 1 weitere Log-Zeile ausgibt
    Then enthält der Buffer genau 500 Zeilen (älteste wird verworfen)

  Scenario: Multicast an N Clients
    Given 3 WebSocket-Clients sind verbunden auf /ws/logs/SPEC-0022
    When Container eine neue Log-Zeile ausgibt
    Then empfangen alle 3 Clients die Zeile

  Scenario: Client-Disconnect stoppt nicht den Stream
    Given 2 WebSocket-Clients sind verbunden
    When Client-1 die Verbindung trennt
    Then bleibt LogStreamer aktiv
    And Client-2 empfängt weiterhin Log-Zeilen

  Scenario: sdd dev down stoppt LogStreamer sauber
    Given LogStreamer für SPEC-0022 ist aktiv
    When "sdd dev down SPEC-0022" ausgeführt wird
    Then stoppt LogStreamer.detach(SPEC-0022) den Log-Thread
    And kein Zombie-Prozess bleibt übrig
```
