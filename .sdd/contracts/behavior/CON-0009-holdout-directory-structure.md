---
id: CON-0009
project: ""
title: "Holdout-Verzeichnisstruktur und HOL-Isolation"
type: behavior
format: markdown
spec: SPEC-0004
version: 0.1.0
status: draft
artifact: ""
tests: ["TST-0010"]
---

# Contract: Holdout-Verzeichnisstruktur und HOL-Isolation

> **Spec:** SPEC-0004 · **Typ:** Verhalten · **Status:** draft

## Zweck

Dieser Contract definiert die strukturelle Isolation von Holdout-Szenarien
gegenüber dem Code-generierenden Agenten. Er entspricht dem Train/Test-Split-
Prinzip aus dem Machine Learning: Was validiert, darf nicht trainieren.

## Garantien

### G-01: Verzeichnis-Isolation

Holdout-Szenarien MÜSSEN in `.sdd/holdout/` gespeichert sein.
Dieses Verzeichnis DARF einem Code-generierenden Agenten NICHT zugänglich gemacht
werden (weder per Kontext-Injection noch per Dateifreigabe).

### G-02: HOL-ID-Format

Jedes Holdout-Dokument MUSS eine ID im Format `HOL-NNNN` tragen (4-stellig, nullgefüllt).
Die ID MUSS im YAML-Frontmatter unter dem Schlüssel `id` stehen.

### G-03: Pflicht-Felder im Frontmatter

Jedes HOL-Dokument MUSS folgende Felder enthalten:

| Feld       | Typ     | Beschreibung                              |
|------------|---------|-------------------------------------------|
| `id`       | string  | HOL-NNNN                                  |
| `title`    | string  | Menschenlesbarer Name des Szenarios        |
| `contract` | string  | CON-ID des geprüften Contracts             |
| `spec`     | string  | SPEC-ID der übergeordneten Spec            |
| `status`   | enum    | `active` \| `disabled` \| `wip`           |

### G-04: Plain-English-Format

Der Szenario-Body DARF KEIN ausführbaren Code enthalten.
Er MUSS in natürlicher Sprache beschreiben:
- Was der Nutzer/Client tut (Schritte)
- Was das System antworten soll (Erwartetes Ergebnis)

### G-05: sdd validate ignoriert .sdd/holdout/

Der Befehl `sdd validate` DARF Holdout-Dokumente dem Code-Agenten NICHT über
Validierungsausgaben oder Reports zugänglich machen. HOL-Dokumente werden von
`sdd validate` **nicht** gegen das Test-Schema geprüft.

## Invarianten

- **INV-01:** `.sdd/holdout/` existiert genau dann, wenn mindestens ein HOL-Dokument angelegt wurde.
- **INV-02:** Kein HOL-Dokument erscheint in der Traceability-Matrix (`docs/traceability.md`).
- **INV-03:** `sdd new holdout` ist der einzige offizielle Weg, HOL-Dokumente anzulegen.

## Begriffe

| Begriff            | Definition                                                        |
|--------------------|-------------------------------------------------------------------|
| Holdout-Szenario   | Plain-English-Akzeptanztest, isoliert vom Code-generierenden Agenten |
| Code-Agent         | LLM, das Sourcecode generiert und implementiert                   |
| Evaluator          | Separater Prozess, der Holdout-Szenarien gegen einen Service ausführt |
