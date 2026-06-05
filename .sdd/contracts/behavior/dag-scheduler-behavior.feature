Feature: DagScheduler – Abhängigkeiten und Parallelität (SPEC-0036)

  Background:
    Given DagScheduler ist mit max_parallel_local=2 und max_parallel_cloud=1 konfiguriert

  Scenario: Root-Tasks werden sofort dispatcht
    Given TaskDag enthält Task-A und Task-B ohne depends_on
    And beide Tasks werden als "local" geroutet
    When DagScheduler.run(dag) gestartet wird
    Then werden Task-A und Task-B gleichzeitig dispatcht
    And beide starten ohne auf den jeweils anderen zu warten

  Scenario: Abhängiger Task startet erst nach Abschluss der Dependency
    Given TaskDag enthält Task-A und Task-B mit Task-B.depends_on=[Task-A]
    When DagScheduler.run(dag) gestartet wird
    Then wird Task-A zuerst dispatcht
    And Task-B wird erst dispatcht nachdem Task-A completed ist

  Scenario: max_parallel_local wird nicht überschritten
    Given TaskDag enthält Task-A, Task-B und Task-C ohne depends_on
    And alle drei Tasks werden als "local" geroutet
    And max_parallel_local ist 2
    When DagScheduler.run(dag) gestartet wird
    Then laufen maximal 2 lokale Tasks gleichzeitig
    And Task-C startet erst wenn Task-A oder Task-B completed ist

  Scenario: max_parallel_cloud wird getrennt gezählt
    Given TaskDag enthält Task-A (local) und Task-B (cloud)
    And max_parallel_local ist 2 und max_parallel_cloud ist 1
    When beide Tasks dispatcht werden
    Then belegt Task-A keinen Cloud-Slot
    And Task-B belegt keinen lokalen Slot

  Scenario: Observer wird nach Task-Completion benachrichtigt
    Given Task-A ist dispatcht und wird completed
    When Task-A-Completion-Event ausgelöst wird
    Then prüft DagScheduler welche Tasks nun bereit sind
    And dispatcht alle Tasks deren depends_on vollständig completed sind

  Scenario: DAG-Invariante – keine zyklischen Abhängigkeiten
    Given TaskDag enthält Task-A.depends_on=[Task-B] und Task-B.depends_on=[Task-A]
    When DagScheduler.run(dag) aufgerufen wird
    Then wirft DagScheduler ValueError mit Hinweis auf Zyklus
    And kein Task wird dispatcht
