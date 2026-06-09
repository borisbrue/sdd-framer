---
id: CON-0156
title: compliance-Konfigurationsschema in config.yaml
type: data
format: markdown
spec: SPEC-0041
version: 0.1.0
status: approved
tests:
- TST-0178
---
Der `compliance:`-Abschnitt in `.sdd/config.yaml` akzeptiert genau die
definierten Felder mit ihren Defaults; unbekannte Felder werden ignoriert.

**Garantiertes Schema**

```yaml
compliance:
  fr_coverage_check: true        # bool, Default: true
  type_aware_test_check: true    # bool, Default: true
  route_registration_check: true # bool, Default: true
  route_entry_points:            # list[str], Default: siehe unten
    - tool/sdd_cli/web/api/main.py
    - web/api/main.py
  post_commit_hook: true         # bool, Default: true
```

**Garantien**

- Fehlt der `compliance:`-Abschnitt vollständig, gelten alle Defaults
  (alle Checks aktiv, Standard-Entry-Points).
- Jeder `bool`-Wert `false` deaktiviert den zugehörigen Check vollständig;
  er produziert dann keine `ComplianceIssue`-Einträge.
- `route_entry_points` ist eine Liste relativer Pfade zum Projekt-Root;
  Pfade die nicht existieren werden stillschweigend übersprungen.
- Felder mit falschem Typ (z.B. `fr_coverage_check: "yes"` statt `bool`)
  werden als ungültig betrachtet: der jeweilige Default-Wert greift und
  beim Start von `sdd finalize` oder `sdd validate` wird eine
  Warnung ausgegeben (`[WARN] compliance.<feld>: ungültiger Wert,
  verwende Default`).
- Die Konfiguration wird einmalig beim Start von `sdd finalize` bzw.
  `sdd validate` gelesen; kein Hot-Reload während der Laufzeit.
