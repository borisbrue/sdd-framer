---
id: CON-0212
title: "Profile, Rollenbelegung, Session-Auftrag und reopen"
type: data
format: json-schema
spec: SPEC-0061
version: 0.3.0
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
  oder `session`. Eine fehlende Stufe fällt auf die übrige Belegung der Rolle zurück (`profile` bzw.
  eigene Parameter, sonst `legacy_component` wie in CON-0199 INV-04); eine Rolle darf deshalb auch
  nur `by_complexity` setzen. `by_complexity` wirkt nur für Rollen mit Task (`test_author`,
  `implementer`, `reviewer`); bei `decomposer` und `supervisor` wird es ignoriert und von
  `sdd config validate` als Warnung gemeldet. Ein Profilname, der in `llm.profiles` fehlt, ist ein
  Fehler von `sdd config validate` (Regelgruppe `llm.roles`/`llm.profiles`, ergänzt CON-0190).
  Schema-Prüfung und Profilauflösung erfolgen in `sdd config validate` und beim Start eines Runs,
  nicht in `load_config` (CON-0023 G-03 bleibt).
- **INV-03:** `mode: session` ist für `decomposer`, `test_author`, `implementer`, `reviewer` und
  `supervisor` erlaubt (bisher nur `supervisor`, CON-0199/SPEC-0053 FR-04 werden erweitert).
- **INV-04:** `pipeline.task_gates` enthält nur `tests`, `architecture`, `lint`;
  `pipeline.auto_steps` nur `holdout`, `finalize`, `automerge`. Die Reihenfolge von `auto_steps` ist
  unerheblich: `holdout` läuft immer vor S3, `finalize` und `automerge` danach.
- **INV-05:** Ein Session-Auftrag (`pending-work.json`) nennt Rolle, Task, erlaubte Pfade und
  Kontextquellen. Er enthält nie Inhalte aus `.sdd/holdout/` und keine API-Keys. Nach der
  Bestätigung wandert er nach `requests/<request_id>.json` (wie Entscheidungsanfragen, CON-0202
  INV-02). Er trägt `kind: work`; Entscheidungsanfragen tragen kein `kind`, damit ist das Archiv
  eindeutig. Offen ist er genau dann, wenn `state.status` `awaiting_session` ist; ein Run hat nie
  gleichzeitig einen offenen Auftrag und eine offene Entscheidungsanfrage. Das `status`-Enum von
  CON-0202 enthält `awaiting_session` bereits.
- **INV-06:** `reopen` ist ein S3-Command nach CON-0201 mit `task_ids` (mindestens einer) und
  `hint`; es ergänzt die an S3 erlaubten Commands (`accept_frs`, `halt`, `reopen`). Anders als
  `retry_with_hint` (S2, ein Task nach erschöpften Versuchen) öffnet es nach der Abnahme mehrere
  abgeschlossene Tasks; je Entscheidung gibt es genau ein Command. Die Zahl der Wiedereröffnungen
  ergibt sich aus `decisions.jsonl`. Die Artefakte von CON-0201 und CON-0202 werden additiv
  erweitert.
- **INV-07:** `llm.profiles`/`by_complexity` lösen den Registry-Gedanken von `llm_pool` (CON-0106,
  seit SPEC-0058 nicht mehr gelesen) ab; ein vorhandener `llm_pool` hat keinen Einfluss auf die
  Pipeline.

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

## Seit SPEC-0055 (0.3.0)

Profil-Schlüssel `requests_per_minute` (Zahl > 0): Höchstzahl der Aufrufe je Minute an den Endpunkt des Profils (SPEC-0055 FR-11, CON-0219 INV-08).
