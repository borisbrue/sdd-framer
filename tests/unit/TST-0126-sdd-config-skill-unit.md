---
id: TST-0126
title: "/sdd-config Claude-Code-Skill (Unit)"
level: unit
spec: SPEC-0027
contract: CON-0107
status: draft
artifact: tests/unit/test_tst_0126.py
---

# TST-0126: /sdd-config Claude-Code-Skill

## Zu prüfendes Verhalten

`.claude/commands/sdd-config.md` definiert das Skill-Verhalten: Lesen, Problemerkennung,
Bestätigung vor Schreiben, API-Key-Sicherheit (CON-0107).

## Testfälle

- T01: Skill-Datei existiert unter `.claude/commands/sdd-config.md`
- T02: Skill enthält Anweisung zum Lesen von `config.yaml` beim Start
- T03: Skill enthält Regel "nie ohne explizite Bestätigung schreiben" (INV-01)
- T04: Skill enthält Regel "niemals API-Keys direkt vorschlagen" (Security)
- T05: Skill enthält Regel "niemals .sdd/holdout/ lesen" (INV-02)
- T06: Skill enthält Abbruch-Bedingung wenn `config.yaml` fehlt (INV-03)
- T07: Skill enthält `sdd config validate` nach dem Schreiben
