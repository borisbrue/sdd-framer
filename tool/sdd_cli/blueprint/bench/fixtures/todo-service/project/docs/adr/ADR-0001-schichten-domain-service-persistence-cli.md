---
id: ADR-0001
title: "Schichten domain, service, persistence und cli"
status: accepted
date: 2026-09-27
deciders: [Bench]
related_specs: [SPEC-0001, SPEC-0002, SPEC-0003]
supersedes: ""
enforced_by: [ARCH-01]
---

# ADR-0001: Schichten domain, service, persistence und cli

## Status

accepted

## Kontext

`todo-service` soll testbar bleiben und die Speicherung austauschen können. Ohne feste Richtung
wandern Dateizugriffe in die Domäne und die CLI greift an der Service-API vorbei auf die Datei zu.

## Optionen

### Option A: Ein Modul für alles
- **Pro:** wenig Dateien
- **Contra:** Domänenlogik ist nur mit Datei testbar; Speicherung nicht austauschbar

### Option B: Vier Schichten plus Einstieg
- **Pro:** Domäne ohne I/O, Persistenz per Injektion austauschbar, CLI nur über den Service
- **Contra:** eine Verdrahtung im Einstieg nötig

## Entscheidung

Option B. ARCH-01 (`allowed_dependencies`): `todo.domain` hängt von nichts ab; `todo.service` und
`todo.persistence` nur von `todo.domain`; `todo.cli` nur von `todo.service` und `todo.domain`. Der
Einstieg (`todo/__init__.py`, `todo/__main__.py`) darf alles und verbindet CLI und Persistenz.

## Folgen

- `TodoService` erhält das Repository als Argument und kennt `todo.persistence` nicht.
- Die CLI bekommt eine Fabrik für den Service vom Einstieg.
