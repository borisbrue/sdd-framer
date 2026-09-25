"""Unit-Tests für SPEC-0008 – LLM-Provider und Factory (TST-0028 bis TST-0032)."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tool"))

from sdd_cli.llm.base import CompletionResult
from sdd_cli.llm.factory import get_code_gen_provider, get_completion_provider

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_config(raw: dict):
    from sdd_cli.config import SddConfig
    return SddConfig(root=Path("/tmp"), raw=raw)


# ─── TST-0028: Factory – Auflösungs-Hierarchie und temperature ────────────────

class TestFactory:
    def test_no_llm_section_evaluator_returns_claude_cli_provider(self):
        """Fehlt llm-Sektion → evaluator bekommt ClaudeCliCompletionProvider (keyfrei)."""
        config = _make_config({})
        from sdd_cli.llm.providers.claude_cli import ClaudeCliCompletionProvider
        provider = get_completion_provider(config, "evaluator")
        assert isinstance(provider, ClaudeCliCompletionProvider)

    def test_no_llm_section_ai_routes_defaults_to_claude_cli(self):
        """ai_routes Default ist claude-cli – keyfreier Betrieb ohne ANTHROPIC_API_KEY."""
        config = _make_config({})
        from sdd_cli.llm.providers.claude_cli import ClaudeCliCompletionProvider
        provider = get_completion_provider(config, "ai_routes")
        assert isinstance(provider, ClaudeCliCompletionProvider)

    def test_explicit_anthropic_still_wins_over_keyless_default(self):
        """Explizites provider: anthropic überschreibt den claude-cli-Default."""
        config = _make_config({"llm": {"evaluator": {"provider": "anthropic",
                                                     "model": "claude-sonnet-4-6"}}})
        with patch("sdd_cli.llm.providers.anthropic.AnthropicCompletionProvider.__init__",
                   return_value=None) as mock_init:
            from sdd_cli.llm.providers.anthropic import AnthropicCompletionProvider
            provider = get_completion_provider(config, "evaluator")
            _, kwargs = mock_init.call_args
        assert isinstance(provider, AnthropicCompletionProvider)
        assert kwargs.get("model") == "claude-sonnet-4-6"

    def test_component_override_inherits_model_from_global_default(self):
        """Komponenten-Override erbt model vom globalen llm.completion (E-05)."""
        config = _make_config({
            "llm": {
                "completion": {
                    "provider": "anthropic",
                    "model": "claude-haiku-4-5-20251001",
                },
                "evaluator": {
                    "provider": "openai-compat",
                    "base_url": "http://localhost:1234/v1",
                    # model nicht gesetzt → erbt von completion
                },
            }
        })
        with patch("sdd_cli.llm.providers.openai_compat.OpenAICompatCompletionProvider.__init__",
                   return_value=None) as mock_init:
            get_completion_provider(config, "evaluator")
            _, kwargs = mock_init.call_args
            assert kwargs.get("model") == "claude-haiku-4-5-20251001"

    def test_missing_base_url_for_openai_compat_raises_value_error(self):
        """openai-compat ohne base_url → ValueError (E-01)."""
        config = _make_config({
            "llm": {
                "evaluator": {
                    "provider": "openai-compat",
                    "model": "test-model",
                }
            }
        })
        with pytest.raises(ValueError, match="base_url"):
            get_completion_provider(config, "evaluator")

    def test_missing_model_for_openai_compat_raises_value_error(self):
        """openai-compat ohne model → ValueError (E-02).

        Uses analyzer component which has no built-in model default.
        evaluator has a built-in model (haiku) and would not raise.
        """
        config = _make_config({
            "llm": {
                "analyzer": {
                    "provider": "openai-compat",
                    "base_url": "http://localhost:1234/v1",
                    # No model here, no llm.completion block → no inherited model
                }
            }
        })
        with pytest.raises(ValueError, match="model"):
            get_completion_provider(config, "analyzer")

    def test_unknown_provider_raises_value_error(self):
        """Unbekannter Provider → ValueError (FR-13)."""
        config = _make_config({
            "llm": {"completion": {"provider": "mythical-provider"}}
        })
        with pytest.raises(ValueError, match="mythical-provider"):
            get_completion_provider(config, "completion")

    def test_temperature_passed_to_anthropic_provider(self):
        """temperature aus Config wird an AnthropicCompletionProvider übergeben."""
        config = _make_config({
            "llm": {
                "completion": {
                    "provider": "anthropic",
                    "model": "claude-haiku-4-5-20251001",
                    "temperature": 0.5,
                }
            }
        })
        with patch("sdd_cli.llm.providers.anthropic.AnthropicCompletionProvider.__init__",
                   return_value=None) as mock_init:
            get_completion_provider(config, "completion")
            call_kwargs = mock_init.call_args[1] if mock_init.call_args[1] else {}
            call_args = mock_init.call_args[0]
            # temperature should be passed either as positional or keyword arg
            assert 0.5 in call_args or call_kwargs.get("temperature") == 0.5

    def test_env_var_api_key_resolved(self, monkeypatch):
        """api_key: ${MY_KEY} wird aus os.environ aufgelöst (E-09)."""
        monkeypatch.setenv("MY_TEST_KEY", "secret-value")
        config = _make_config({
            "llm": {
                "completion": {
                    "provider": "anthropic",
                    "model": "claude-haiku-4-5-20251001",
                    "api_key": "${MY_TEST_KEY}",
                }
            }
        })
        with patch("sdd_cli.llm.providers.anthropic.AnthropicCompletionProvider.__init__",
                   return_value=None) as mock_init:
            get_completion_provider(config, "completion")
            call_kwargs = mock_init.call_args[1] if mock_init.call_args[1] else {}
            call_args = mock_init.call_args[0]
            assert "secret-value" in call_args or call_kwargs.get("api_key") == "secret-value"

    def test_env_var_api_key_missing_raises_runtime_error(self, monkeypatch):
        """api_key: ${MISSING_VAR} und Variable fehlt → RuntimeError (E-09)."""
        monkeypatch.delenv("MISSING_VAR_XYZ", raising=False)
        config = _make_config({
            "llm": {
                "completion": {
                    "provider": "anthropic",
                    "model": "claude-haiku-4-5-20251001",
                    "api_key": "${MISSING_VAR_XYZ}",
                }
            }
        })
        with pytest.raises(RuntimeError, match="MISSING_VAR_XYZ"):
            get_completion_provider(config, "completion")

    def test_anthropic_not_valid_for_code_gen_provider(self):
        """anthropic ist kein gültiger code_gen-Provider → ValueError (§5.1)."""
        config = _make_config({
            "llm": {
                "code_gen": {"provider": "anthropic"}
            }
        })
        with pytest.raises(ValueError, match="anthropic"):
            get_code_gen_provider(config)

    def test_unknown_component_raises_value_error(self):
        """Unbekannte Komponente → ValueError."""
        config = _make_config({})
        with pytest.raises(ValueError, match="unknown-comp"):
            get_completion_provider(config, "unknown-comp")

    def test_field_for_field_merge_not_section_replace(self):
        """Felder werden einzeln geerbt — andere Komponenten-Overrides beeinflussen sich nicht."""
        config = _make_config({
            "llm": {
                "completion": {"provider": "anthropic", "model": "model-A"},
                "analyzer": {"model": "model-B"},  # provider nicht gesetzt → erbt von completion
                "evaluator": {"provider": "openai-compat",
                               "base_url": "http://localhost:1234/v1"},
            }
        })
        with patch("sdd_cli.llm.providers.anthropic.AnthropicCompletionProvider.__init__",
                   return_value=None) as mock_init:
            get_completion_provider(config, "analyzer")
            args = mock_init.call_args[0]
            kwargs = mock_init.call_args[1] if mock_init.call_args[1] else {}
            model = args[0] if args else kwargs.get("model")
            assert model == "model-B"


# ─── TST-0029: OpenAICompatCompletionProvider ─────────────────────────────────

class TestOpenAICompatCompletionProvider:
    def _make_provider(self, temperature: float = 0.0):
        from sdd_cli.llm.providers.openai_compat import OpenAICompatCompletionProvider
        return OpenAICompatCompletionProvider(
            base_url="http://localhost:1234/v1",
            model="test-model",
            temperature=temperature,
        )

    def _make_mock_openai_module(self, content: str = "ok",
                                  prompt_tokens: int = 10, completion_tokens: int = 5):
        mock_usage = MagicMock()
        mock_usage.prompt_tokens = prompt_tokens
        mock_usage.completion_tokens = completion_tokens
        mock_choice = MagicMock()
        mock_choice.message.content = content
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = mock_usage
        mock_openai = MagicMock()
        mock_openai.OpenAI.return_value.chat.completions.create.return_value = mock_response
        return mock_openai, mock_response

    def test_complete_sends_correct_request(self):
        """complete() sendet korrekten Request an openai Client."""
        provider = self._make_provider()
        mock_openai, _ = self._make_mock_openai_module('{"result": "ok"}')

        with patch.dict("sys.modules", {"openai": mock_openai}):
            provider.complete("test prompt", max_tokens=256)

        mock_client = mock_openai.OpenAI.return_value
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "test-model"
        assert call_kwargs["max_tokens"] == 256
        assert call_kwargs["messages"][-1]["role"] == "user"
        assert call_kwargs["messages"][-1]["content"] == "test prompt"

    def test_complete_returns_completion_result_with_usage(self):
        """complete() gibt CompletionResult mit UsageMetadata zurück."""
        provider = self._make_provider()
        mock_openai, _ = self._make_mock_openai_module("hello world", prompt_tokens=15, completion_tokens=3)

        with patch.dict("sys.modules", {"openai": mock_openai}):
            result = provider.complete("prompt")

        assert isinstance(result, CompletionResult)
        assert result.text == "hello world"
        assert result.usage is not None
        assert result.usage.input_tokens == 15
        assert result.usage.output_tokens == 3
        assert result.usage.model == "test-model"

    def test_complete_with_system_prompt_adds_system_message(self):
        """system_prompt wird als system-Nachricht vorangestellt."""
        provider = self._make_provider()
        mock_openai, _ = self._make_mock_openai_module("answer")

        with patch.dict("sys.modules", {"openai": mock_openai}):
            provider.complete("user msg", system_prompt="be helpful")

        mock_client = mock_openai.OpenAI.return_value
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        messages = call_kwargs["messages"]
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "be helpful"
        assert messages[1]["role"] == "user"

    def test_complete_with_timeout_passes_timeout(self):
        """timeout wird an completions.create weitergereicht."""
        provider = self._make_provider()
        mock_openai, _ = self._make_mock_openai_module("ok")

        with patch.dict("sys.modules", {"openai": mock_openai}):
            provider.complete("prompt", timeout=30)

        mock_client = mock_openai.OpenAI.return_value
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs.get("timeout") == 30

    def test_temperature_is_passed_to_api(self):
        """temperature aus Konstruktor wird an API übergeben."""
        provider = self._make_provider(temperature=0.7)
        mock_openai, _ = self._make_mock_openai_module("ok")

        with patch.dict("sys.modules", {"openai": mock_openai}):
            provider.complete("prompt")

        mock_client = mock_openai.OpenAI.return_value
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["temperature"] == 0.7

    def test_disabled_thinking_sends_chat_template_kwargs(self):
        """HF-0011: enable_thinking=False erreicht auch vLLM-Server.

        vLLM ignoriert das flache extra_body.enable_thinking, Qwen-Modelle denken dort
        nur mit chat_template_kwargs.enable_thinking=False nicht. Das flache Feld bleibt
        für LM Studio erhalten.
        """
        from sdd_cli.llm.providers.openai_compat import OpenAICompatCompletionProvider
        provider = OpenAICompatCompletionProvider(
            base_url="http://localhost:1234/v1", model="test-model", enable_thinking=False,
        )
        mock_openai, _ = self._make_mock_openai_module("ok")

        with patch.dict("sys.modules", {"openai": mock_openai}):
            provider.complete("prompt")

        call_kwargs = mock_openai.OpenAI.return_value.chat.completions.create.call_args[1]
        assert call_kwargs["extra_body"] == {
            "enable_thinking": False,
            "chat_template_kwargs": {"enable_thinking": False},
        }

    def test_enabled_thinking_sends_no_extra_body(self):
        """Default enable_thinking=True lässt das Server-Verhalten unverändert."""
        provider = self._make_provider()
        mock_openai, _ = self._make_mock_openai_module("ok")

        with patch.dict("sys.modules", {"openai": mock_openai}):
            provider.complete("prompt")

        call_kwargs = mock_openai.OpenAI.return_value.chat.completions.create.call_args[1]
        assert "extra_body" not in call_kwargs

    def test_missing_openai_raises_runtime_error(self):
        """Fehlendes openai-Paket → RuntimeError mit install-Hinweis (FR-11)."""
        provider = self._make_provider()
        with patch.dict("sys.modules", {"openai": None}):
            with pytest.raises(RuntimeError, match="lm-studio"):
                provider.complete("prompt")


# ─── TST-0030: OpenAICompatCodeGenProvider ────────────────────────────────────

class TestOpenAICompatCodeGenProvider:
    def _make_provider(self):
        from sdd_cli.llm.providers.openai_compat import OpenAICompatCodeGenProvider
        return OpenAICompatCodeGenProvider(
            base_url="http://localhost:1234/v1",
            model="test-model",
        )

    def _make_mock_openai_with_content(self, content: str):
        mock_response = MagicMock()
        mock_response.choices[0].message.content = content
        mock_openai = MagicMock()
        mock_openai.OpenAI.return_value.chat.completions.create.return_value = mock_response
        return mock_openai

    def test_generate_writes_files_from_json_response(self, tmp_path):
        """generate() schreibt Dateien aus JSON-Antwort in workspace."""
        provider = self._make_provider()
        json_response = json.dumps({
            "files": [
                {"path": "src/main.py", "content": "print('hello')"},
                {"path": "README.md", "content": "# Project"},
            ],
            "explanation": "initial implementation",
        })
        mock_openai = self._make_mock_openai_with_content(json_response)

        with patch.dict("sys.modules", {"openai": mock_openai}):
            files, explanation = provider.generate("implement X", tmp_path)

        assert len(files) == 2
        assert (tmp_path / "src" / "main.py").read_text() == "print('hello')"
        assert (tmp_path / "README.md").read_text() == "# Project"
        assert explanation == "initial implementation"

    def test_generate_overwrites_existing_files(self, tmp_path):
        """Existierende Dateien werden ohne Fehler überschrieben (FR-09)."""
        existing = tmp_path / "src" / "main.py"
        existing.parent.mkdir()
        existing.write_text("old content")

        provider = self._make_provider()
        json_response = json.dumps({
            "files": [{"path": "src/main.py", "content": "new content"}],
            "explanation": "update",
        })
        mock_openai = self._make_mock_openai_with_content(json_response)

        with patch.dict("sys.modules", {"openai": mock_openai}):
            provider.generate("update X", tmp_path)

        assert existing.read_text() == "new content"

    def test_path_traversal_raises_value_error(self, tmp_path):
        """Pfad außerhalb workspace → ValueError (E-08)."""
        provider = self._make_provider()
        json_response = json.dumps({
            "files": [{"path": "../../etc/passwd", "content": "evil"}],
            "explanation": "pwned",
        })
        mock_openai = self._make_mock_openai_with_content(json_response)

        with patch.dict("sys.modules", {"openai": mock_openai}):
            with pytest.raises(ValueError, match="Workspace-Escape"):
                provider.generate("evil", tmp_path)

    def test_invalid_json_raises_json_decode_error(self, tmp_path):
        """Ungültiges JSON vom Modell → JSONDecodeError (E-04)."""
        provider = self._make_provider()
        mock_openai = self._make_mock_openai_with_content("not json at all")

        with patch.dict("sys.modules", {"openai": mock_openai}):
            with pytest.raises(json.JSONDecodeError):
                provider.generate("fail", tmp_path)


# ─── TST-0031: ClaudeCliCompletionProvider ────────────────────────────────────

class TestClaudeCliCompletionProvider:
    def _make_provider(self):
        from sdd_cli.llm.providers.claude_cli import ClaudeCliCompletionProvider
        return ClaudeCliCompletionProvider()

    def _make_proc_result(self, stdout: str, returncode: int = 0):
        mock = MagicMock()
        mock.stdout = stdout
        mock.returncode = returncode
        return mock

    def test_complete_strips_outer_json_envelope(self):
        """Äußerer JSON-Envelope wird gestrippt; innerer result-Text zurückgegeben."""
        provider = self._make_provider()
        outer = json.dumps({"type": "result", "result": "inner text", "total_cost_usd": 0.001})

        with patch("shutil.which", return_value="/usr/bin/claude"), \
             patch("subprocess.run", return_value=self._make_proc_result(outer)):
            result = provider.complete("prompt")

        assert result.text == "inner text"
        assert result.usage is None

    def test_complete_system_prompt_prepended_as_xml(self):
        """system_prompt wird als <system>...</system>\\n\\n vorangestellt."""
        provider = self._make_provider()
        outer = json.dumps({"type": "result", "result": "ok"})

        with patch("shutil.which", return_value="/usr/bin/claude"), \
             patch("subprocess.run", return_value=self._make_proc_result(outer)) as mock_run:
            provider.complete("user prompt", system_prompt="be helpful")

        call_args = mock_run.call_args[0][0]
        prompt_arg = call_args[-1]
        assert prompt_arg.startswith("<system>\nbe helpful\n</system>\n\n")
        assert prompt_arg.endswith("user prompt")

    def test_complete_timeout_passed_to_subprocess(self):
        """timeout wird an subprocess.run weitergereicht."""
        provider = self._make_provider()
        outer = json.dumps({"type": "result", "result": "ok"})

        with patch("shutil.which", return_value="/usr/bin/claude"), \
             patch("subprocess.run", return_value=self._make_proc_result(outer)) as mock_run:
            provider.complete("prompt", timeout=45)

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs.get("timeout") == 45

    def test_complete_usage_is_none(self):
        """usage ist immer None (CLI liefert keine Token-Counts)."""
        provider = self._make_provider()
        outer = json.dumps({"type": "result", "result": "ok"})

        with patch("shutil.which", return_value="/usr/bin/claude"), \
             patch("subprocess.run", return_value=self._make_proc_result(outer)):
            result = provider.complete("prompt")

        assert result.usage is None

    def test_claude_cli_not_found_raises_runtime_error(self):
        """claude CLI nicht gefunden → RuntimeError (FR-12)."""
        provider = self._make_provider()
        with patch("shutil.which", return_value=None):
            with pytest.raises(RuntimeError, match="claude CLI nicht gefunden"):
                provider.complete("prompt")

    def test_complete_without_system_prompt_sends_plain_prompt(self):
        """Ohne system_prompt wird prompt unverändert übergeben."""
        provider = self._make_provider()
        outer = json.dumps({"type": "result", "result": "ok"})

        with patch("shutil.which", return_value="/usr/bin/claude"), \
             patch("subprocess.run", return_value=self._make_proc_result(outer)) as mock_run:
            provider.complete("plain prompt")

        call_args = mock_run.call_args[0][0]
        assert call_args[-1] == "plain prompt"


# ─── TST-0032: AnthropicCompletionProvider ────────────────────────────────────

class TestAnthropicCompletionProvider:
    def _make_provider(self, temperature: float = 0.0):
        from sdd_cli.llm.providers.anthropic import AnthropicCompletionProvider
        return AnthropicCompletionProvider(
            model="claude-haiku-4-5-20251001",
            api_key="test-key",
            temperature=temperature,
        )

    def _make_mock_anthropic_module(
        self,
        text: str = "response",
        input_tokens: int = 10,
        output_tokens: int = 5,
        cache_creation: int = 0,
        cache_read: int = 0,
    ):
        mock_usage = MagicMock()
        mock_usage.input_tokens = input_tokens
        mock_usage.output_tokens = output_tokens
        mock_usage.cache_creation_input_tokens = cache_creation
        mock_usage.cache_read_input_tokens = cache_read
        mock_content = MagicMock()
        mock_content.text = text
        mock_message = MagicMock()
        mock_message.content = [mock_content]
        mock_message.usage = mock_usage
        mock_anthropic = MagicMock()
        mock_anthropic.Anthropic.return_value.messages.create.return_value = mock_message
        return mock_anthropic, mock_message

    def test_complete_returns_completion_result_with_usage(self):
        """complete() gibt CompletionResult mit befüllter UsageMetadata zurück."""
        provider = self._make_provider()
        mock_anthropic, _ = self._make_mock_anthropic_module(
            text="hello", input_tokens=20, output_tokens=8
        )

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            result = provider.complete("test prompt")

        assert isinstance(result, CompletionResult)
        assert result.text == "hello"
        assert result.usage is not None
        assert result.usage.input_tokens == 20
        assert result.usage.output_tokens == 8
        assert result.usage.model == "claude-haiku-4-5-20251001"

    def test_complete_with_system_prompt_uses_cache_control(self):
        """system_prompt != None → cache_control: ephemeral in system-Block."""
        provider = self._make_provider()
        mock_anthropic, _ = self._make_mock_anthropic_module()

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            provider.complete("prompt", system_prompt="be helpful")

        mock_client = mock_anthropic.Anthropic.return_value
        call_kwargs = mock_client.messages.create.call_args[1]
        system_block = call_kwargs.get("system", [])
        assert len(system_block) == 1
        assert system_block[0]["type"] == "text"
        assert system_block[0]["text"] == "be helpful"
        assert system_block[0]["cache_control"] == {"type": "ephemeral"}

    def test_complete_without_system_prompt_no_system_kwarg(self):
        """Ohne system_prompt wird kein system-Kwarg übergeben."""
        provider = self._make_provider()
        mock_anthropic, _ = self._make_mock_anthropic_module()

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            provider.complete("prompt")

        mock_client = mock_anthropic.Anthropic.return_value
        call_kwargs = mock_client.messages.create.call_args[1]
        assert "system" not in call_kwargs

    def test_complete_with_timeout_passes_timeout(self):
        """timeout wird an messages.create weitergereicht."""
        provider = self._make_provider()
        mock_anthropic, _ = self._make_mock_anthropic_module()

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            provider.complete("prompt", timeout=60)

        mock_client = mock_anthropic.Anthropic.return_value
        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs.get("timeout") == 60

    def test_complete_cache_tokens_in_usage(self):
        """cache_creation_input_tokens und cache_read_input_tokens werden in usage abgebildet."""
        provider = self._make_provider()
        mock_anthropic, _ = self._make_mock_anthropic_module(cache_creation=100, cache_read=50)

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            result = provider.complete("prompt")

        assert result.usage.cache_creation_tokens == 100
        assert result.usage.cache_read_tokens == 50

    def test_missing_api_key_raises_runtime_error(self):
        """Fehlt api_key (und ANTHROPIC_API_KEY env) → RuntimeError."""
        from sdd_cli.llm.providers.anthropic import AnthropicCompletionProvider
        provider = AnthropicCompletionProvider(model="m", api_key=None)
        mock_anthropic = MagicMock()
        with patch.dict(os.environ, {}, clear=True), \
             patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            os.environ.pop("ANTHROPIC_API_KEY", None)
            with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
                provider.complete("prompt")

    def test_missing_anthropic_package_raises_runtime_error(self):
        """Fehlendes anthropic-Paket → RuntimeError mit install-Hinweis (FR-10)."""
        provider = self._make_provider()
        with patch.dict("sys.modules", {"anthropic": None}):
            with pytest.raises(RuntimeError, match="evaluate"):
                provider.complete("prompt")
