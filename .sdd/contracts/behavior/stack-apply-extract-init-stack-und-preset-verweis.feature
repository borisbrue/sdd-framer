Feature: stack apply, extract, init --stack und Preset-Verweis
  Als Entwickler
  möchte ich eine bewährte Einrichtung übernehmen und eigene Erfahrungen zurückführen
  um Projekte schnell messbar aufzusetzen

  Scenario: Neues Projekt mit Vorlage
    Given ein leeres Verzeichnis
    When ich "sdd init --name Demo --stack python-cli" ausführe
    Then enthält das Projekt .sdd/quality.yaml, .sdd/architecture.yaml und einen Skeleton-Test
    And config.yaml nennt unter stack python-cli mit Version und Datei-Hashes

  Scenario: Projekt hat die Vorlage weiterentwickelt
    Given das Projekt hat in .sdd/quality.yaml eine zusätzliche Sonde "coverage"
    When ich "sdd stack apply python-cli --yes" ausführe
    Then wird .sdd/quality.yaml nicht überschrieben
    And es entsteht .sdd/quality.yaml.new mit Diff-Ausgabe

  Scenario: Idempotent
    Given python-cli ist angewendet
    When ich "sdd stack apply python-cli --yes" erneut ausführe
    Then ändert sich keine Datei

  Scenario: AGENTS.md-Abschnitte
    Given AGENTS.md mit eigenem Text
    When ich "sdd stack apply python-cli --yes" ausführe
    Then stehen die Abschnitte zwischen den Markierungen und der eigene Text ist unverändert

  Scenario: Nutzervorlage mit Vorschau
    Given eine Nutzervorlage demo
    When ich "sdd stack apply demo" ausführe und ablehne
    Then zeigt die Ausgabe die Dateiliste und nichts wird geschrieben

  Scenario: Fehlender Platzhalter
    Given eine Vorlage mit Platzhalter ohne Default
    When ich "sdd stack apply demo --yes" nicht interaktiv ausführe
    Then ist der Exit-Code 2 und nichts wird geschrieben

  Scenario: Nur Qualität
    When ich "sdd stack apply python-cli --only quality --yes" ausführe
    Then werden nur .sdd/quality.yaml und .sdd/quality/ geschrieben

  Scenario: Vorlage aus dem Projekt extrahieren
    Given ein Projekt mit angewendeter Vorlage python-cli und eigener Sonde
    When ich "sdd stack extract mein-stack --to project" ausführe
    Then erfüllt .sdd/stacks/mein-stack/stack.yaml das Schema
    And ein anderes Projekt kann mein-stack anwenden

  Scenario: Preset-Verweis
    When ich "sdd quality init --preset python" ausführe
    Then ist der Exit-Code 1 und die Ausgabe nennt "sdd stack apply python-cli --only quality"
