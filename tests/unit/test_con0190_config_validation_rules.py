# TST-0219 – CON-0190: Config-Validierungsregeln
from sdd_cli.config_validator import ConfigIssue, ConfigValidator


def _issues(raw: dict) -> list[ConfigIssue]:
    return ConfigValidator(raw).validate()


def _errors(raw: dict) -> list[ConfigIssue]:
    return [i for i in _issues(raw) if i.level == "error"]


def _warnings(raw: dict) -> list[ConfigIssue]:
    return [i for i in _issues(raw) if i.level == "warning"]


VALID_BASE = {
    "version": "1.0.0",
    "project": {"name": "test", "description": "desc"},
}


class TestRequiredFields:
    def test_missing_version(self):
        raw = {"project": {"name": "x", "description": "y"}}
        paths = [i.path for i in _errors(raw)]
        assert "version" in paths

    def test_missing_project_name(self):
        raw = {"version": "1.0", "project": {"description": "y"}}
        paths = [i.path for i in _errors(raw)]
        assert "project.name" in paths

    def test_missing_project_description(self):
        raw = {"version": "1.0", "project": {"name": "x"}}
        paths = [i.path for i in _errors(raw)]
        assert "project.description" in paths

    def test_valid_required_fields_no_errors(self):
        assert _errors(VALID_BASE) == []

    def test_empty_config_reports_all_required_fields(self):
        paths = [i.path for i in _errors({})]
        assert "version" in paths
        assert "project.name" in paths
        assert "project.description" in paths


class TestProviderEnum:
    def test_invalid_provider_name_is_error(self):
        raw = {**VALID_BASE, "llm": {"completion": {"provider": "foobar"}}}
        errors = _errors(raw)
        assert any(i.path.endswith(".provider") for i in errors)

    def test_valid_provider_names_accepted(self):
        for p in ("anthropic", "claude-cli", "openai-compat", "huggingface"):
            raw = {**VALID_BASE, "llm": {"completion": {"provider": p}}}
            provider_errors = [
                i for i in _errors(raw)
                if "provider" in i.path and "enum" in i.message.lower()
            ]
            assert provider_errors == [], f"Provider {p!r} should be valid"

    def test_error_message_lists_allowed_providers(self):
        raw = {**VALID_BASE, "llm": {"completion": {"provider": "bad"}}}
        errors = [i for i in _errors(raw) if "provider" in i.path]
        assert errors
        assert any(
            p in errors[0].message
            for p in ("anthropic", "openai-compat", "claude-cli", "huggingface")
        )


class TestOpenAiCompatConsistency:
    def test_missing_base_url_is_error(self):
        raw = {**VALID_BASE, "llm": {"completion": {"provider": "openai-compat", "model": "x"}}}
        paths = [i.path for i in _errors(raw)]
        assert "llm.completion.base_url" in paths

    def test_missing_model_is_error(self):
        raw = {**VALID_BASE, "llm": {"completion": {"provider": "openai-compat", "base_url": "http://x"}}}
        paths = [i.path for i in _errors(raw)]
        assert "llm.completion.model" in paths

    def test_complete_openai_compat_config_no_errors(self):
        raw = {**VALID_BASE, "llm": {"completion": {
            "provider": "openai-compat", "base_url": "http://x", "model": "m"
        }}}
        assert _errors(raw) == []


class TestHuggingFaceConsistency:
    def test_serverless_without_token_is_error(self, monkeypatch):
        monkeypatch.delenv("HF_TOKEN", raising=False)
        raw = {**VALID_BASE, "llm": {"completion": {
            "provider": "huggingface", "hf_mode": "serverless", "model": "x"
        }}}
        assert _errors(raw)

    def test_dedicated_without_endpoint_is_error(self, monkeypatch):
        monkeypatch.setenv("HF_TOKEN", "tok")
        raw = {**VALID_BASE, "llm": {"completion": {
            "provider": "huggingface", "hf_mode": "dedicated", "model": "x"
        }}}
        assert _errors(raw)


class TestAnthropicConsistency:
    def test_missing_api_key_is_warning_not_error(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        raw = {**VALID_BASE, "llm": {"completion": {"provider": "anthropic"}}}
        assert _warnings(raw)
        assert not _errors(raw)

    def test_api_key_via_env_var_no_warning(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        raw = {**VALID_BASE, "llm": {"completion": {"provider": "anthropic"}}}
        assert _warnings(raw) == []


class TestNoEarlyExit:
    def test_multiple_errors_all_reported(self):
        raw = {"project": {}}  # missing version, project.name, project.description
        paths = [i.path for i in _errors(raw)]
        assert len(paths) >= 3

    def test_missing_llm_block_no_crash(self):
        raw = VALID_BASE.copy()
        issues = _issues(raw)  # must not raise
        assert isinstance(issues, list)
