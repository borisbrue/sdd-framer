---
id: CON-0212
title: "Profile, Rollenbelegung, Session-Auftrag und reopen"
type: data
format: json-schema
spec: SPEC-0061
version: 0.1.0
status: approved
artifact: ".sdd/contracts/data/profile-rollenbelegung-session-auftrag-und-reopen.schema.json"
tests: ["TST-0241"]
---

# Contract: Profile, Rollenbelegung, Session-Auftrag und reopen

> **Spec:** SPEC-0061 · **Typ:** Daten (JSON Schema) · **Status:** approved

## Zweck

Beschreibt die Datenstrukturen der Pipeline-Fähigkeiten aus SPEC-0061: benannte Modellprofile
(`llm.profiles`), die erweiterte Rollenbelegung (`llm.roles.<rolle>`: `mode`, `profile`,
`by_complexity`), die Pipeline-Einstellungen (`pipeline.*`), den Auftrag an eine Session-Arbeitsrolle
(`pending-work.json`) und das S3-Command `reopen`. Alles ergänzt bestehende Contracts additiv.

## Invarianten

- **INV-01:** Eine Rollenbelegung nennt entweder `profile` oder eigene Parameter mit `provider`,
  nie beides. Ein Profil ist vollständig (mindestens `provider`); unbekannte Parameter sind Fehler.
- **INV-02:** `by_complexity` ordnet nur `low`, `medium` und `high` zu, jeweils einem Profilnamen
  oder `session`. Ein Profilname, der in `llm.profiles` fehlt, ist ein Fehler von
  `sdd config validate` (Laufzeitprüfung, nicht Schema).
- **INV-03:** `mode: session` ist für `decomposer`, `test_author`, `implementer`, `reviewer` und
  `supervisor` erlaubt (bisher nur `supervisor`, CON-0199/SPEC-0053 FR-04 werden erweitert).
- **INV-04:** `pipeline.task_gates` enthält nur `tests`, `architecture`, `lint`;
  `pipeline.auto_steps` nur `holdout`, `finalize`, `automerge`. Die Reihenfolge von `auto_steps` ist
  unerheblich: `holdout` läuft immer vor S3, `finalize` und `automerge` danach.
- **INV-05:** Ein Session-Auftrag (`pending-work.json`) nennt Rolle, Task, erlaubte Pfade und
  Kontextquellen. Er enthält nie Inhalte aus `.sdd/holdout/` und keine API-Keys. Nach der
  Bestätigung wandert er nach `requests/<request_id>.json` (wie Entscheidungsanfragen, CON-0202
  INV-02); offen ist er genau dann, wenn `state.status` `awaiting_session` ist.
- **INV-06:** `reopen` ist ein S3-Command nach CON-0201 mit `task_ids` (mindestens einer) und
  `hint`; es ergänzt die an S3 erlaubten Commands (`accept_frs`, `halt`, `reopen`). Die Artefakte von
  CON-0201 und CON-0202 werden bei der Umsetzung additiv erweitert.

## Beispiele

**Gültig:**
```yaml
llm:
  profiles:
    lokal: {provider: openai-compat, base_url: "http://192.168.0.149:8080/v1", model: qwen}
    claude: {provider: claude-cli}
  roles:
    implementer:
      profile: claude
      by_complexity: {low: lokal, medium: lokal, high: session}
pipeline:
  task_gates: [tests, architecture]
  auto_steps: [holdout, finalize, automerge]
```

**Ungültig (und warum):**
```yaml
llm:
  roles:
    implementer: {profile: claude, provider: claude-cli, by_complexity: {extrem: lokal}}
```
→ `profile` und `provider` zugleich (INV-01), unbekannte Stufe `extrem` (INV-02).

## Validierung

- Schema: `.sdd/contracts/data/profile-rollenbelegung-session-auftrag-und-reopen.schema.json`.
- INV-02 (Profilnamen) prüft `sdd config validate`, INV-05 der Pipeline-Test (TST-0242).
