Feature: Bench-Lauf, Isolation, Suiten roles und regen
  Als Entwickler
  möchte ich Modellbelegungen reproduzierbar auf festen Aufgaben vergleichen
  um Rollen mit dem besten Verhältnis von Qualität zu Tokens zu belegen

  Scenario: Sweep über drei Profile in regen
    Given matrix.yaml mit sweep über drei Profile für implementer und eine regen-Suite mit einem Modul
    When ich "sdd bench run --matrix bench/matrix.yaml --suite regen --repetitions 1" ausführe
    Then enthält results.jsonl drei Records mit q_kind quality und je einer Belegung sweep-<profil>
    And das Projekt-Worktree ist unverändert

  Scenario: Versteckte Tests bleiben verborgen
    Given eine regen-Suite, deren Modul einen Marker im Code trägt
    When ein Lauf die Rolle implementer aufruft
    Then enthält kein Prompt an implementer den Marker

  Scenario: Suite roles
    Given eine roles-Suite für decomposer und zwei Profile
    When ich "sdd bench run --matrix bench/matrix.yaml --suite roles" ausführe
    Then enthält results.jsonl je Profil einen Record mit q_kind eval und ohne Holdout-IDs

  Scenario: Stufenmodell
    Given top_k ist 1 und roles bewertet Profil a besser als b
    When ich "sdd bench run --matrix bench/matrix.yaml" ausführe
    Then läuft regen nur mit a und der Report nennt b als gefiltert

  Scenario: Budget
    Given budget.max_tokens ist 100
    When ein Lauf mehr als 100 Tokens verbraucht
    Then endet der Lauf mit halted: budget und der Record enthält den gemessenen Stand

  Scenario: Resume
    Given ein Ergebnisordner mit zwei von drei Läufen, einer davon mit Ausgang error
    When ich "sdd bench run --matrix bench/matrix.yaml --resume <ordner>" ausführe
    Then werden nur der fehlende und der error-Lauf ausgeführt
    And results.jsonl enthält danach drei Records

  Scenario: Probelauf
    When ich "sdd bench run --matrix bench/matrix.yaml --dry-run" ausführe
    Then nennt die Ausgabe die Zahl der Läufe und kein LLM wird aufgerufen

  Scenario: Ungültige Matrix
    Given matrix.yaml nennt ein Profil, das in llm.profiles fehlt
    When ich "sdd bench run --matrix bench/matrix.yaml" ausführe
    Then ist der Exit-Code 2

  Scenario: bench init
    When ich "sdd bench init" zweimal ausführe
    Then existieren bench/matrix.yaml und bench/suites/roles.yaml und wurden nicht überschrieben
