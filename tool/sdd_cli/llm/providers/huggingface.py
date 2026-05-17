"""HuggingFaceCompletionProvider – HF Inference API (serverless, dedicated, local)."""
from __future__ import annotations

from ..base import CompletionResult, UsageMetadata

_SYSTEM_TMPL = "<system>\n{system}\n</system>\n\n{user}"


class HuggingFaceCompletionProvider:
    """CompletionProvider für die Hugging Face Inference API und lokale Modelle.

    hf_mode:
        serverless – HF Serverless Inference (Standard)
        dedicated  – HF Dedicated Endpoints (privates Deployment)
        local      – lokale Ausführung via transformers.pipeline (kein API-Key erforderlich)
    """

    def __init__(
        self,
        model: str | None = None,
        hf_token: str | None = None,
        hf_mode: str = "serverless",
        endpoint_url: str | None = None,
        temperature: float = 0.0,
    ) -> None:
        self._model = model
        self._hf_token = hf_token
        self._hf_mode = hf_mode
        self._endpoint_url = endpoint_url
        self._temperature = temperature
        self._pipeline = None

        # InferenceClient wird einmalig im Konstruktor erzeugt (FR-02/FR-03)
        if hf_mode in ("serverless", "dedicated"):
            self._client = self._build_inference_client()
        else:
            self._client = None

    def _build_inference_client(self):
        try:
            from huggingface_hub import InferenceClient
        except ImportError as exc:
            raise RuntimeError(
                "Das huggingface_hub-Paket ist nicht installiert. "
                "Führe `pip install 'sdd-cli[huggingface]'` aus."
            ) from exc

        if self._hf_mode == "dedicated":
            return InferenceClient(base_url=self._endpoint_url, token=self._hf_token)
        return InferenceClient(token=self._hf_token)

    def _build_prompt(self, prompt: str, system_prompt: str | None) -> str:
        if system_prompt:
            return _SYSTEM_TMPL.format(system=system_prompt, user=prompt)
        return prompt

    def complete(
        self,
        prompt: str,
        *,
        max_tokens: int = 512,
        system_prompt: str | None = None,
        timeout: int | None = None,
    ) -> CompletionResult:
        if self._hf_mode == "local":
            return self._complete_local(prompt, max_tokens=max_tokens, system_prompt=system_prompt)
        return self._complete_api(prompt, max_tokens=max_tokens, system_prompt=system_prompt)

    def _complete_api(
        self, prompt: str, *, max_tokens: int, system_prompt: str | None
    ) -> CompletionResult:
        full_prompt = self._build_prompt(prompt, system_prompt)

        gen_kwargs: dict = {"max_new_tokens": max_tokens}
        if self._temperature > 0:
            gen_kwargs["temperature"] = self._temperature
            gen_kwargs["do_sample"] = True

        if self._hf_mode == "serverless":
            gen_kwargs["model"] = self._model

        try:
            result = self._client.text_generation(full_prompt, **gen_kwargs)
        except Exception as exc:
            msg = str(exc)
            if "503" in msg:
                raise RuntimeError(
                    f"HF Serverless API: Modell wird noch geladen (503). "
                    f"Bitte kurz warten und erneut versuchen. Details: {msg}"
                ) from exc
            raise

        generated = result if isinstance(result, str) else getattr(result, "generated_text", None)
        if generated is None:
            raise ValueError(
                f"Unerwartetes Antwortformat der HF API: 'generated_text' fehlt. "
                f"Antwort: {str(result)[:200]}"
            )

        usage = UsageMetadata(
            input_tokens=len(full_prompt.split()),
            output_tokens=len(generated.split()),
            model=self._model or "",
            estimated=True,
        )
        return CompletionResult(text=generated.strip(), usage=usage)

    def _complete_local(
        self, prompt: str, *, max_tokens: int, system_prompt: str | None
    ) -> CompletionResult:
        try:
            from transformers import pipeline as hf_pipeline
        except ImportError as exc:
            raise RuntimeError(
                "Das transformers-Paket ist nicht installiert. "
                "Führe `pip install 'sdd-cli[huggingface-local]'` aus."
            ) from exc

        if self._pipeline is None:
            try:
                self._pipeline = hf_pipeline("text-generation", model=self._model)
            except OSError as exc:
                raise RuntimeError(
                    f"Modell {self._model!r} nicht im Cache und kein Netzwerkzugriff verfügbar. "
                    "Lade das Modell zuerst herunter oder prüfe die Netzwerkverbindung."
                ) from exc

        tokenizer = getattr(self._pipeline, "tokenizer", None)
        has_chat_template = (
            tokenizer is not None
            and hasattr(tokenizer, "apply_chat_template")
            and getattr(tokenizer, "chat_template", None) is not None
        )

        if has_chat_template and system_prompt:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ]
            full_prompt = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
        else:
            full_prompt = self._build_prompt(prompt, system_prompt)

        gen_kwargs: dict = {"max_new_tokens": max_tokens, "return_full_text": False}
        if self._temperature > 0:
            gen_kwargs["temperature"] = self._temperature
            gen_kwargs["do_sample"] = True

        output = self._pipeline(full_prompt, **gen_kwargs)
        generated = output[0]["generated_text"]

        usage = UsageMetadata(
            input_tokens=len(full_prompt.split()),
            output_tokens=len(generated.split()),
            model=self._model or "",
            estimated=True,
        )
        return CompletionResult(text=generated.strip(), usage=usage)
