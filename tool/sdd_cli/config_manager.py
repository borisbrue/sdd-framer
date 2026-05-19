"""Config-Lese/Schreib-Layer mit Dot-Notation-Zugriff für SPEC-0027 (CON-0104, CON-0106).

Command Pattern: set/get/show/validate sind diskrete Operationen.
Builder Pattern: ConfigManager liest/schreibt atomar – kein Teilzustand.
"""
from __future__ import annotations

import json
import re
import tempfile
import os
from pathlib import Path
from typing import Any

import yaml


_ARRAY_INDEX = re.compile(r"^(.+)\[(\d+)\]$")
_ENV_VAR_NAME = re.compile(r"^[A-Z][A-Z0-9_]+$")
_PLAINTEXT_KEY_PREFIXES = ("sk-", "ant-", "hf-")

PLACEHOLDER_DESCRIPTION = "<PROJECT_DESCRIPTION>"
STRATEGIES = ("cost_first", "quality_first", "local_first")
COST_TIERS = ("cheap", "standard", "powerful")
RUNTIMES = ("docker", "podman")


class ConfigValidationError(ValueError):
    """Raised when config fails schema or business-rule validation."""


class ConfigKeyError(KeyError):
    """Raised when a dot-notation key cannot be resolved."""


def _parse_segment(segment: str) -> tuple[str, int | None]:
    m = _ARRAY_INDEX.match(segment)
    if m:
        return m.group(1), int(m.group(2))
    return segment, None


def _get_nested(data: dict, key: str) -> Any:
    parts = key.split(".")
    cur: Any = data
    for part in parts:
        name, idx = _parse_segment(part)
        if not isinstance(cur, dict) or name not in cur:
            raise ConfigKeyError(key)
        cur = cur[name]
        if idx is not None:
            if not isinstance(cur, list) or idx >= len(cur):
                raise ConfigKeyError(key)
            cur = cur[idx]
    return cur


def _set_nested(data: dict, key: str, value: Any) -> None:
    parts = key.split(".")
    cur: Any = data
    for part in parts[:-1]:
        name, idx = _parse_segment(part)
        if name not in cur:
            cur[name] = {}
        cur = cur[name]
        if idx is not None:
            cur = cur[idx]
    last_name, last_idx = _parse_segment(parts[-1])
    if last_idx is not None:
        if last_name not in cur:
            cur[last_name] = []
        cur[last_name][last_idx] = value
    else:
        cur[last_name] = value


def _coerce(value: str) -> Any:
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value


class ConfigManager:
    """Dot-Notation-Zugriff auf config.yaml mit atomarem Schreiben."""

    def __init__(self, config_path: Path) -> None:
        self._path = config_path

    def load(self) -> dict:
        if not self._path.exists():
            return {}
        with self._path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def get(self, key: str) -> Any:
        data = self.load()
        try:
            return _get_nested(data, key)
        except ConfigKeyError:
            return None

    def set(self, key: str, value: Any) -> None:
        if isinstance(value, str) and any(value.startswith(p) for p in _PLAINTEXT_KEY_PREFIXES):
            raise ConfigValidationError(
                f"Sicherheit: '{value}' sieht wie ein API-Key aus. "
                "Gib stattdessen den Namen der Env-Variable an (z.B. ANTHROPIC_API_KEY)."
            )
        data = self.load()
        _set_nested(data, key, value)
        errors = _validate_business_rules(data)
        if errors:
            raise ConfigValidationError("\n".join(errors))
        _write_atomic(self._path, data)

    def show(self, section: str | None = None) -> str:
        data = self.load()
        if section:
            section_data = data.get(section) or data.get(f"{section}_pool") or {}
            return yaml.dump({section: section_data}, allow_unicode=True, sort_keys=False)
        return yaml.dump(data, allow_unicode=True, sort_keys=False)

    def validate(self) -> list[str]:
        data = self.load()
        return _validate_business_rules(data)


def _write_atomic(path: Path, data: dict) -> None:
    tmp_fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _validate_business_rules(data: dict) -> list[str]:
    errors: list[str] = []

    llm_pool = data.get("llm_pool", {})
    if llm_pool:
        strategy = llm_pool.get("strategy")
        if strategy and strategy not in STRATEGIES:
            errors.append(f"llm_pool.strategy muss einer von {STRATEGIES} sein, nicht '{strategy}'")

        providers = llm_pool.get("providers") or []
        seen_ids: set[str] = set()
        for i, p in enumerate(providers):
            pid = p.get("id", "")
            if pid in seen_ids:
                errors.append(f"Doppelte Provider-ID: '{pid}' (llm_pool.providers[{i}])")
            seen_ids.add(pid)
            if p.get("type") == "remote":
                env = p.get("api_key_env", "")
                if not env:
                    errors.append(
                        f"Remote-Provider '{pid}' braucht api_key_env (llm_pool.providers[{i}])"
                    )
                elif not _ENV_VAR_NAME.match(env):
                    errors.append(
                        f"api_key_env '{env}' für '{pid}' muss ein Env-Var-Name sein (z.B. ANTHROPIC_API_KEY)"
                    )

    docker = data.get("docker", {})
    if docker:
        max_par = docker.get("max_parallel_containers")
        if max_par is not None and (not isinstance(max_par, int) or max_par < 1):
            errors.append("docker.max_parallel_containers muss eine ganze Zahl ≥ 1 sein")

        registry = docker.get("registry", {})
        if registry.get("url") and not registry.get("auth_env"):
            errors.append("docker.registry.auth_env erforderlich wenn docker.registry.url gesetzt ist")

    return errors


def validate_schema(data: dict) -> list[str]:
    """Validates the llm_pool and docker sections against JSON Schema."""
    import jsonschema

    schema_path = (
        Path(__file__).parent.parent.parent
        / "contracts" / "data" / "sdd-config.schema.json"
    )
    if not schema_path.exists():
        return []

    with schema_path.open("r", encoding="utf-8") as f:
        schema = json.load(f)

    errors: list[str] = []
    validator = jsonschema.Draft202012Validator(schema)
    for err in validator.iter_errors(data):
        path = ".".join(str(p) for p in err.absolute_path)
        errors.append(f"Schema: {path}: {err.message}" if path else f"Schema: {err.message}")

    errors.extend(_validate_business_rules(data))
    return errors
