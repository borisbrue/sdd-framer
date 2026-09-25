---
id: CON-0207
title: "Usage-Erfassung: Provider, Decorator, Kontext und Senken"
type: behavior
format: gherkin
spec: SPEC-0060
version: 0.2.0
status: approved
artifact: ".sdd/contracts/behavior/usage-erfassung-provider-decorator-kontext-und-senken.feature"
tests: ["TST-0236"]
---

# Contract: Usage-Erfassung: Provider, Decorator, Kontext und Senken

> **Spec:** SPEC-0060 · **Typ:** Verhalten (Gherkin) · **Status:** approved

## Zweck

Legt fest, wie jeder LLM-Aufruf zu genau einem Usage-Datensatz wird (SPEC-0060 FR-01 bis FR-10):
Abbildung der Provider-Antworten, Umhüllung durch die Factory, Aufrufkontext, Senken und
Fehlertoleranz.

## Garantien

Die Szenarien im Artifact (`.sdd/contracts/behavior/usage-erfassung-provider-decorator-kontext-und-senken.feature`)
sind **ausführbare Spezifikation**. Jedes Szenario MUSS durch einen automatisierten Test (pytest)
abgedeckt sein.

## Schnittstellen

| Element | Vertrag |
|---------|---------|
| `UsageMetadata` | `input_tokens`, `output_tokens`, `cache_creation_tokens`, `cache_read_tokens`, `model`, `estimated`, `reasoning_tokens`, `finish_reason`, `latency_ms`, `server_model`, `source` |
| `sdd_cli.llm.usage.usage_context(**kw)` | Kontextmanager; verschachtelt ergänzt/überschreibt Schlüssel; je Thread/Task getrennt |
| `sdd_cli.llm.usage.UsageSink` | `record(record: UsageRecord) -> None` |
| `sdd_cli.llm.usage.register_sink(sink)` | registriert eine Senke dauerhaft für den Prozess (z. B. Benchmark-Export); die SQLite-Senke ist vorregistriert |
| `sdd_cli.llm.usage.use_sinks(sinks)` | Kontextmanager, der die registrierten Senken vorübergehend ersetzt (Tests) |
| Factory | `get_completion_provider`/`get_code_gen_provider` liefern umhüllte Provider mit unveränderter Schnittstelle |

## Invarianten

- **INV-01:** Jeder Aufruf eines Providers aus der Factory erzeugt genau einen `UsageRecord`, auch
  wenn der Provider eine Ausnahme wirft (dann `finish_reason: error`, `source: unavailable`).
- **INV-02:** Jeder Provider liefert ein `UsageMetadata`-Objekt, nie `None`. Nicht gemeldete
  Zählwerte sind `None` (bzw. `input_tokens`/`output_tokens` 0 bei `source: unavailable`); `0` bei
  `reasoning_tokens` bedeutet „gemeldet, kein Reasoning“ (CON-0206 INV-05).
- **INV-06:** Senken und Kontext sind prozessweiter Zustand des Moduls `sdd_cli.llm.usage`
  (bewusste Entscheidung: kein Durchreichen durch Provider-Signaturen). Er wird ausschließlich über
  `register_sink`, `use_sinks` und `usage_context` verändert.
- **INV-03:** Der Decorator ändert weder Ergebnis noch Ausnahme des umhüllten Providers.
- **INV-04:** Fällt eine Senke aus, erhalten alle übrigen Senken den Datensatz; der Aufruf gilt
  nicht als gescheitert; ein Warnhinweis wird geloggt.
- **INV-05:** Die Erfassung setzt keinen API-Key voraus und speichert keinen Prompttext.

## Begriffe

| Begriff | Definition |
|---------|------------|
| UsageRecord | Usage eines Aufrufs plus `component`, `model`, Dauer, Zeitstempel und Aufrufkontext |
| Senke | Empfänger von UsageRecords; Standard ist die SQLite-Senke für `token_usage` |
