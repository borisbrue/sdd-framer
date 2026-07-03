---
id: TST-0219
title: Config-Validierungsregeln – Pflichtfelder, Provider-Enum, Provider-Konsistenz
level: unit
spec: SPEC-0052
contract: CON-0190
status: planned
framework: pytest
artifact: tests/unit/test_con0190_config_validation_rules.py
tags:
- config
- validator
- unit
---

# Test: Config-Validierungsregeln – Pflichtfelder, Provider-Enum, Provider-Konsistenz

> **Level:** unit · **Spec:** SPEC-0052 · **Contract:** CON-0190 · **Status:** planned

## Was wird geprüft?

Alle Validierungsregeln des `ConfigValidator` isoliert ohne CLI-Aufruf:
- Pflichtfelder (version, project.name, project.description)
- Provider-Enum (erlaubte Provider-Namen)
- openai-compat-Konsistenz (base_url + model Pflicht)
- huggingface-Konsistenz (hf_token bei serverless/dedicated Pflicht)
- anthropic-Konsistenz (fehlender api_key → Warning, kein Error)
- INV-04: kein Abbruch bei erstem Fehler, alle Checks laufen durch

## Vorbedingungen

- `config_validator.py` mit `ConfigValidator`-Klasse und `ConfigIssue`-Dataclass vorhanden
- Keine externen Ressourcen (LM Studio, Anthropic API) werden kontaktiert

## Ablauf

1. Dict mit minimaler/fehlerhafter Config als Input konstruieren
2. `ConfigValidator(raw_config).validate()` aufrufen
3. Rückgabe-Liste von `ConfigIssue(level, path, message)` prüfen

## Erwartetes Ergebnis

- Fehlende Pflichtfelder → `ConfigIssue(level="error", path="<feldpfad>")`
- Ungültiger Provider → `ConfigIssue(level="error")` mit erlaubten Werten in message
- openai-compat ohne base_url → `ConfigIssue(level="error", path="llm.completion.base_url")`
- anthropic ohne api_key → `ConfigIssue(level="warning")`
- Valide Config → leere Liste

## Negativfälle / Edge Cases

- Mehrere Fehler gleichzeitig → alle werden zurückgegeben (kein Early-Exit)
- Leere Config (`{}`) → Fehler für alle Pflichtfelder
- `llm`-Block fehlt komplett → kein Crash, nur Pflichtfeld-Fehler

## Verknüpfung mit Contract

- [x] FR-01: Pflichtfeld-Check
- [x] FR-02: Provider-Enum-Check
- [x] FR-03: openai-compat-Konsistenz
- [x] FR-04: huggingface-Konsistenz
- [x] FR-05: anthropic-Konsistenz (Warning)
- [x] INV-04: kein Abbruch bei Fehler
