---
id: CON-0031
project: PRJ-0001
title: "HuggingFaceCompletionProvider – Interface-Konformität und Betriebsmodi"
type: behavior
format: markdown
spec: SPEC-0013
version: 0.1.0
status: active
artifact: "tool/sdd_cli/llm/providers/huggingface.py"
tests: ["TST-0068"]
---

# Contract: HuggingFaceCompletionProvider – Interface-Konformität und Betriebsmodi

> **Spec:** SPEC-0013 · **Typ:** Verhalten · **Status:** implemented

## Zweck

Spezifiziert `HuggingFaceCompletionProvider` als vollständige Implementierung des
`CompletionProvider`-Protokolls (CON-0022) für drei Betriebsmodi: `serverless`,
`dedicated` und `local`.

## Garantien

### G-01: Interface-Konformität

`HuggingFaceCompletionProvider` implementiert `CompletionProvider` vollständig:

```python
def complete(
    self,
    prompt: str,
    *,
    max_tokens: int = 512,
    system_prompt: str | None = None,
    timeout: int | None = None,
) -> CompletionResult: ...
```

- Gibt immer `CompletionResult` zurück, niemals `None`
- Wirft bei Fehler immer eine Exception
- `isinstance(provider, CompletionProvider)` ist `True` (`@runtime_checkable`)

### G-02: Serverless-Modus

- Nutzt `huggingface_hub.InferenceClient(token=hf_token)`
- `InferenceClient` wird **einmalig im Konstruktor** erzeugt (kein Re-Instantiieren pro Aufruf)
- Ruft `client.text_generation(prompt, model=model_id, max_new_tokens=max_tokens)` auf
- `temperature=0` → kein `do_sample`/`temperature`-Parameter (greedy decoding)
- `temperature>0` → `do_sample=True` und `temperature=<value>` werden übergeben

### G-03: Dedicated-Modus

- Nutzt `huggingface_hub.InferenceClient(base_url=endpoint_url, token=hf_token)`
- Kein `model`-Parameter in `text_generation()` (Endpoint impliziert das Modell)

### G-04: Local-Modus

- Nutzt `transformers.pipeline("text-generation", model=model_id)` (lazy import)
- Pipeline wird beim **ersten `complete()`-Aufruf** geladen und danach gecacht
- Kein API-Key erforderlich; kein Netzwerkzugriff wenn Modell im HF-Cache vorhanden
- `return_full_text=False` → Antwort enthält nur den generierten Teil, nicht den Prompt

### G-05: System-Prompt-Behandlung

Für `serverless` und `dedicated`:
```
<system>
{system_prompt}
</system>

{user_prompt}
```

Für `local` mit Chat-Template (Instruct-Modelle):
```python
tokenizer.apply_chat_template(
    [{"role": "system", ...}, {"role": "user", ...}],
    tokenize=False,
    add_generation_prompt=True,
)
```
Erkennung: `tokenizer.chat_template is not None`. Kein Chat-Template → XML-Präfix wie oben.

### G-06: Token-Schätzung (UsageMetadata)

HF `text_generation()` liefert keine Token-Counts. Der Provider schätzt:
- `input_tokens = len(full_prompt.split())`
- `output_tokens = len(generated_text.split())`
- `usage.estimated = True` (immer gesetzt)

### G-07: Fehlerbehandlung

| Fehlerfall                                      | Exception                                |
|-------------------------------------------------|------------------------------------------|
| HTTP 503 (Modell lädt)                          | `RuntimeError` mit "503" im Message      |
| API antwortet ohne `generated_text`             | `ValueError` mit Antwort-Auszug          |
| `hf_mode: local` + OSError beim Laden          | `RuntimeError` mit Cache-Hinweis         |
| `huggingface_hub` nicht installiert             | `RuntimeError("pip install 'sdd-cli[huggingface]'")`   |
| `transformers` nicht installiert (local)        | `RuntimeError("pip install 'sdd-cli[huggingface-local]'")` |

## Invarianten

- **INV-01:** Kein `huggingface_hub`- oder `transformers`-Import auf Modul-Ebene (lazy imports)
- **INV-02:** `hf_token` erscheint nie in Logs, Subprocess-Argumenten oder Rich-Output
- **INV-03:** `complete()` ist stateless; der gecachte `InferenceClient` und die Pipeline sind thread-safe bezüglich Lesezugriffen
