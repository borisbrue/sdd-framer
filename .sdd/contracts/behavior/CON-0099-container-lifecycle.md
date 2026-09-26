---
id: CON-0099
title: "Container-Lifecycle – Erstellung, Task-Zuweisung und Cleanup"
type: behavior
format: gherkin
spec: SPEC-0026
version: 0.2.0
status: deprecated
tests:
- TST-0118
deprecated_reason: "mit SPEC-0026 abgelöst: Distribution Engine ohne Codeerzeugung; abgelöst durch die Rollen-Pipeline"
---

# Contract: Container-Lifecycle – Erstellung, Task-Zuweisung und Cleanup

> **Spec:** SPEC-0026 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Legt fest, wo die Tasks einer Spec bei `sdd distribute` ausgeführt werden und
wo Isolation und Aufräumen stattfinden.

> **v0.2.0 (2026-09-11):** Der Contract beschrieb eine eigene Container-Runtime
> für Tasks, mit Build per `git archive`, Netzwerkisolation, Aufräumen bei
> SIGINT und Namen nach dem Schema `sdd-SPEC-XXXX-<uuid>` (INV-03). **Nichts
> davon ist umgesetzt.** `DistributionOrchestrator` führt jeden Task mit
> `container_id="local"` aus. Seit SPEC-0026 (`45b29e6`) laufen Tests und
> Isolation in der gemeinsamen Finalisierung, im Dev-Container aus CON-0065.
>
> TST-0118 prüfte bis dahin ein `MockContainerRuntime`, das in der Testdatei
> selbst definiert war. Die sechs Tests dagegen konnten nicht rot werden, wenn
> Produktionscode kaputtgeht (#113).
>
> Jetzt beschreibt der Contract, was der Code tut. Die entfallenen Zusagen
> stehen unten, damit nachvollziehbar bleibt, was einmal geplant war. Das
> `artifact`-Feld zeigte auf eine nie angelegte `.feature`-Datei und ist
> entfernt.

## Garantien

- **G-01:** Beim Start eines Tasks (`TaskLifecycle.start_running`) wird der
  Ausführungsort am Task festgehalten (`container_id`), und der Task geht auf
  `running`. Welche Übergänge erlaubt sind, regelt der Task-Lifecycle (CON-0095).
- **G-02:** `sdd distribute` führt die Tasks lokal aus: `container_id` ist
  `"local"`. Eine eigene Container-Runtime pro Task gibt es nicht.
- **G-03:** Isolation und Aufräumen übernimmt die gemeinsame Finalisierung, im
  Dev-Container der Spec (CON-0065 G-06).
- **G-04:** `container_id` bleibt beim Speichern und Laden eines Tasks erhalten
  (`Task.to_dict` / `Task.from_dict`).

## Invarianten

- **INV-01:** `start_running` setzt Status und Ausführungsort gemeinsam. Einen
  Übergang nach `running` ohne `container_id` gibt es nicht.

## Entfallene Zusagen (v0.1.0)

| Zusage | Stand |
|---|---|
| Container werden aus dem Git-HEAD gebaut (`git archive` + Dockerfile) | nicht umgesetzt; der Dev-Container mountet das Arbeitsverzeichnis (CON-0065 G-02) |
| Mehrere Tasks pro Container, flexibler Zuschnitt | nicht umgesetzt; Tasks laufen lokal |
| Container ohne Netzwerkzugang zu Produktionssystemen | nicht umgesetzt |
| Entfernen nach Abschluss aller Tasks | ersetzt durch CON-0065 G-06 (Finalisierung) |
| Entfernen aller Container bei SIGINT/Fehler | nicht umgesetzt |
| INV-01: mindestens ein Task pro Container | gegenstandslos |
| INV-02: Code-Stand = HEAD beim `sdd distribute`-Aufruf, kein Live-Mount | nicht umgesetzt; der Dev-Container nutzt einen Live-Mount |
| INV-03: Namensschema `sdd-SPEC-XXXX-<uuid>` | nicht umgesetzt; es gibt nur `sdd-dev-<spec-id>` (CON-0065 INV-01) |
| INV-04: nach `container.remove()` kein Runtime-Objekt mehr | gegenstandslos |

Wird eine echte Task-Isolation wieder gebraucht, gehört sie in eine eigene Spec,
nicht in eine Wiederbelebung dieses Contracts.

## Szenarien (Gherkin)

```gherkin
Feature: Ausführungsort von Tasks

  Scenario: Task startet mit Ausführungsort
    Given ein Task T1 im Status assigned
    When TaskLifecycle(T1).start_running("local") aufgerufen wird
    Then ist T1 im Status running
    And T1.container_id ist "local"

  Scenario: sdd distribute führt lokal aus
    Given zwei Tasks für SPEC-0026
    When DistributionOrchestrator.run die Tasks startet
    Then haben beide Tasks container_id "local"

  Scenario: Ausführungsort übersteht Speichern und Laden
    Given ein laufender Task mit container_id "local"
    When der Task gespeichert und wieder geladen wird
    Then ist container_id weiterhin "local"
```

## Begriffe

| Begriff | Definition |
|---|---|
| Ausführungsort | Wo ein Task läuft; festgehalten als `Task.container_id` |
| Finalisierung | `SpecFinalizer.run()`, gemeinsam für alle Implementierungspfade (CON-0065) |
