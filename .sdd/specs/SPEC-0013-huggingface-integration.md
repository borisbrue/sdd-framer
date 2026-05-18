---
id: SPEC-0013
title: Hugging Face Provider – LLM-Anbindung über die HF Inference API
status: implemented
owner: Boris
created: 2026-05-14
updated: 2026-05-14
version: 0.1.0
priority: medium
tags:
- hugging-face
- provider-pattern
- llm
- inference-api
- open-source-models
depends_on:
- SPEC-0008
contracts:
- CON-0031
- CON-0032
- CON-0033
tests:
- TST-0068
adrs: []
---
# Hugging Face Provider – LLM-Anbindung über die HF Inference API

> **Status:** implemented · **Owner:** Boris · **Version:** 0.1.0

## 1. Kontext & Motivation

SPEC-0008 etabliert eine SOLID-konforme LLM-Provider-Abstraktionsschicht mit drei
Implementierungen: Anthropic SDK, Claude CLI und OpenAI-compatible. Hugging Face ist ein
weiterer wichtiger Integrationspunkt:

- **Open-Source-Modelle:** Viele leistungsfähige Modelle (Llama, Mistral, Falcon, CodeLlama)
  sind auf HF kostenlos oder günstig über die Inference API verfügbar
- **Kostenkontrolle:** HF Serverless Inference hat ein großzügiges Free Tier für kleinere
  Modelle – attraktiv für Evaluator und Analyzer (kurze Completions)
- **Privacy-Option:** HF Dedicated Endpoints ermöglichen private Deployments
- **Ökosystem:** HF `transformers`-Library erlaubt vollständig lokale Ausführung ohne API
  (für höchste Privacy-Anforderungen)

Die Integration folgt dem OCP (Open/Closed Principle) aus SPEC-0008: neuer Provider = neue
Klasse in `providers/`, keine Änderung an bestehenden Dateien.

## 2. Zielsetzung

**Primärziel:**
Hugging Face (Serverless Inference API, Dedicated Endpoints und lokal via `transformers`)
als `provider: huggingface` in der SDD-LLM-Konfiguration verfügbar machen.

**Erfolgskriterien (messbar):**
- [ ] `provider: huggingface` in `.sdd/config.yaml` funktioniert für Evaluator, Analyzer und AI-Routes
- [ ] Serverless Inference API (hosted) und Dedicated Endpoints werden unterstützt
- [ ] Optionaler lokaler Modus via `huggingface_hub`-Library (kein API-Key erforderlich)
- [ ] `HuggingFaceCompletionProvider` implementiert `CompletionProvider` aus SPEC-0008
- [ ] Kein bestehender Code wird geändert (OCP-Konformität)
- [ ] `pip install 'sdd-cli[huggingface]'` installiert alle benötigten Dependencies

**Nicht-Ziele (explizit):**
- Kein `CodeGenProvider` für HF (Code-Gen erfordert agentische Datei-Schreibung; HF-Modelle
  ohne Funktionsaufruf-Unterstützung sind dafür ungeeignet – Claude CLI bleibt Default)
- Kein Fine-Tuning oder Model-Training
- Kein HF Dataset-Zugriff
- Keine Streaming-Unterstützung (konsistent mit allen anderen Providern)

## 3. Architektur (Erweiterung SPEC-0008)

### 3.1 Neue Provider-Klasse

```
tool/sdd_cli/llm/providers/
├── __init__.py
├── anthropic.py
├── claude_cli.py
├── openai_compat.py
└── huggingface.py          ← NEU
```

### 3.2 HuggingFace-Betriebsmodi

| Modus           | Konfiguration                          | Interne Implementierung                        |
|-----------------|----------------------------------------|------------------------------------------------|
| `serverless`    | `model` + `hf_token`                  | `huggingface_hub.InferenceClient.text_generation()` |
| `dedicated`     | `endpoint_url` + `hf_token`           | `InferenceClient(endpoint_url=...).text_generation()` |
| `local`         | `model` (lokal gecacht), kein Token   | `transformers.pipeline("text-generation", ...)`    |

### 3.3 Provider-Konfiguration

```yaml
# .sdd/config.yaml
llm:
  completion:
    provider: huggingface
    model: "mistralai/Mistral-7B-Instruct-v0.3"
    hf_token: "${HF_TOKEN}"              # Pflicht für serverless/dedicated; optional für local
    hf_mode: serverless                  # serverless | dedicated | local; Default: serverless
    # endpoint_url: "https://..."        # Pflicht bei hf_mode: dedicated
    # temperature: 0.0                   # Default 0.0
    # max_new_tokens: 512                # Alias für max_tokens; Default 512
```

### 3.4 System-Prompt-Behandlung

HF-Modelle haben kein natives System-Prompt-Feld in der Text-Generation-API.
Umsetzung analog zu `ClaudeCliCompletionProvider`:

```
<system>
{system_prompt}
</system>

{user_prompt}
```

Bei Modellen mit Chat-Template (z.B. Instruct-Varianten) wird stattdessen das
HF Chat-Template-Format genutzt, wenn erkennbar:

```python
messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": prompt}
]
tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
```

## 4. Funktionale Anforderungen

### Provider-Implementierung

- **FR-01:** `HuggingFaceCompletionProvider` implementiert `CompletionProvider` (SPEC-0008 §4.1)
  vollständig, einschließlich `max_tokens`, `system_prompt` und `timeout`-Parameter.
- **FR-02:** Im `serverless`-Modus wird `huggingface_hub.InferenceClient` genutzt (lazy import).
  `InferenceClient` wird einmalig im Konstruktor erzeugt (kein Re-Instantiieren pro Aufruf).
- **FR-03:** Im `dedicated`-Modus wird `InferenceClient(base_url=endpoint_url)` genutzt.
  `endpoint_url` ist Pflicht; fehlt es → `ValueError` in Factory.
- **FR-04:** Im `local`-Modus wird `transformers.pipeline` genutzt (lazy import). Modell wird
  beim ersten Aufruf von `pipeline()` aus dem HF-Cache geladen; kein Netzwerkzugriff wenn
  das Modell bereits gecacht ist.
- **FR-05:** `result.usage` enthält `input_tokens` und `output_tokens` wenn die API diese
  liefert; andernfalls schätzt der Provider über `len(prompt.split())` (Fallback, markiert
  als `estimated=True` in `UsageMetadata`).
- **FR-06:** Kein `HuggingFaceCodeGenProvider` – Factory wirft `ValueError` wenn `huggingface`
  als `code_gen`-Provider konfiguriert wird.

### Factory-Integration

- **FR-07:** `factory.py` erhält einen Eintrag für `provider: huggingface` →
  `HuggingFaceCompletionProvider`. Keine Änderung an den bestehenden Provider-Zweigen.
- **FR-08:** Fehlt `huggingface_hub` bei `provider: huggingface` → `RuntimeError("pip install
  'sdd-cli[huggingface]'")`. Fehlt `transformers` bei `hf_mode: local` →
  `RuntimeError("pip install 'sdd-cli[huggingface-local]'")`.

### Dependencies

- **FR-09:** `pyproject.toml` erhält neue optionale Dependency-Gruppen:
  ```toml
  [project.optional-dependencies]
  huggingface = ["huggingface_hub>=0.23"]
  huggingface-local = ["huggingface_hub>=0.23", "transformers>=4.40", "torch>=2.0"]
  ```

### Konfigurationsvalidierung

- **FR-10:** Pflichtfelder je Modus:
  - `serverless`: `model` (Pflicht), `hf_token` (Pflicht)
  - `dedicated`: `endpoint_url` (Pflicht), `hf_token` (Pflicht), `model` optional
  - `local`: `model` (Pflicht), `hf_token` optional
- **FR-11:** `hf_token` unterstützt `${ENV_VAR}`-Syntax analog zu SPEC-0008 §8 (Security).

## 5. Nicht-funktionale Anforderungen

| Kategorie       | Anforderung                                                                               |
|-----------------|-------------------------------------------------------------------------------------------|
| OCP-Konformität | `evaluator.py`, `analyzer.py`, `orchestrator.py`, `routes/ai.py` werden **nicht** geändert |
| Lazy Imports    | Kein `huggingface_hub`- oder `transformers`-Import auf Modul-Ebene                       |
| Testbarkeit     | Alle externen API-Aufrufe mockbar (kein echter HF-Aufruf in Unit-Tests)                  |
| Security        | `hf_token` erscheint nie in Logs, Subprocess-Argumenten oder Rich-Output                 |
| Performance     | `local`-Modus: Modell-Ladezeit beim ersten Aufruf akzeptiert; danach gecacht             |
| Backwards-Compat | Fehlt `huggingface`-Konfiguration → kein Effekt auf bestehende Provider                |

## 6. Akzeptanzkriterien (Gherkin)

```gherkin
Feature: Hugging Face als LLM-Provider

  Scenario: Evaluator nutzt HF Serverless Inference
    Given llm.evaluator.provider ist huggingface in config.yaml
    And llm.evaluator.model ist "mistralai/Mistral-7B-Instruct-v0.3"
    And HF_TOKEN ist als Env-Var gesetzt
    When run_evaluation() ausgeführt wird
    Then werden LLM-Anfragen an die HF Inference API gesendet
    And kein ANTHROPIC_API_KEY wird benötigt

  Scenario: Dedicated Endpoint Nutzung
    Given llm.completion.provider ist huggingface
    And llm.completion.hf_mode ist dedicated
    And llm.completion.endpoint_url ist "https://xyz.endpoints.huggingface.cloud"
    When get_completion_provider(config) aufgerufen wird
    Then wird HuggingFaceCompletionProvider mit endpoint_url initialisiert

  Scenario: Fehlende huggingface_hub-Dependency
    Given llm.completion.provider ist huggingface
    And huggingface_hub ist nicht installiert
    When get_completion_provider(config) aufgerufen wird
    Then wird RuntimeError mit "pip install 'sdd-cli[huggingface]'" geworfen

  Scenario: huggingface als code_gen-Provider abgelehnt
    Given llm.code_gen.provider ist huggingface in config.yaml
    When get_code_gen_provider(config) aufgerufen wird
    Then wird ValueError geworfen

  Scenario: Kein Breaking Change für bestehende Anthropic-Konfiguration
    Given llm.completion.provider ist anthropic in config.yaml
    When get_completion_provider(config) aufgerufen wird
    Then wird AnthropicCompletionProvider zurückgegeben
    And HuggingFaceCompletionProvider wird nicht instantiiert

  Scenario: HF_TOKEN als Env-Var-Referenz
    Given llm.completion.hf_token ist "${MY_HF_TOKEN}"
    And MY_HF_TOKEN ist nicht in os.environ gesetzt
    When get_completion_provider(config) aufgerufen wird
    Then wird RuntimeError mit Hinweis auf MY_HF_TOKEN geworfen
```

## 7. Edge Cases & Fehlerfälle

- **E-01:** HF Serverless API gibt HTTP 503 (Modell lädt gerade) → Provider wirft Exception mit klarer Meldung; Evaluator-Fehlerbehandlung fängt ab.
- **E-02:** `hf_mode: local` + Modell nicht im Cache + kein Netzwerk → `transformers` wirft `OSError`; Provider wraps in `RuntimeError` mit Hinweis.
- **E-03:** Modell antwortet nicht im erwarteten Format (kein `generated_text`-Feld) → Provider wirft `ValueError` mit API-Antwort-Auszug.
- **E-04:** `max_tokens` größer als das Modell-Maximum → HF-API gibt Fehler; Provider propagiert Exception.
- **E-05:** `dedicated` ohne `endpoint_url` → `ValueError` in Factory (wie SPEC-0008 E-01).
- **E-06:** `local`-Modus ohne `torch` installiert → `RuntimeError("pip install 'sdd-cli[huggingface-local]'")`.

## 8. Contracts (was wird garantiert)

| Contract-ID | Typ      | Was wird garantiert?                                                     |
|-------------|----------|--------------------------------------------------------------------------|
| TBD         | behavior | `HuggingFaceCompletionProvider.complete()` – Interface-Konformität mit SPEC-0008 `CompletionProvider` |
| TBD         | data     | Schema der `huggingface`-Konfigurationssektion (Pflichtfelder je Modus) |
| TBD         | behavior | Factory: `huggingface` als `code_gen`-Provider → `ValueError`           |

## 9. Tests (wie wird verifiziert)

| Test-ID | Level | Was prüft der Test?                                                                           |
|---------|-------|-----------------------------------------------------------------------------------------------|
| TBD     | unit  | `HuggingFaceCompletionProvider.complete()` serverless: Request korrekt (Mock InferenceClient) |
| TBD     | unit  | `HuggingFaceCompletionProvider.complete()` dedicated: endpoint_url wird genutzt (Mock)        |
| TBD     | unit  | system_prompt: korrekte Präfix-Formatierung im Prompt                                         |
| TBD     | unit  | `result.usage`: Tokens befüllt aus API-Antwort; Fallback auf Schätzung wenn nicht vorhanden  |
| TBD     | unit  | Factory: `huggingface` als `code_gen`-Provider → `ValueError`                                |
| TBD     | unit  | Factory: fehlende `huggingface_hub`-Dependency → `RuntimeError` mit pip-Hinweis              |
| TBD     | unit  | `hf_token: "${MY_HF_TOKEN}"` und Variable nicht gesetzt → `RuntimeError`                     |
| TBD     | unit  | OCP: Bestehende Factory-Zweige (anthropic, claude-cli, openai-compat) unverändert             |

## 10. Offene Fragen

- [ ] Soll `hf_mode: local` mit `device: cuda` konfigurierbar sein (GPU-Beschleunigung)?
- [ ] Wie wird mit Rate-Limiting der HF Serverless API umgegangen (429-Responses)? Automatisches Retry mit Backoff?
- [ ] Soll die `model`-ID bei `serverless`-Modus auf bekannte Instruct-Modelle eingeschränkt werden, oder ist jedes Text-Generation-Modell erlaubt?
- [ ] Wie verhält sich `UsageMetadata.estimated=True` im Kontext von SPEC-0011 (Kostenschätzung)? Geschätzte Token-Counts sollten anders gewichtet werden.

## 11. Änderungshistorie

| Datum      | Version | Autor | Änderung              |
|------------|---------|-------|-----------------------|
| 2026-05-14 | 0.1.0   | Boris | Initiale Erstellung   |
