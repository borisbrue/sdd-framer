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
