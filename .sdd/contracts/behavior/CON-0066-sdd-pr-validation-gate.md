---
id: CON-0066
title: "sdd-dev-pr-validation-gate"
type: behavior
format: gherkin
spec: SPEC-0021
version: 0.3.0
status: deprecated
tests: [TST-0075]
---

# Contract: sdd-dev-pr-validation-gate (deprecated)

> **Spec:** SPEC-0021 · **Typ:** Verhalten (Gherkin) · **Status:** deprecated

## Zweck

Beschrieb das Validierungsgatter von `sdd dev pr SPEC-XXXX` vor der
PR-Erstellung im interaktiven Pfad.

> **v0.3.0 (2026-09-11), deprecated (#123):** `sdd dev pr` ist mit SPEC-0044
> entfallen, zusammen mit der ganzen `sdd dev`-Gruppe. `DevContainerManager.pr()`
> erreichten seitdem nur noch TST-0075 und TST-0077. Die Methode und TST-0075
> sind entfernt.
>
> Das PR-Gate liegt heute in der Finalisierung (`SpecFinalizer.run`). Welche
> Zusage dort geblieben ist, zeigt die Tabelle unten. Einige hat die
> Finalisierung ins Gegenteil gedreht, das ist so gewollt und kein Fehler.
>
> Das `artifact`-Feld zeigte auf eine nie angelegte `.feature`-Datei und ist
> entfernt.

## Was aus den Zusagen wurde

| Zusage (v0.2.0) | Heute in der Finalisierung |
|---|---|
| G-01: Kein PR bei roten oder fehlenden Tests | **Geblieben, anders begründet.** Die Finalisierung liest kein protokolliertes Ergebnis, sie führt die Tests selbst aus. Sind sie rot, entsteht kein PR. |
| G-02: Kein PR, wenn `sdd validate` Fehler meldet | **Ersetzt.** Statt `sdd validate` läuft die Compliance-Kette (`strict=True`). Fehler dort blockieren den PR. |
| G-03: Warnung bei uncommitted changes, kein Abbruch | **Entfallen.** Die Finalisierung committet offene Änderungen selbst, außer bei `no_commit`. |
| G-04: PR-Dokument `.sdd/prs/PR-SPEC-XXXX.md` und Merge-Anleitung | **Als Fallback geblieben.** Zuerst `gh pr create`. Ist `gh` nicht da oder scheitert es, schreibt `LocalGitStrategy` das Dokument (CON-0067). |
| G-05: Regression-Check (`git diff main..<branch> --stat`) im PR-Dokument | **Im Fallback geblieben**, im Text des gh-PR nicht. |
| INV-01: Kein automatischer `git commit` | **Umgekehrt**, siehe G-03. |
| INV-02: PR nur, wenn alle Prüfungen bestanden sind | **Geblieben.** Der PR entsteht erst nach grünen Tests und sauberer Compliance-Kette. |
| INV-03: Merge-Anleitung nennt den konkreten Branch | **Im Fallback geblieben**, mit dem Branch, den die Finalisierung übergibt. |
| INV-04: Kein aktiver Container nötig | **Umgekehrt.** Ohne `docker.compose_file` bricht die Finalisierung ab, wenn der Dev-Container nicht läuft. |

## Verweise

- CON-0065 G-06: Container-Lifecycle in der Finalisierung
- CON-0067: Schema des lokalen PR-Dokuments
- Tests der Finalisierung: `tests/unit/test_finalize_container.py`,
  `tests/unit/test_finalize_push.py`, `tests/unit/test_finalize_build.py`,
  `tests/unit/test_finalize_pr_branch.py`
