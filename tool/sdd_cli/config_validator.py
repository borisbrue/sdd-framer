"""Config-Validator – SPEC-0052.

Chain of Responsibility: jeder ConfigCheck sammelt Issues unabhängig.
Composite: LlmSectionCheck traversiert alle llm.<component>-Blöcke.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

_ALLOWED_PROVIDERS = ("anthropic", "claude-cli", "openai-compat", "huggingface")
_LLM_COMPONENTS = (
    "completion", "evaluator", "analyzer", "ai_routes",
    "local_llm", "orchestrator", "code_gen",
)


@dataclass
class ConfigIssue:
    level: str   # "error" | "warning"
    path: str
    message: str


class ConfigCheck:
    def run(self, raw: dict, issues: list[ConfigIssue]) -> None:
        raise NotImplementedError


class RequiredFieldsCheck(ConfigCheck):
    def run(self, raw: dict, issues: list[ConfigIssue]) -> None:
        if not raw.get("version"):
            issues.append(ConfigIssue("error", "version", "Pflichtfeld 'version' fehlt."))
        project = raw.get("project") or {}
        if not project.get("name"):
            issues.append(ConfigIssue("error", "project.name", "Pflichtfeld 'project.name' fehlt."))
        if not project.get("description"):
            issues.append(ConfigIssue("error", "project.description", "Pflichtfeld 'project.description' fehlt."))


class ProviderEnumCheck(ConfigCheck):
    def run(self, raw: dict, issues: list[ConfigIssue]) -> None:
        llm = raw.get("llm") or {}
        for component, block in llm.items():
            if not isinstance(block, dict):
                continue
            provider = block.get("provider")
            if provider and provider not in _ALLOWED_PROVIDERS:
                issues.append(ConfigIssue(
                    "error",
                    f"llm.{component}.provider",
                    f"Ungültiger Provider {provider!r}. "
                    f"Erlaubt: {', '.join(_ALLOWED_PROVIDERS)}.",
                ))


class OpenAiCompatCheck(ConfigCheck):
    def run(self, raw: dict, issues: list[ConfigIssue]) -> None:
        llm = raw.get("llm") or {}
        completion_block = llm.get("completion") or {}
        for component, block in llm.items():
            if not isinstance(block, dict):
                continue
            if block.get("provider") != "openai-compat":
                continue
            base_url = block.get("base_url") or completion_block.get("base_url")
            model = block.get("model") or completion_block.get("model")
            prefix = f"llm.{component}"
            if not base_url:
                issues.append(ConfigIssue("error", f"{prefix}.base_url",
                    f"{prefix}.base_url ist Pflicht für provider: openai-compat."))
            if not model:
                issues.append(ConfigIssue("error", f"{prefix}.model",
                    f"{prefix}.model ist Pflicht für provider: openai-compat."))


class HuggingFaceCheck(ConfigCheck):
    def run(self, raw: dict, issues: list[ConfigIssue]) -> None:
        llm = raw.get("llm") or {}
        for component, block in llm.items():
            if not isinstance(block, dict):
                continue
            if block.get("provider") != "huggingface":
                continue
            mode = block.get("hf_mode", "serverless")
            prefix = f"llm.{component}"
            if mode in ("serverless", "dedicated"):
                token = block.get("hf_token") or os.environ.get("HF_TOKEN")
                if not token:
                    issues.append(ConfigIssue("error", f"{prefix}.hf_token",
                        f"hf_token (oder $HF_TOKEN) ist Pflicht für huggingface hf_mode={mode}."))
            if mode == "dedicated":
                if not block.get("endpoint_url"):
                    issues.append(ConfigIssue("error", f"{prefix}.endpoint_url",
                        f"{prefix}.endpoint_url ist Pflicht für hf_mode=dedicated."))


class AnthropicCheck(ConfigCheck):
    def run(self, raw: dict, issues: list[ConfigIssue]) -> None:
        llm = raw.get("llm") or {}
        for component, block in llm.items():
            if not isinstance(block, dict):
                continue
            if block.get("provider") != "anthropic":
                continue
            raw_key = block.get("api_key") or ""
            if raw_key.startswith("${") and raw_key.endswith("}"):
                env_var = raw_key[2:-1]
                resolved = os.environ.get(env_var)
            else:
                resolved = raw_key or os.environ.get("ANTHROPIC_API_KEY")
            if not resolved:
                issues.append(ConfigIssue("warning", f"llm.{component}.api_key",
                    "api_key (oder $ANTHROPIC_API_KEY) nicht gesetzt. "
                    "Keyfreier Betrieb via claude-cli bleibt möglich."))


class ConfigValidator:
    _CHECKS: list[ConfigCheck] = [
        RequiredFieldsCheck(),
        ProviderEnumCheck(),
        OpenAiCompatCheck(),
        HuggingFaceCheck(),
        AnthropicCheck(),
    ]

    def __init__(self, raw: dict) -> None:
        self._raw = raw

    def validate(self) -> list[ConfigIssue]:
        issues: list[ConfigIssue] = []
        for check in self._CHECKS:
            check.run(self._raw, issues)
        return issues
