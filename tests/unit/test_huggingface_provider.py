"""Unit-Tests für SPEC-0013 – HuggingFace Provider (TST-XXXX)."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tool"))

from sdd_cli.llm.base import CompletionResult, UsageMetadata
from sdd_cli.llm.factory import get_code_gen_provider, get_completion_provider


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_config(raw: dict):
    from sdd_cli.config import SddConfig
    return SddConfig(root=Path("/tmp"), raw=raw)


def _make_hf_module(generated_text: str = "result text"):
    """Erzeugt ein Mock-huggingface_hub-Modul mit InferenceClient."""
    mock_client = MagicMock()
    mock_client.text_generation.return_value = generated_text
    mock_hf_hub = MagicMock()
    mock_hf_hub.InferenceClient.return_value = mock_client
    return mock_hf_hub, mock_client


# ─── Provider-Klasse: serverless ──────────────────────────────────────────────

class TestHuggingFaceCompletionProviderServerless:
    def _make_provider(self, temperature: float = 0.0):
        from sdd_cli.llm.providers.huggingface import HuggingFaceCompletionProvider
        mock_hf_hub, _ = _make_hf_module()
        with patch.dict("sys.modules", {"huggingface_hub": mock_hf_hub}):
            provider = HuggingFaceCompletionProvider(
                model="mistralai/Mistral-7B-Instruct-v0.3",
                hf_token="hf_test",
                hf_mode="serverless",
                temperature=temperature,
            )
        return provider, mock_hf_hub

    def test_complete_sends_correct_request(self):
        """complete() sendet model und max_new_tokens an text_generation (serverless)."""
        provider, mock_hf_hub = self._make_provider()
        mock_client = mock_hf_hub.InferenceClient.return_value

        result = provider.complete("was ist Python?", max_tokens=256)

        mock_client.text_generation.assert_called_once()
        call_args, call_kwargs = mock_client.text_generation.call_args
        assert call_args[0] == "was ist Python?" or call_kwargs.get("prompt") == "was ist Python?"
        assert call_kwargs.get("max_new_tokens") == 256
        assert call_kwargs.get("model") == "mistralai/Mistral-7B-Instruct-v0.3"

    def test_complete_returns_completion_result(self):
        """complete() gibt CompletionResult mit usage zurück."""
        provider, _ = self._make_provider()
        mock_client = _  # get fresh mock
        provider._client.text_generation.return_value = "generated answer"

        result = provider.complete("frage")

        assert isinstance(result, CompletionResult)
        assert result.text == "generated answer"
        assert result.usage is not None
        assert result.usage.estimated is True
        assert result.usage.model == "mistralai/Mistral-7B-Instruct-v0.3"

    def test_complete_usage_is_estimated_word_count(self):
        """usage.input_tokens und output_tokens werden per Wörter-Schätzung befüllt."""
        provider, _ = self._make_provider()
        provider._client.text_generation.return_value = "eins zwei drei"

        result = provider.complete("vier fünf")

        assert result.usage.input_tokens == len("vier fünf".split())
        assert result.usage.output_tokens == len("eins zwei drei".split())
        assert result.usage.estimated is True

    def test_system_prompt_prepended_as_xml(self):
        """system_prompt wird als <system>...</system>\\n\\n vorangestellt."""
        provider, _ = self._make_provider()
        provider._client.text_generation.return_value = "ok"

        provider.complete("user msg", system_prompt="sei hilfreich")

        call_args, _ = provider._client.text_generation.call_args
        full_prompt = call_args[0]
        assert full_prompt.startswith("<system>\nsei hilfreich\n</system>\n\n")
        assert full_prompt.endswith("user msg")

    def test_temperature_zero_no_do_sample(self):
        """temperature=0 → kein do_sample/temperature im Request (greedy decoding)."""
        provider, _ = self._make_provider(temperature=0.0)
        provider._client.text_generation.return_value = "ok"

        provider.complete("prompt")

        _, call_kwargs = provider._client.text_generation.call_args
        assert "do_sample" not in call_kwargs
        assert "temperature" not in call_kwargs

    def test_temperature_nonzero_sets_do_sample(self):
        """temperature > 0 → do_sample=True und temperature im Request."""
        provider, _ = self._make_provider(temperature=0.7)
        provider._client.text_generation.return_value = "ok"

        provider.complete("prompt")

        _, call_kwargs = provider._client.text_generation.call_args
        assert call_kwargs.get("do_sample") is True
        assert call_kwargs.get("temperature") == pytest.approx(0.7)

    def test_503_error_raises_runtime_error(self):
        """HTTP 503 → RuntimeError mit erklärender Meldung."""
        provider, _ = self._make_provider()
        provider._client.text_generation.side_effect = Exception("503 Service Unavailable")

        with pytest.raises(RuntimeError, match="503"):
            provider.complete("prompt")

    def test_missing_generated_text_raises_value_error(self):
        """Kein generated_text-Feld in der Antwort → ValueError."""
        from sdd_cli.llm.providers.huggingface import HuggingFaceCompletionProvider
        mock_hf_hub, mock_client = _make_hf_module()
        mock_result = MagicMock(spec=[])  # kein generated_text Attribut
        mock_result.__class__ = type("TextGenerationOutput", (), {})
        mock_client.text_generation.return_value = mock_result

        with patch.dict("sys.modules", {"huggingface_hub": mock_hf_hub}):
            provider = HuggingFaceCompletionProvider(
                model="test/model",
                hf_token="hf_test",
                hf_mode="serverless",
            )

        with pytest.raises(ValueError, match="generated_text"):
            provider.complete("prompt")

    def test_client_created_once_in_constructor(self):
        """InferenceClient wird einmalig im Konstruktor erzeugt (FR-02)."""
        from sdd_cli.llm.providers.huggingface import HuggingFaceCompletionProvider
        mock_hf_hub, mock_client = _make_hf_module()
        mock_client.text_generation.return_value = "ok"

        with patch.dict("sys.modules", {"huggingface_hub": mock_hf_hub}):
            provider = HuggingFaceCompletionProvider(
                model="test/model",
                hf_token="hf_test",
                hf_mode="serverless",
            )
            provider.complete("a")
            provider.complete("b")

        assert mock_hf_hub.InferenceClient.call_count == 1

    def test_missing_huggingface_hub_raises_runtime_error(self):
        """Fehlendes huggingface_hub → RuntimeError mit pip-Hinweis (FR-08)."""
        from sdd_cli.llm.providers.huggingface import HuggingFaceCompletionProvider

        with patch.dict("sys.modules", {"huggingface_hub": None}):
            with pytest.raises(RuntimeError, match="sdd-cli\\[huggingface\\]"):
                HuggingFaceCompletionProvider(
                    model="test/model",
                    hf_token="hf_test",
                    hf_mode="serverless",
                )


# ─── Provider-Klasse: dedicated ───────────────────────────────────────────────

class TestHuggingFaceCompletionProviderDedicated:
    def _make_provider(self):
        from sdd_cli.llm.providers.huggingface import HuggingFaceCompletionProvider
        mock_hf_hub, mock_client = _make_hf_module()
        mock_client.text_generation.return_value = "dedicated result"

        with patch.dict("sys.modules", {"huggingface_hub": mock_hf_hub}):
            provider = HuggingFaceCompletionProvider(
                model=None,
                hf_token="hf_test",
                hf_mode="dedicated",
                endpoint_url="https://xyz.endpoints.huggingface.cloud",
            )
        return provider, mock_hf_hub

    def test_dedicated_client_uses_base_url(self):
        """dedicated-Modus: InferenceClient wird mit base_url initialisiert (FR-03)."""
        from sdd_cli.llm.providers.huggingface import HuggingFaceCompletionProvider
        mock_hf_hub, mock_client = _make_hf_module()
        mock_client.text_generation.return_value = "ok"

        with patch.dict("sys.modules", {"huggingface_hub": mock_hf_hub}):
            HuggingFaceCompletionProvider(
                model=None,
                hf_token="hf_test",
                hf_mode="dedicated",
                endpoint_url="https://my.endpoint.cloud",
            )

        mock_hf_hub.InferenceClient.assert_called_once_with(
            base_url="https://my.endpoint.cloud", token="hf_test"
        )

    def test_dedicated_no_model_in_request(self):
        """dedicated-Modus: kein model-Parameter in text_generation (Endpoint impliziert Modell)."""
        provider, _ = self._make_provider()

        provider.complete("prompt")

        _, call_kwargs = provider._client.text_generation.call_args
        assert "model" not in call_kwargs


# ─── Provider-Klasse: local ───────────────────────────────────────────────────

class TestHuggingFaceCompletionProviderLocal:
    def _make_local_provider(self):
        from sdd_cli.llm.providers.huggingface import HuggingFaceCompletionProvider
        return HuggingFaceCompletionProvider(
            model="gpt2",
            hf_token=None,
            hf_mode="local",
        )

    def _make_mock_transformers(self, generated: str = "local output"):
        mock_pipeline_instance = MagicMock()
        mock_pipeline_instance.return_value = [{"generated_text": generated}]
        mock_pipeline_instance.tokenizer = None  # kein chat template
        mock_transformers = MagicMock()
        mock_transformers.pipeline.return_value = mock_pipeline_instance
        return mock_transformers, mock_pipeline_instance

    def test_local_mode_uses_transformers_pipeline(self):
        """local-Modus nutzt transformers.pipeline (FR-04)."""
        provider = self._make_local_provider()
        mock_transformers, _ = self._make_mock_transformers()

        with patch.dict("sys.modules", {"transformers": mock_transformers}):
            result = provider.complete("hallo")

        mock_transformers.pipeline.assert_called_once_with("text-generation", model="gpt2")
        assert result.text == "local output"

    def test_local_pipeline_cached_after_first_call(self):
        """Pipeline wird beim zweiten Aufruf nicht neu geladen (gecacht)."""
        provider = self._make_local_provider()
        mock_transformers, mock_pipe = self._make_mock_transformers()

        with patch.dict("sys.modules", {"transformers": mock_transformers}):
            provider.complete("a")
            provider.complete("b")

        assert mock_transformers.pipeline.call_count == 1

    def test_local_system_prompt_as_xml_prefix_without_chat_template(self):
        """Kein chat template → system_prompt als <system>...</system>\\n\\n Präfix."""
        provider = self._make_local_provider()
        mock_transformers, mock_pipe = self._make_mock_transformers()
        mock_pipe.tokenizer = None

        with patch.dict("sys.modules", {"transformers": mock_transformers}):
            provider.complete("user msg", system_prompt="sei hilfreich")

        call_args, _ = mock_pipe.call_args
        full_prompt = call_args[0]
        assert full_prompt.startswith("<system>\nsei hilfreich\n</system>\n\n")

    def test_local_system_prompt_uses_chat_template_when_available(self):
        """chat_template vorhanden → apply_chat_template statt XML-Präfix."""
        provider = self._make_local_provider()
        mock_transformers, mock_pipe = self._make_mock_transformers()

        mock_tokenizer = MagicMock()
        mock_tokenizer.chat_template = "<...>"
        mock_tokenizer.apply_chat_template.return_value = "<|system|>sei hilfreich<|user|>frage"
        mock_pipe.tokenizer = mock_tokenizer

        with patch.dict("sys.modules", {"transformers": mock_transformers}):
            provider.complete("frage", system_prompt="sei hilfreich")

        mock_tokenizer.apply_chat_template.assert_called_once()
        call_kwargs = mock_tokenizer.apply_chat_template.call_args[1]
        assert call_kwargs.get("tokenize") is False
        assert call_kwargs.get("add_generation_prompt") is True

    def test_local_usage_is_estimated(self):
        """local-Modus: usage.estimated ist True (keine echten Token-Counts)."""
        provider = self._make_local_provider()
        mock_transformers, _ = self._make_mock_transformers("word1 word2")

        with patch.dict("sys.modules", {"transformers": mock_transformers}):
            result = provider.complete("eins zwei")

        assert result.usage.estimated is True

    def test_missing_transformers_raises_runtime_error(self):
        """Fehlendes transformers-Paket → RuntimeError mit pip-Hinweis (FR-08)."""
        provider = self._make_local_provider()

        with patch.dict("sys.modules", {"transformers": None}):
            with pytest.raises(RuntimeError, match="sdd-cli\\[huggingface-local\\]"):
                provider.complete("prompt")

    def test_ose_rror_on_missing_cached_model(self):
        """OSError beim Laden des Modells (kein Cache) → RuntimeError mit Hinweis."""
        provider = self._make_local_provider()
        mock_transformers = MagicMock()
        mock_transformers.pipeline.side_effect = OSError("no such file or directory")

        with patch.dict("sys.modules", {"transformers": mock_transformers}):
            with pytest.raises(RuntimeError, match="Cache"):
                provider.complete("prompt")


# ─── Factory-Integration ──────────────────────────────────────────────────────

class TestHuggingFaceFactory:
    def test_factory_returns_hf_provider_for_serverless(self, monkeypatch):
        """Factory erzeugt HuggingFaceCompletionProvider für provider: huggingface."""
        monkeypatch.setenv("HF_TOKEN", "hf_secret")
        config = _make_config({
            "llm": {
                "completion": {
                    "provider": "huggingface",
                    "model": "mistralai/Mistral-7B-Instruct-v0.3",
                    "hf_token": "${HF_TOKEN}",
                }
            }
        })
        from sdd_cli.llm.providers.huggingface import HuggingFaceCompletionProvider
        mock_hf_hub, _ = _make_hf_module()

        with patch.dict("sys.modules", {"huggingface_hub": mock_hf_hub}):
            provider = get_completion_provider(config, "completion")

        assert isinstance(provider, HuggingFaceCompletionProvider)
        assert provider._hf_token == "hf_secret"

    def test_factory_dedicated_initializes_with_endpoint_url(self, monkeypatch):
        """Factory: dedicated-Modus mit endpoint_url → HuggingFaceCompletionProvider."""
        monkeypatch.setenv("HF_TOKEN", "hf_secret")
        config = _make_config({
            "llm": {
                "completion": {
                    "provider": "huggingface",
                    "hf_mode": "dedicated",
                    "endpoint_url": "https://xyz.endpoints.huggingface.cloud",
                    "hf_token": "${HF_TOKEN}",
                }
            }
        })
        from sdd_cli.llm.providers.huggingface import HuggingFaceCompletionProvider
        mock_hf_hub, _ = _make_hf_module()

        with patch.dict("sys.modules", {"huggingface_hub": mock_hf_hub}):
            provider = get_completion_provider(config, "completion")

        assert isinstance(provider, HuggingFaceCompletionProvider)
        assert provider._endpoint_url == "https://xyz.endpoints.huggingface.cloud"
        assert provider._hf_mode == "dedicated"

    def test_factory_dedicated_without_endpoint_url_raises_value_error(self, monkeypatch):
        """dedicated ohne endpoint_url → ValueError (FR-03)."""
        monkeypatch.setenv("HF_TOKEN", "hf_secret")
        config = _make_config({
            "llm": {
                "completion": {
                    "provider": "huggingface",
                    "hf_mode": "dedicated",
                    "hf_token": "${HF_TOKEN}",
                }
            }
        })
        with pytest.raises(ValueError, match="endpoint_url"):
            get_completion_provider(config, "completion")

    def test_factory_hf_token_env_var_missing_raises_runtime_error(self, monkeypatch):
        """hf_token: ${MY_HF_TOKEN} und Variable fehlt → RuntimeError (FR-11)."""
        monkeypatch.delenv("MY_HF_TOKEN", raising=False)
        config = _make_config({
            "llm": {
                "completion": {
                    "provider": "huggingface",
                    "model": "test/model",
                    "hf_token": "${MY_HF_TOKEN}",
                }
            }
        })
        with pytest.raises(RuntimeError, match="MY_HF_TOKEN"):
            get_completion_provider(config, "completion")

    def test_factory_huggingface_as_code_gen_raises_value_error(self):
        """huggingface als code_gen-Provider → ValueError (FR-06)."""
        config = _make_config({
            "llm": {
                "code_gen": {"provider": "huggingface"}
            }
        })
        with pytest.raises(ValueError, match="huggingface"):
            get_code_gen_provider(config)

    def test_factory_existing_anthropic_branch_unaffected(self):
        """OCP: bestehende anthropic-Branch bleibt unverändert (FR-07)."""
        config = _make_config({
            "llm": {
                "completion": {
                    "provider": "anthropic",
                    "model": "claude-haiku-4-5-20251001",
                }
            }
        })
        from sdd_cli.llm.providers.anthropic import AnthropicCompletionProvider
        with patch(
            "sdd_cli.llm.providers.anthropic.AnthropicCompletionProvider.__init__",
            return_value=None,
        ):
            provider = get_completion_provider(config, "completion")

        assert isinstance(provider, AnthropicCompletionProvider)
        from sdd_cli.llm.providers.huggingface import HuggingFaceCompletionProvider
        assert not isinstance(provider, HuggingFaceCompletionProvider)

    def test_factory_serverless_missing_hf_token_raises_runtime_error(self):
        """serverless ohne hf_token → RuntimeError (FR-10)."""
        config = _make_config({
            "llm": {
                "completion": {
                    "provider": "huggingface",
                    "model": "test/model",
                }
            }
        })
        with pytest.raises(RuntimeError, match="hf_token"):
            get_completion_provider(config, "completion")
