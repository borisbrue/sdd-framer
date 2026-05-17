---
id: CON-0002
title: "Login Behavior"
type: behavior
format: gherkin
spec: SPEC-0001
version: 1.0.0
status: active
artifact: "contracts/behavior/login.feature"
tests: [TST-0002]
---

# Contract: Login Behavior

> **Spec:** SPEC-0001 · **Typ:** Verhalten (Gherkin) · **Status:** active

## Zweck

Ausführbare Spezifikation des beobachtbaren Login-Verhaltens. Ergänzt CON-0001 um Szenario-getriebene Akzeptanz.

## Garantien

Die Szenarien in `contracts/behavior/login.feature` MÜSSEN durch TST-0002 (Cucumber/behave) automatisiert ausgeführt werden und vor jedem Release grün sein.

## Invarianten

- **INV-01:** Antworten auf "User existiert nicht" und "Falsches Passwort" sind ununterscheidbar (gleicher Status, gleiche Body, ähnliche Antwortzeit).
- **INV-02:** Erfolgreiche Logins werden geloggt, ohne dass das Passwort im Log erscheint.

## Begriffe

| Begriff             | Definition |
|---------------------|------------|
| Registrierter Nutzer| Ein Account mit verifizierter E-Mail im Status `active`. |
| Brute-Force         | ≥ 5 fehlgeschlagene Login-Versuche pro Account innerhalb von 15 Minuten. |
| Token-Familie       | Menge aller Refresh-Token, die durch Rotation aus einem ursprünglichen Login entstanden sind. |
