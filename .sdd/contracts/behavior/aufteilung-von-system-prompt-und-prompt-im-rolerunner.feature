# language: de
Funktionalität: Aufteilung von System-Prompt und Prompt im RoleRunner
  Als Pipeline
  möchte ich gleichbleibenden Kontext im System-Prompt übergeben
  um ihn bei Wiederholungsversuchen aus dem Prompt-Cache zu lesen

  Szenario: Wiederholungsversuche teilen den System-Prompt
    Angenommen eine Task, deren Implementer dreimal am GREEN-Gate scheitert
    Wenn die Pipeline läuft
    Dann sind die System-Nachrichten der drei Implementer-Aufrufe byte-gleich
    Und sie enthalten Spec, Contracts, AGENTS.md, Task, Testdatei und den aktuellen Dateiinhalt
    Und sie enthalten weder "nonce:" noch die Testausgabe

  Szenario: Rückmeldungen stehen im Prompt
    Angenommen eine Task, deren Implementer zweimal am GREEN-Gate scheitert
    Wenn die Pipeline läuft
    Dann enthält die Nutzer-Nachricht des zweiten Implementer-Aufrufs "## Testausgabe" und "## history"
    Und sie endet mit "nonce: " und 16 Hex-Zeichen
    Und sie enthält weder "## Spec" noch "## Contracts"

  Szenario: Nach Review-Ablehnung ändert sich der System-Prompt
    Angenommen eine Task, deren Implementer grün ist und deren Review einmal ablehnt
    Wenn der Implementer den nächsten Versuch macht
    Dann unterscheidet sich seine System-Nachricht von der des ersten Versuchs
    Und sie enthält den grünen Dateiinhalt aus dem ersten Versuch

  Szenario: Reviewer sieht den Diff im Prompt
    Angenommen eine Task mit grünem Implementer
    Wenn der Reviewer aufgerufen wird
    Dann steht "## Diff" in der Nutzer-Nachricht und nicht in der System-Nachricht
    Und "## Spec" steht in der System-Nachricht

  Szenario: Supervisor-Anfrage im Prompt
    Wenn der Supervisor an S1 entscheidet
    Dann beginnt die Nutzer-Nachricht mit der Entscheidungsanfrage
    Und die System-Nachricht enthält "## Spec"

  Szenario: Rolle ohne wechselnde Quellen
    Angenommen der erste Decomposer-Aufruf ohne lead und mit leeren wechselnden Quellen
    Wenn er aufgerufen wird
    Dann ist die Nutzer-Nachricht genau purpose, "\n\nnonce: " und 16 Hex-Zeichen
    Und die System-Nachricht ist der Rollen-Prompt, "\n\n" und die gerenderten stabilen Quellen

  Szenario: Aufbau, Reihenfolge, Kürzung und leere Quellen
    Angenommen eine Rolle mit inputs [spec, task, test_output, contracts, review]
    Und spec ist länger als ihr Budget, contracts ist leer, review ist leer
    Wenn der RoleRunner sie mit lead "ANFRAGE" aufruft
    Dann ist der System-Prompt genau Rollen-Prompt, "## Spec" mit gekürzter Spec, "## Task"
    Und der Prompt ist genau "ANFRAGE", "## Testausgabe" mit test_output und der Nonce
    Und "## Contracts" und "## Review" kommen nicht vor

  Szenario: Rolle ohne stabile Quellen
    Angenommen eine Rolle mit inputs [diff]
    Wenn der RoleRunner sie aufruft
    Dann ist der System-Prompt genau der Rollen-Prompt ohne angehängte Leerzeilen

  Szenario: prompt_hash
    Wenn zwei Aufrufe mit gleichen Quellen erfolgen
    Dann haben beide denselben prompt_hash
    Und er ist SHA-256 über System-Prompt, "\n\n" und Prompt ohne Nonce, auf 16 Hex-Zeichen gekürzt
    Und eine andere wechselnde Quelle ergibt einen anderen prompt_hash
    Und eine andere stabile Quelle ergibt einen anderen prompt_hash

  Szenario: Jede Quelle ist eingeteilt
    Dann sind CONTEXT_SOURCES genau die Schlüssel von SOURCE_KINDS
    Und jede Einteilung ist stable oder volatile
