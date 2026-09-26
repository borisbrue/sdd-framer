---
id: CON-0207
title: "Usage-Erfassung: Provider, Decorator, Kontext und Senken"
type: behavior
format: gherkin
spec: SPEC-0060
version: 0.3.1
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
| `CompletionProvider.complete()` | liefert `CompletionResult(text, usage)`; `usage` ist der Rückkanal der Metadaten und ab SPEC-0060 nie `None`. Das ersetzt die Signatur `-> str` aus CON-0022; der Text bleibt wie in CON-0022 G-02 nur `result` der claude-Hülle, die Usage wird zusätzlich aus derselben Hülle gelesen |
| `CodeGenProvider.generate()` | entfallen mit SPEC-0062 (CodeGen-Pfad entfernt, CON-0024 deprecated) |
| `UsageMetadata` | `input_tokens`, `output_tokens`, `cache_creation_tokens`, `cache_read_tokens`, `model`, `estimated`, `reasoning_tokens`, `finish_reason`, `latency_ms`, `server_model`, `source` |
| `sdd_cli.llm.usage.usage_context(**kw)` | Kontextmanager; verschachtelt ergänzt/überschreibt Schlüssel; je Thread/Task getrennt |
| `sdd_cli.llm.usage.UsageSink` | `record(record: UsageRecord) -> None` |
| `sdd_cli.llm.usage.register_sink(sink)` | registriert eine Senke dauerhaft für den Prozess (z. B. Benchmark-Export); die SQLite-Senke ist vorregistriert |
| `sdd_cli.llm.usage.use_sinks(sinks)` | Kontextmanager, der die registrierten Senken vorübergehend ersetzt (Tests) |
| Factory | `get_completion_provider`/`get_role_provider` liefern umhüllte Provider mit unveränderter Schnittstelle (`get_code_gen_provider` entfallen mit SPEC-0062) |

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
- **INV-07:** (entfallen mit SPEC-0062, galt bis dahin:) Ein `generate()`-Aufruf eines CodeGen-Providers erzeugt genau einen `UsageRecord`;
  macht der Provider intern mehrere Modellaufrufe, summiert er deren Zählwerte. Kann er das nicht,
  meldet er `source: unavailable`.
- **INV-08:** Der Decorator umhüllt jeden Provider der Factory, auch `huggingface`
  (CON-0031). Grob gezählte Werte melden `source: estimated`; nicht gemeldete Felder wie
  `reasoning_tokens` sind `None`, nicht 0.
- **INV-09:** Die SQLite-Senke schreibt Kontextschlüssel mit eigener Spalte (`spec_id`, `task_id`,
  `task_label`, `run_id`, `agent_type`) in diese Spalten und nur die übrigen nach `context_json`
  (CON-0206 INV-03). `task_id`/`task_label` und `agent_type` kommen damit aus `usage_context`; es
  gibt keine zweite Migration dieser Spalten. `model` ist die konfigurierte Modell-ID,
  `server_model` die gemeldete (CON-0206 INV-07).
- **INV-10:** Zusammenfassungen behandeln `source` wie CON-0206 INV-06: `unavailable` zählt nicht
  in Summen, `estimated` schon.

## Abhängigkeiten

CON-0022 (Provider-Protokoll, Rückgabetyp hier präzisiert), CON-0024 (CodeGen), CON-0031
(HuggingFace), CON-0041/CON-0121/CON-0129 (Spalten von `token_usage`, über CON-0206), CON-0013
(Analyzer: dessen einmalige Completion-Aufrufe laufen nach SPEC-0060 FR-06 über die Factory;
interaktive Claude-Code-Sitzungen sind keine Provider-Aufrufe und werden nicht erfasst).

## Begriffe

| Begriff | Definition |
|---------|------------|
| UsageRecord | Usage eines Aufrufs plus `component`, `model`, Dauer, Zeitstempel und Aufrufkontext |
| Senke | Empfänger von UsageRecords; Standard ist die SQLite-Senke für `token_usage` |
