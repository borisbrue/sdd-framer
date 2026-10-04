---
id: CON-0070
title: "log-streamer"
type: behavior
format: gherkin
spec: SPEC-0022
version: 0.2.0
status: draft
artifact: "contracts/behavior/log-streamer.feature"
tests: [TST-0080]
---

# Contract: log-streamer

> **Spec:** SPEC-0022 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Beschreibt das beobachtbare Verhalten des `LogStreamer` und `LogEventBus`:
Attach/Detach von Container-Logs, Buffer-Verwaltung und WebSocket-Multicast.

> **v0.2.0 (2026-10-04, #128):** G-01 und G-04 nannten `sdd dev up/start` und
> `sdd dev down/close`. Die Befehle gibt es seit SPEC-0044 nicht mehr. Den Stream startet
> heute nur der Container-Start über die Web-API; einen eigenen Stopp-Befehl gibt es nicht.

## Garantien

- **G-01:** Nach einem erfolgreichen Container-Start über die Web-API
  (`POST /api/specs/{spec_id}/start`, ruft `sdd start`) startet
  `LogStreamer.attach(spec_id)` automatisch. `sdd start` auf der Kommandozeile streamt
  nicht; dort läuft kein API-Prozess, der Clients bedienen könnte.
- **G-02:** Neue Log-Zeilen werden innerhalb von 1 Sekunde an alle verbundenen
  WebSocket-Clients gesendet.
- **G-03:** Bei WebSocket-Verbindungsaufbau werden die letzten `log_stream.max_lines`
  Zeilen aus dem In-Memory-Buffer gesendet, danach Live-Zeilen.
- **G-04:** `LogStreamer.detach(spec_id)` stoppt den Log-Thread sauber (kein
  hängender Prozess). Endet der Container (Finalisierung), endet `logs --follow` und
  mit ihm der Thread.
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

  Scenario: Automatischer Start nach Container-Start über die Web-API
    Given Container "sdd-dev-spec-0022" wird gestartet
    When "POST /api/specs/SPEC-0022/start" erfolgreich abgeschlossen ist
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

  Scenario: detach stoppt LogStreamer sauber
    Given LogStreamer für SPEC-0022 ist aktiv
    When LogStreamer.detach(SPEC-0022) aufgerufen wird
    Then stoppt LogStreamer.detach(SPEC-0022) den Log-Thread
    And kein Zombie-Prozess bleibt übrig
```
