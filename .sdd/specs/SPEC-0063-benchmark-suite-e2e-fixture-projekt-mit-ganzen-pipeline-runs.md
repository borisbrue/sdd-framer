---
id: SPEC-0063
title: "Benchmark-Suite e2e: Fixture-Projekt mit ganzen Pipeline-Runs"
type: feature
status: draft
owner: "Boris"
created: 2026-09-27
updated: 2026-09-27
version: 0.1.0
priority: medium
tags: [benchmark, pipeline, fixture, quality]
depends_on: [SPEC-0056, SPEC-0053, SPEC-0054, SPEC-0061]
contracts: []
tests: []
---

# Benchmark-Suite e2e: Fixture-Projekt mit ganzen Pipeline-Runs

> **Status:** draft · **Owner:** Boris · **Version:** 0.1.0

## 1. Kontext & Motivation

Aus SPEC-0056 0.1.0 abgespalten (Review 2026-09-27). SPEC-0056 liefert die Benchmark-Engine mit den
Suiten `roles` und `regen`. Diese Spec ergänzt die teuerste und realistischste Stufe: ganze Specs
eines Fixture-Projekts per `sdd pipeline run` mit einer Modellbelegung umsetzen und den Endstand
mit versteckten Akzeptanztests und SPEC-0054 messen.

## 2. Zielsetzung

**Primärziel:** Suite-Art `e2e` für `sdd bench run`, mit dem Fixture `todo-service` im Blueprint.

**Nicht-Ziele (explizit):**
- Keine Änderungen an der Benchmark-Engine außer der Registrierung der Suite-Art.

## 3. Architektur & Design Patterns

Nutzt die in SPEC-0056 angenommenen Patterns (Template Method `BenchTask`, Proxy für versteckte
Tests und Referenzlösung, Decorator für Budget und Zählung).

## 4. Funktionale Anforderungen

- **FR-01:** Suite-Art `e2e` führt `sdd pipeline run --auto` für die gelisteten Specs eines
  Fixture-Projekts in einem frischen Arbeitsverzeichnis (Kopie oder `git worktree`) mit der Belegung
  der Matrix aus und misst den Endstand mit `sdd quality measure --spec … --diff <start>` plus
  versteckten Akzeptanztests (`q_kind: quality`).
- **FR-02:** Versteckte Akzeptanztests und Referenzlösung werden erst nach dem letzten Rollenaufruf
  in das Arbeitsverzeichnis kopiert; kein Rollenkontext enthält sie.
- **FR-03:** Budget: `bench.budget.max_tokens` und `max_claude_tokens` brechen einen Pipeline-Run
  kontrolliert ab (Ausgang `halted: budget`, Record mit dem erreichten Stand). Dafür bekommt die
  Pipeline einen Budget-Haken.
- **FR-04:** Optional `bench.isolation: container` (Dev-Container statt Verzeichnis).
- **FR-05:** Der Blueprint liefert das Fixture `todo-service` mit mindestens drei Specs
  unterschiedlicher Größe (klein: 3 FRs, mittel: 6 FRs, groß: 10 FRs mit Schichtregeln) samt
  versteckten Akzeptanztests, Referenzlösung, `architecture.yaml` und `quality.yaml`.

## 10. Offene Fragen

- [ ] Fixture-Stack: Python mit Standardbibliothek oder FastAPI (Abhängigkeit ist in sdd-framer schon
      vorhanden)?
- [ ] Nächtlicher Lauf per GitHub-Action gegen einen selbst gehosteten Runner?

## 11. Änderungshistorie

| Datum      | Version | Autor         | Änderung |
|------------|---------|---------------|----------|
| 2026-09-27 | 0.1.0   | Boris, Claude | Aus SPEC-0056 0.1.0 abgespalten (Review) |
