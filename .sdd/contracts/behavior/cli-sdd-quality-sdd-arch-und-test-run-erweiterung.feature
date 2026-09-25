# language: de
# CON-0197 · SPEC-0054 FR-01, FR-03, FR-06, FR-07, FR-13, FR-14
Funktionalität: CLI für Qualitätsmessung und Architekturregeln
  Als Entwickler, Pipeline oder CI
  möchte ich Qualität und Architekturtreue über stabile Befehle mit festen Exit-Codes messen
  um sie als Gate und als Datenquelle nutzen zu können

  Grundlage:
    Angenommen ein Projekt mit .sdd/config.yaml, .sdd/quality.yaml und .sdd/architecture.yaml

  Szenario: measure schreibt einen schema-gültigen Report
    Wenn ich "sdd quality measure --spec SPEC-0900 --json" ausführe
    Dann ist stdout ein JSON-Dokument, das quality-report.schema.json erfüllt
    Und der Exit-Code ist 0

  Szenario: measure mit --out
    Wenn ich "sdd quality measure --out build/q.json" ausführe
    Dann existiert build/q.json und erfüllt quality-report.schema.json
    Und eine Kopie liegt unter .sdd/quality/runs/

  Szenario: measure mit fehlgeschlagenem Gate
    Angenommen quality.gates enthält "requirements >= 1.0"
    Und FR-02 hat den Status teilweise
    Wenn ich "sdd quality measure --spec SPEC-0900" ausführe
    Dann ist der Exit-Code 1
    Und die Ausgabe nennt das Gate und FR-02

  Szenario: measure ohne quality.yaml
    Angenommen .sdd/quality.yaml existiert nicht
    Wenn ich "sdd quality measure" ausführe
    Dann ist der Exit-Code 2
    Und die Ausgabe verweist auf "sdd quality init"

  Szenario: measure mit ungültiger quality.yaml
    Angenommen .sdd/quality.yaml verletzt quality-config.schema.json
    Wenn ich "sdd quality measure" ausführe
    Dann ist der Exit-Code 2
    Und die Ausgabe nennt den Feldpfad des Fehlers

  Szenario: Diff-begrenzte Messung
    Angenommen seit BASE wurde nur tool/a.py geändert
    Und die Sonde "lint" hat diff_scoped true
    Wenn ich "sdd quality measure --diff BASE --json" ausführe
    Dann erhielt die Sonde "lint" für {paths} nur tool/a.py
    Und der Report enthält base_ref "BASE"

  Szenario: test run nutzt die Testsonde und speichert Testfälle
    Angenommen .sdd/quality.yaml definiert eine Sonde mit role tests
    Wenn ich "sdd test run SPEC-0900" ausführe
    Dann wurde der Befehl dieser Sonde ausgeführt
    Und neben dem Run-Report liegt eine JUnit-Datei
    Und der Run-Report enthält je Testfall Name, Status und FR-Markierung

  Szenario: test run ohne quality.yaml bleibt unverändert
    Angenommen .sdd/quality.yaml existiert nicht
    Wenn ich "sdd test run SPEC-0900" ausführe
    Dann verhält sich der Befehl wie in SPEC-0006

  Szenario: measure nutzt vorhandenen Test-Run
    Angenommen es gibt einen Run-Report von SPEC-0900 für den aktuellen Git-SHA
    Wenn ich "sdd quality measure --spec SPEC-0900 --reuse-test-run" ausführe
    Dann wurde die Testsonde nicht erneut ausgeführt
    Und requirements.test_run verweist auf diesen Run-Report

  Szenario: doctor meldet Probleme je Sonde
    Angenommen die Sonde "types" verweist auf einen nicht installierten Befehl
    Und die Sonde "complexity" speist die Metrik complexity_max ohne Normierung
    Wenn ich "sdd quality doctor" ausführe
    Dann ist der Exit-Code 1
    Und die Ausgabe meldet für "types" "Befehl nicht gefunden"
    Und für "complexity" "Normierung fehlt"

  Szenario: init kopiert ein Preset ins Projekt
    Angenommen .sdd/quality.yaml existiert nicht
    Wenn ich "sdd quality init --preset python" ausführe
    Dann existieren .sdd/quality.yaml und die Hilfsskripte unter .sdd/quality/
    Und die Sondenbefehle rufen die Skripte unter .sdd/quality/ auf

  Szenario: init überschreibt keine vorhandene Datei
    Angenommen .sdd/quality.yaml existiert und weicht vom Preset ab
    Wenn ich "sdd quality init --preset python" ausführe
    Dann ist .sdd/quality.yaml unverändert
    Und es existiert .sdd/quality.yaml.new
    Und die Ausgabe zeigt den Diff

  Szenario: arch check meldet Verstoß mit ADR
    Angenommen Regel ARCH-01 mit adr ADR-0007 verbietet Abhängigkeiten von web nach core/writer.py
    Und web/routes.py importiert core/writer.py in Zeile 4
    Wenn ich "sdd arch check" ausführe
    Dann ist der Exit-Code 1
    Und die Ausgabe enthält "ARCH-01", "ADR-0007", den ADR-Titel und "web/routes.py:4"

  Szenario: arch check mit Baseline
    Angenommen der Verstoß ARCH-01 in web/routes.py mit Symbol writer steht in der Baseline
    Wenn ich "sdd arch check" ausführe
    Dann ist der Exit-Code 0
    Und die Ausgabe markiert den Verstoß als "warn (Baseline)"

  Szenario: Veralteter Baseline-Eintrag
    Angenommen die Baseline enthält einen Eintrag, zu dem es keinen Verstoß mehr gibt
    Wenn ich "sdd arch check" ausführe
    Dann ist der Exit-Code 0
    Und die Ausgabe meldet "Baseline kann bereinigt werden"

  Szenario: Baseline schreiben
    Wenn ich "sdd arch check --write-baseline" ausführe
    Dann enthält .sdd/quality/arch-baseline.json jeden aktuellen error-Verstoß mit dem reason-Platzhalter "TODO"
    Und der Exit-Code ist 0

  Szenario: Baseline fortschreiben erhält vorhandene Einträge
    Angenommen die Baseline enthält einen Eintrag mit reason "Altlast, SPEC-0053"
    Und es ist ein neuer error-Verstoß hinzugekommen
    Wenn ich "sdd arch check --write-baseline" ausführe
    Dann enthält die Baseline den alten Eintrag mit unverändertem reason
    Und einen neuen Eintrag mit reason "TODO"
    Und stderr zeigt den Diff

  Szenario: --out überschreibt ein vorhandenes Ziel
    Angenommen build/q.json existiert
    Wenn ich "sdd quality measure --out build/q.json" ausführe
    Dann ist build/q.json der neue Report
    Und es entsteht keine Datei build/q.json.new

  Szenario: arch check ohne architecture.yaml
    Angenommen .sdd/architecture.yaml existiert nicht
    Wenn ich "sdd arch check" ausführe
    Dann ist der Exit-Code 2
    Und die Ausgabe verweist auf "sdd arch init"

  Szenario: arch init schlägt Schichten vor
    Angenommen .sdd/architecture.yaml existiert nicht
    Wenn ich "sdd arch init" ausführe
    Dann existiert .sdd/architecture.yaml mit einer Schicht je Top-Level-Paket und leerer Regelliste

  Szenario: validate prüft die ADR-Verknüpfung
    Angenommen Regel ARCH-05 verweist auf ADR-0099, das nicht existiert
    Und ADR-0007 mit Status accepted nennt enforced_by ARCH-09, das nicht existiert
    Wenn ich "sdd validate" ausführe
    Dann meldet die Ausgabe einen Fehler zu ARCH-05 und ADR-0099
    Und eine Warnung zu ADR-0007 und ARCH-09
    Und der Exit-Code ist 1

  Szenario: validate warnt bei Regel an abgelöstem ADR
    Angenommen Regel ARCH-02 verweist auf ADR-0008 mit Status superseded
    Wenn ich "sdd validate" ausführe
    Dann meldet die Ausgabe eine Warnung zu ARCH-02 und ADR-0008

  Szenario: validate meldet doppelte Regel-IDs
    Angenommen architecture.yaml enthält zweimal die Regel-ID ARCH-03
    Wenn ich "sdd validate" ausführe
    Dann meldet die Ausgabe einen Fehler "doppelte Regel-ID ARCH-03"

  Szenario: Zwei Sonden mit derselben Rolle
    Angenommen .sdd/quality.yaml definiert zwei Sonden mit role tests
    Wenn ich "sdd quality measure" ausführe
    Dann ist der Exit-Code 2
    Und die Ausgabe nennt beide Sondennamen

  Szenario: Keine sprachspezifischen Befehle
    Wenn ich "sdd --help" und die Hilfe jeder Befehlsgruppe ausgebe
    Dann kommt kein Sprach- oder Werkzeugname als Befehl vor
