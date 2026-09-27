# CON-0197 · SPEC-0054 FR-01, FR-03, FR-06, FR-07, FR-13, FR-14
Feature: CLI für Qualitätsmessung und Architekturregeln
  Als Entwickler, Pipeline oder CI
  möchte ich Qualität und Architekturtreue über stabile Befehle mit festen Exit-Codes messen
  um sie als Gate und als Datenquelle nutzen zu können

  Background:
    Given ein Projekt mit .sdd/config.yaml, .sdd/quality.yaml und .sdd/architecture.yaml

  Scenario: measure schreibt einen schema-gültigen Report
    When ich "sdd quality measure --spec SPEC-0900 --json" ausführe
    Then ist stdout ein JSON-Dokument, das quality-report.schema.json erfüllt
    And der Exit-Code ist 0

  Scenario: measure mit --out
    When ich "sdd quality measure --out build/q.json" ausführe
    Then existiert build/q.json und erfüllt quality-report.schema.json
    And eine Kopie liegt unter .sdd/quality/runs/

  Scenario: measure mit fehlgeschlagenem Gate
    Given quality.gates enthält "requirements >= 1.0"
    And FR-02 hat den Status teilweise
    When ich "sdd quality measure --spec SPEC-0900" ausführe
    Then ist der Exit-Code 1
    And die Ausgabe nennt das Gate und FR-02

  Scenario: measure ohne quality.yaml
    Given .sdd/quality.yaml existiert nicht
    When ich "sdd quality measure" ausführe
    Then ist der Exit-Code 2
    And die Ausgabe verweist auf "sdd stack apply"

  Scenario: measure mit ungültiger quality.yaml
    Given .sdd/quality.yaml verletzt quality-config.schema.json
    When ich "sdd quality measure" ausführe
    Then ist der Exit-Code 2
    And die Ausgabe nennt den Feldpfad des Fehlers

  Scenario: Diff-begrenzte Messung
    Given seit BASE wurde nur tool/a.py geändert
    And die Sonde "lint" hat diff_scoped true
    When ich "sdd quality measure --diff BASE --json" ausführe
    Then erhielt die Sonde "lint" für {paths} nur tool/a.py
    And der Report enthält base_ref "BASE"

  Scenario: test run nutzt die Testsonde und speichert Testfälle
    Given .sdd/quality.yaml definiert eine Sonde mit role tests
    When ich "sdd test run SPEC-0900" ausführe
    Then wurde der Befehl dieser Sonde ausgeführt
    And neben dem Run-Report liegt eine JUnit-Datei
    And der Run-Report enthält je Testfall Name, Status und FR-Markierung

  Scenario: test run ohne quality.yaml bleibt unverändert
    Given .sdd/quality.yaml existiert nicht
    When ich "sdd test run SPEC-0900" ausführe
    Then verhält sich der Befehl wie in SPEC-0006

  Scenario: measure nutzt vorhandenen Test-Run
    Given es gibt einen Run-Report von SPEC-0900 für den aktuellen Git-SHA
    When ich "sdd quality measure --spec SPEC-0900 --reuse-test-run" ausführe
    Then wurde die Testsonde nicht erneut ausgeführt
    And requirements.test_run verweist auf diesen Run-Report

  Scenario: doctor meldet Probleme je Sonde
    Given die Sonde "types" verweist auf einen nicht installierten Befehl
    And die Sonde "complexity" speist die Metrik complexity_max ohne Normierung
    When ich "sdd quality doctor" ausführe
    Then ist der Exit-Code 1
    And die Ausgabe meldet für "types" "Befehl nicht gefunden"
    And für "complexity" "Normierung fehlt"

  Scenario: init verweist auf die Stack-Vorlage
    Given .sdd/quality.yaml existiert nicht
    When ich "sdd quality init --preset python" ausführe
    Then ist der Exit-Code 1
    And die Ausgabe nennt "sdd stack apply python-cli --only quality"
    And .sdd/quality.yaml existiert weiterhin nicht

  Scenario: init schreibt nichts
    Given .sdd/quality.yaml existiert und weicht von der Vorlage ab
    When ich "sdd quality init --preset python" ausführe
    Then ist der Exit-Code 1
    And .sdd/quality.yaml ist unverändert und es gibt keine .new-Datei

  Scenario: arch check meldet Verstoß mit ADR
    Given Regel ARCH-01 mit adr ADR-0007 verbietet Abhängigkeiten von web nach core/writer.py
    And web/routes.py importiert core/writer.py in Zeile 4
    When ich "sdd arch check" ausführe
    Then ist der Exit-Code 1
    And die Ausgabe enthält "ARCH-01", "ADR-0007", den ADR-Titel und "web/routes.py:4"

  Scenario: arch check mit Baseline
    Given der Verstoß ARCH-01 in web/routes.py mit Symbol writer steht in der Baseline
    When ich "sdd arch check" ausführe
    Then ist der Exit-Code 0
    And die Ausgabe markiert den Verstoß als "warn (Baseline)"

  Scenario: Veralteter Baseline-Eintrag
    Given die Baseline enthält einen Eintrag, zu dem es keinen Verstoß mehr gibt
    When ich "sdd arch check" ausführe
    Then ist der Exit-Code 0
    And die Ausgabe meldet "Baseline kann bereinigt werden"

  Scenario: Baseline schreiben
    When ich "sdd arch check --write-baseline" ausführe
    Then enthält .sdd/quality/arch-baseline.json jeden aktuellen error-Verstoß mit dem reason-Platzhalter "TODO"
    And der Exit-Code ist 0

  Scenario: Baseline fortschreiben erhält vorhandene Einträge
    Given die Baseline enthält einen Eintrag mit reason "Altlast, SPEC-0053"
    And es ist ein neuer error-Verstoß hinzugekommen
    When ich "sdd arch check --write-baseline" ausführe
    Then enthält die Baseline den alten Eintrag mit unverändertem reason
    And einen neuen Eintrag mit reason "TODO"
    And stderr zeigt den Diff

  Scenario: --out überschreibt ein vorhandenes Ziel
    Given build/q.json existiert
    When ich "sdd quality measure --out build/q.json" ausführe
    Then ist build/q.json der neue Report
    And es entsteht keine Datei build/q.json.new

  Scenario: arch check ohne architecture.yaml
    Given .sdd/architecture.yaml existiert nicht
    When ich "sdd arch check" ausführe
    Then ist der Exit-Code 2
    And die Ausgabe verweist auf "sdd arch init"

  Scenario: arch init schlägt Schichten vor
    Given .sdd/architecture.yaml existiert nicht
    When ich "sdd arch init" ausführe
    Then existiert .sdd/architecture.yaml mit einer Schicht je Top-Level-Paket und leerer Regelliste

  Scenario: validate prüft die ADR-Verknüpfung
    Given Regel ARCH-05 verweist auf ADR-0099, das nicht existiert
    And ADR-0007 mit Status accepted nennt enforced_by ARCH-09, das nicht existiert
    When ich "sdd validate" ausführe
    Then meldet die Ausgabe einen Fehler zu ARCH-05 und ADR-0099
    And eine Warnung zu ADR-0007 und ARCH-09
    And der Exit-Code ist 1

  Scenario: validate warnt bei Regel an abgelöstem ADR
    Given Regel ARCH-02 verweist auf ADR-0008 mit Status superseded
    When ich "sdd validate" ausführe
    Then meldet die Ausgabe eine Warnung zu ARCH-02 und ADR-0008

  Scenario: validate meldet doppelte Regel-IDs
    Given architecture.yaml enthält zweimal die Regel-ID ARCH-03
    When ich "sdd validate" ausführe
    Then meldet die Ausgabe einen Fehler "doppelte Regel-ID ARCH-03"

  Scenario: Zwei Sonden mit derselben Rolle
    Given .sdd/quality.yaml definiert zwei Sonden mit role tests
    When ich "sdd quality measure" ausführe
    Then ist der Exit-Code 2
    And die Ausgabe nennt beide Sondennamen

  Scenario: Keine sprachspezifischen Befehle
    When ich "sdd --help" und die Hilfe jeder Befehlsgruppe ausgebe
    Then kommt kein Sprach- oder Werkzeugname als Befehl vor
