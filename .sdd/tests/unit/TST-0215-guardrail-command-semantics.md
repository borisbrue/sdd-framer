---
id: TST-0215
project: PRJ-0001
title: "Guardrail-Modul – Kommando-Semantik"
level: unit
spec: SPEC-0051
contract: CON-0189
status: planned
framework: pytest
artifact: "tests/unit/test_tst_0215.py"
tags: [guardrail, security, strategy, chain-of-responsibility]
---

# Test: Guardrail-Modul – Kommando-Semantik

> **Level:** unit · **Spec:** SPEC-0051 · **Contract:** CON-0189 · **Status:** planned

## Was wird geprüft?

Die Block/Allow-Entscheidung des Guardrail-Moduls (`sdd_cli/guard.py`, genutzt von `sdd guard check`).

## Testfälle

- **test_block_force_push_main:** `git push --force origin main` → "deny" (INV-04).
- **test_block_rm_rf_root:** `rm -rf /` → "deny" (INV-04).
- **test_allow_mention_in_commit_message:** `git commit -m '… rm -rf / … $HOME'` → "allow"
  (INV-02, Segment-/Mention-Erkennung).
- **test_allow_f_flag_not_force:** `gh pr create --base main --body-file /tmp/x.md` → "allow"
  (INV-03, präzise Force-Flags).
- **test_allow_compound_no_cross_trigger:** `git push origin feat/x ; gh pr create --base main`
  → "allow" (INV-01, segment-genau).
- **test_allow_targeted_repo_delete:** `rm -rf web/ui/dist` → "allow".
- **test_fail_safe_when_module_unavailable:** Hook-Wrapper bei nicht erreichbarem Modul → erlaubt +
  sichtbare `[WARN] Guardrail inaktiv` (INV-05).

## Abdeckung

CON-0189 INV-01…INV-05 · SPEC-0051 FR-04, FR-05, FR-06, FR-07, FR-08.
