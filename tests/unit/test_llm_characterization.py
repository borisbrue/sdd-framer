"""Charakterisierungstests – Regressionsschutz gemäß FR-17 (TST-0033 bis TST-0036).

Diese Tests sichern den Input→Output-Vertrag der vier refaktorierten LLM-Call-Sites.
Sie müssen nach jedem Refactor dieser Stellen grün bleiben (Merge-Blocker).

Alle vier Tests mocken den externen Aufruf (Provider/subprocess) und prüfen
ausschließlich den Vertrag der übergeordneten Funktion.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# sdd_cli muss im Pfad liegen
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tool"))
# web/api muss im Pfad liegen (für analyzer, usage_store, sdd_context)
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tool" / "sdd_cli" / "web" / "api"))

from sdd_cli.llm.base import CompletionResult, UsageMetadata

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_provider(text: str, usage: UsageMetadata | None = None):
    """Erzeugt einen Mock-Provider, der CompletionResult(text, usage) zurückgibt."""
    provider = MagicMock()
    provider.complete.return_value = CompletionResult(text=text, usage=usage)
    return provider


# ─── TST-0033: evaluator._call_llm ───────────────────────────────────────────

class TestEvaluatorCallLlm:
    """Charakterisierung: evaluator._call_llm(provider, prompt) → dict."""

    def test_returns_parsed_dict_from_provider_text(self):
        """Gibt geparsten dict aus provider.complete().text zurück."""
        from sdd_cli.evaluator import _call_llm

        payload = {"method": "GET", "path": "/api/health", "headers": {}, "body": None}
        provider = _make_provider(json.dumps(payload))

        result = _call_llm(provider, "plan this scenario")

        assert result == payload
        provider.complete.assert_called_once_with("plan this scenario")

    def test_extracts_json_from_surrounding_text(self):
        """JSON wird robust aus umgebendem Text extrahiert."""
        from sdd_cli.evaluator import _call_llm

        payload = {"passed": True, "reasoning": "looks good"}
        surrounding = f"Here is my answer:\n\n{json.dumps(payload)}\n\nDone."
        provider = _make_provider(surrounding)

        result = _call_llm(provider, "evaluate this")

        assert result == payload

    def test_raises_json_decode_error_for_invalid_response(self):
        """Gibt keine dict zurück bei ungültigem JSON → JSONDecodeError."""
        from sdd_cli.evaluator import _call_llm

        provider = _make_provider("this is not json at all")

        with pytest.raises((json.JSONDecodeError, ValueError)):
            _call_llm(provider, "prompt")

    def test_plan_prompt_keys_present_in_result(self):
        """Plan-Antwort enthält erwartete Schlüssel (method, path, headers, body)."""
        from sdd_cli.evaluator import _call_llm

        plan = {"method": "POST", "path": "/api/users", "headers": {"Content-Type": "application/json"}, "body": {"name": "test"}}
        provider = _make_provider(json.dumps(plan))

        result = _call_llm(provider, "plan prompt")

        assert "method" in result
        assert "path" in result

    def test_eval_prompt_keys_present_in_result(self):
        """Eval-Antwort enthält erwartete Schlüssel (passed, reasoning)."""
        from sdd_cli.evaluator import _call_llm

        verdict = {"passed": False, "reasoning": "status code was 404 not 200"}
        provider = _make_provider(json.dumps(verdict))

        result = _call_llm(provider, "evaluate this response")

        assert "passed" in result
        assert "reasoning" in result


# ─── TST-0034: orchestrator._call_code_gen_agent ─────────────────────────────

class TestOrchestratorCallCodeGenAgent:
    """Charakterisierung: _call_code_gen_agent(...) → (list[dict], str)."""

    def _make_config(self, root: Path):
        from sdd_cli.config import SddConfig
        return SddConfig(root=root, raw={})

    def test_returns_tuple_of_files_list_and_explanation(self, tmp_path):
        """Gibt (list[dict], str) Tuple zurück."""
        from sdd_cli.orchestrator import _call_code_gen_agent

        config = self._make_config(tmp_path)
        mock_provider = MagicMock()
        expected_files = [{"path": "src/main.py", "content": "print('hello')"}]
        mock_provider.generate.return_value = (expected_files, "initial implementation")

        # Patch at sdd_cli.llm (the package namespace where _call_code_gen_agent imports from)
        with patch("sdd_cli.llm.get_code_gen_provider", return_value=mock_provider):
            files, explanation = _call_code_gen_agent(
                config=config,
                spec_id="SPEC-0001",
                spec_content="## Feature\n\nAdd a hello world function.",
                agents_md="",
                contracts=[],
                error_context="",
            )

        assert isinstance(files, list)
        assert isinstance(explanation, str)
        assert files == expected_files
        assert explanation == "initial implementation"

    def test_timeout_parameter_forwarded_to_provider(self, tmp_path):
        """timeout-Parameter wird an provider.generate() weitergereicht."""
        from sdd_cli.orchestrator import _call_code_gen_agent

        config = self._make_config(tmp_path)
        mock_provider = MagicMock()
        mock_provider.generate.return_value = ([], "done")

        with patch("sdd_cli.llm.get_code_gen_provider", return_value=mock_provider):
            _call_code_gen_agent(
                config=config,
                spec_id="SPEC-0001",
                spec_content="spec",
                agents_md="",
                contracts=[],
                error_context="",
                timeout=300,
            )

        call_kwargs = mock_provider.generate.call_args[1]
        assert call_kwargs.get("timeout") == 300

    def test_spec_id_appears_in_prompt(self, tmp_path):
        """spec_id erscheint im Prompt an den Provider."""
        from sdd_cli.orchestrator import _call_code_gen_agent

        config = self._make_config(tmp_path)
        mock_provider = MagicMock()
        mock_provider.generate.return_value = ([], "done")

        with patch("sdd_cli.llm.get_code_gen_provider", return_value=mock_provider):
            _call_code_gen_agent(
                config=config,
                spec_id="SPEC-9999",
                spec_content="spec content",
                agents_md="",
                contracts=[],
                error_context="",
            )

        prompt_arg = mock_provider.generate.call_args[0][0]
        assert "SPEC-9999" in prompt_arg

    def test_error_context_appears_in_prompt(self, tmp_path):
        """error_context erscheint im Prompt bei Retry."""
        from sdd_cli.orchestrator import _call_code_gen_agent

        config = self._make_config(tmp_path)
        mock_provider = MagicMock()
        mock_provider.generate.return_value = ([], "retry done")

        with patch("sdd_cli.llm.get_code_gen_provider", return_value=mock_provider):
            _call_code_gen_agent(
                config=config,
                spec_id="SPEC-0001",
                spec_content="spec",
                agents_md="",
                contracts=[],
                error_context="test failed: assertion error",
            )

        prompt_arg = mock_provider.generate.call_args[0][0]
        assert "test failed: assertion error" in prompt_arg

    def test_workspace_is_config_root(self, tmp_path):
        """workspace-Argument an provider.generate() ist config.root."""
        from sdd_cli.orchestrator import _call_code_gen_agent

        config = self._make_config(tmp_path)
        mock_provider = MagicMock()
        mock_provider.generate.return_value = ([], "done")

        with patch("sdd_cli.llm.get_code_gen_provider", return_value=mock_provider):
            _call_code_gen_agent(
                config=config,
                spec_id="SPEC-0001",
                spec_content="spec",
                agents_md="",
                contracts=[],
                error_context="",
            )

        workspace_arg = mock_provider.generate.call_args[0][1]
        assert workspace_arg == tmp_path


# ─── TST-0035: analyzer._call_claude ─────────────────────────────────────────

class TestAnalyzerCallClaude:
    """Charakterisierung: analyzer._call_claude(prompt, provider) → (dict, dict)."""

    def test_returns_parsed_json_and_usage_dict(self):
        """Gibt (geparsten dict, usage dict) zurück."""
        from analyzer import _call_claude

        payload = {
            "questions": [{"id": "q1", "section": "§1", "text": "What?", "severity": "warning"}],
            "issues": [],
            "suggestions": [],
        }
        provider = _make_provider(json.dumps(payload), usage=UsageMetadata(
            input_tokens=100, output_tokens=50, model="claude-haiku-4-5-20251001"
        ))

        result, usage = _call_claude("analyze this doc", provider)

        assert result == payload
        assert "provider" in usage

    def test_strips_markdown_fence_from_response(self):
        """JSON in markdown-Fence wird korrekt geparst."""
        from analyzer import _call_claude

        payload = {"questions": [], "issues": [], "suggestions": []}
        fenced = f"```json\n{json.dumps(payload)}\n```"
        provider = _make_provider(fenced)

        result, usage = _call_claude("analyze", provider)

        assert result == payload

    def test_usage_dict_has_provider_key(self):
        """usage-Dict enthält mindestens 'provider'-Schlüssel."""
        from analyzer import _call_claude

        provider = _make_provider('{"questions":[],"issues":[],"suggestions":[]}')

        _, usage = _call_claude("analyze", provider)

        assert "provider" in usage

    def test_usage_populated_when_anthropic_provider_returns_tokens(self):
        """Bei Anthropic-Provider mit usage werden Tokens in usage-Dict abgebildet."""
        from analyzer import _call_claude

        provider = _make_provider(
            '{"questions":[],"issues":[],"suggestions":[]}',
            usage=UsageMetadata(input_tokens=42, output_tokens=17, model="claude-haiku"),
        )

        _, usage = _call_claude("analyze", provider)

        assert usage.get("input_tokens") == 42
        assert usage.get("output_tokens") == 17

    def test_runtime_error_from_provider_raises_http_exception(self):
        """RuntimeError vom Provider → HTTPException."""
        from analyzer import _call_claude
        from fastapi import HTTPException

        provider = MagicMock()
        provider.complete.side_effect = RuntimeError("claude CLI nicht gefunden")

        with pytest.raises(HTTPException) as exc_info:
            _call_claude("prompt", provider)

        assert exc_info.value.status_code in (503, 504, 502)

    def test_invalid_json_from_provider_raises_http_exception(self):
        """Ungültiges JSON vom Provider → HTTPException 502."""
        from analyzer import _call_claude
        from fastapi import HTTPException

        provider = _make_provider("this is not json")

        with pytest.raises(HTTPException) as exc_info:
            _call_claude("prompt", provider)

        assert exc_info.value.status_code == 502


# ─── TST-0036: ai._call ───────────────────────────────────────────────────────

class TestAiRoutesCall:
    """Charakterisierung: ai._call(operation, user_message) → (str, dict)."""

    def _reset_ai_module_provider(self):
        """Reset des modul-globalen _provider in routes/ai.py."""
        import routes.ai as ai_module
        ai_module._provider = None

    def test_returns_text_and_usage_entry(self):
        """Gibt (text: str, entry: dict) Tuple zurück."""
        self._reset_ai_module_provider()

        mock_usage = UsageMetadata(input_tokens=100, output_tokens=50,
                                   cache_creation_tokens=0, cache_read_tokens=0,
                                   model="claude-opus-4-7")
        provider = _make_provider("generated spec text", usage=mock_usage)

        usage_entry = {"ts": "2026-01-01", "cost_usd": 0.01, "operation": "generate-spec"}

        with patch("routes.ai.get_config"), \
             patch("sdd_cli.llm.factory.get_completion_provider", return_value=provider), \
             patch("usage_store.cost_entry", return_value=usage_entry):
            import routes.ai as ai_module
            ai_module._provider = provider
            text, entry = ai_module._call("generate-spec", "Write a spec about X")

        assert text == "generated spec text"
        assert isinstance(entry, dict)

    def test_usage_store_cost_entry_called_when_usage_available(self):
        """usage_store.cost_entry() liefert den Eintrag; gespeichert hat die Factory (SPEC-0060 FR-08)."""
        self._reset_ai_module_provider()

        mock_usage = UsageMetadata(
            input_tokens=200, output_tokens=80,
            cache_creation_tokens=10, cache_read_tokens=5,
            model="claude-opus-4-7",
        )
        provider = _make_provider("text", usage=mock_usage)
        usage_entry = {"ts": "2026-01-01", "cost_usd": 0.05}

        with patch("usage_store.cost_entry", return_value=usage_entry) as mock_record:
            import routes.ai as ai_module
            ai_module._provider = provider
            _, entry = ai_module._call("improve-spec", "improve this")

        mock_record.assert_called_once_with(
            operation="improve-spec",
            input_tokens=200,
            output_tokens=80,
            cache_creation_tokens=10,
            cache_read_tokens=5,
            model="claude-opus-4-7",
        )
        assert entry == usage_entry

    def test_usage_store_not_called_when_usage_is_none(self):
        """usage_store.cost_entry() wird NICHT aufgerufen wenn result.usage None."""
        self._reset_ai_module_provider()

        provider = _make_provider("text", usage=None)

        with patch("usage_store.cost_entry") as mock_record:
            import routes.ai as ai_module
            ai_module._provider = provider
            _, entry = ai_module._call("suggest-contracts", "suggest contracts")

        mock_record.assert_not_called()
        assert entry == {}

    def test_runtime_error_from_provider_raises_http_exception(self):
        """RuntimeError vom Provider → HTTPException 503."""
        from fastapi import HTTPException
        self._reset_ai_module_provider()

        provider = MagicMock()
        provider.complete.side_effect = RuntimeError("provider unavailable")

        with pytest.raises(HTTPException) as exc_info:
            import routes.ai as ai_module
            ai_module._provider = provider
            ai_module._call("generate-spec", "write a spec")

        assert exc_info.value.status_code == 503

    def test_system_prompt_passed_to_provider(self):
        """SDD_SYSTEM_PROMPT wird als system_prompt an provider.complete() übergeben."""
        self._reset_ai_module_provider()

        provider = _make_provider("spec text")

        with patch("usage_store.cost_entry", return_value={}):
            import routes.ai as ai_module
            ai_module._provider = provider
            ai_module._call("generate-spec", "write it")

        call_kwargs = provider.complete.call_args[1]
        assert call_kwargs.get("system_prompt") == ai_module.SDD_SYSTEM_PROMPT
