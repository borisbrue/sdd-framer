---
id: CON-0181
project: PRJ-0001
title: "VisionStats – Value Object Schema"
type: data
format: markdown
spec: SPEC-0047
version: 0.1.0
status: approved
artifact: ""
tests:
- TST-0207
---

# Contract: VisionStats – Value Object Schema

> **Spec:** SPEC-0047 · **Typ:** Daten (Schema) · **Status:** draft

## Zweck

Definiert das unveränderliche Datenmodell `VisionStats`, das alle berechneten
Kennzahlen einer `VisionDocument`-Instanz kapselt.

## Schema

| Feld                 | Typ   | Beschreibung                                      | Nie negativ |
|----------------------|-------|---------------------------------------------------|-------------|
| `feature_count`      | `int` | Anzahl aller Features in `## Features`            | ✓           |
| `task_total`         | `int` | Gesamtanzahl aller Tasks in `## Tasks`            | ✓           |
| `task_done`          | `int` | Anzahl erledigter Tasks (`[x]`)                   | ✓           |
| `task_open`          | `int` | Anzahl offener Tasks (`[ ]`)                      | ✓           |
| `llm_challenge_count`| `int` | Anzahl Features mit `llm_challenge is not None`   | ✓           |
| `code_challenge_count`| `int`| Anzahl Features mit `code_challenge is not None`  | ✓           |

## Invarianten

- **INV-01:** `task_done + task_open == task_total` — immer erfüllt, keine Ausnahmen.
- **INV-02:** Alle Felder sind `>= 0` — keine negativen Zählwerte möglich.
- **INV-03:** `llm_challenge_count <= feature_count` und
  `code_challenge_count <= feature_count` — Challenges können nicht mehr sein als Features.
- **INV-04:** `VisionStats` ist ein Frozen Dataclass (oder äquivalent immutable) —
  nach der Erstellung sind keine Feldänderungen möglich.
- **INV-05:** `VisionStats.from_document(doc: VisionDocument) -> VisionStats` ist die
  einzige Factory-Methode — keine Konstruktion aus rohem Markdown.

## Beispielinstanz

```python
VisionStats(
    feature_count=3,
    task_total=5,
    task_done=2,
    task_open=3,
    llm_challenge_count=2,
    code_challenge_count=1,
)
```

## Fehlerverhalten

- `from_document()` wirft keinen Fehler — fehlt ein Abschnitt im Dokument, wird
  der entsprechende Zähler als 0 initialisiert.
- Alle Validierungen (INV-01 bis INV-03) werden in `__post_init__` geprüft;
  ein Verstoß löst `ValueError` mit beschreibender Nachricht aus.
