"""Interaktiver Config-Wizard für SPEC-0027 (CON-0102, CON-0105).

Builder Pattern: Schritt-für-Schritt durch Config-Sections, atomares Schreiben am Ende.
Strategy Pattern: Jede Section ist ein eigener Schritt mit Validierung + Defaults.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

from .config_manager import (
    ConfigManager, ConfigValidationError,
    PLACEHOLDER_DESCRIPTION, STRATEGIES, RUNTIMES,
    _validate_business_rules,
)

SECTIONS = ("project", "llm", "docker", "evaluator", "orchestrator")
_KEY_PREFIX = "sk-", "ant-", "hf-"


class WizardAbortError(Exception):
    """Raised on Ctrl+C to signal clean abort without changing config."""


class ConfigWizard:
    """Builder: collects config section by section, writes atomically."""

    def __init__(self, config_path: Path) -> None:
        self._path = config_path
        self._mgr = ConfigManager(config_path)

    @staticmethod
    def needs_setup(config: dict) -> bool:
        return config.get("project", {}).get("description", "") == PLACEHOLDER_DESCRIPTION

    def run(
        self,
        section: str | None = None,
        non_interactive: bool = False,
        **kwargs: Any,
    ) -> dict:
        backup = self._mgr.load()
        try:
            data = dict(backup)
            sections = [section] if section else list(SECTIONS)
            for sec in sections:
                handler = getattr(self, f"_section_{sec}", None)
                if handler:
                    data = handler(data, non_interactive=non_interactive, **kwargs)
            errors = _validate_business_rules(data)
            if errors:
                raise ConfigValidationError("\n".join(errors))
            _write_wizard(self._path, data)
            return data
        except (KeyboardInterrupt, WizardAbortError):
            return backup

    # ── Sections ─────────────────────────────────────────────────────────────

    def _section_project(self, data: dict, non_interactive: bool = False, **kwargs) -> dict:
        desc = kwargs.get("project_description") or data.get("project", {}).get("description", "")
        if not non_interactive:
            desc = _prompt("Projektbeschreibung", default=desc)
        if not desc:
            raise ConfigValidationError("Projektbeschreibung darf nicht leer sein")
        data.setdefault("project", {})["description"] = desc
        return data

    def _section_llm(self, data: dict, non_interactive: bool = False, **kwargs) -> dict:
        if non_interactive:
            strategy = kwargs.get("llm_strategy", data.get("llm_pool", {}).get("strategy", "cost_first"))
            data.setdefault("llm_pool", {})["strategy"] = strategy
            return data

        print("\n── LLM-Pool ────────────────────────────────────────────")
        strategy = _choice("Auswahlstrategie", STRATEGIES,
                           default=data.get("llm_pool", {}).get("strategy", "cost_first"))
        pool = data.get("llm_pool", {})
        pool["strategy"] = strategy
        providers = list(pool.get("providers") or [])
        while True:
            another = _confirm("Weiteren LLM-Provider hinzufügen?", default=True)
            if not another:
                break
            p = _collect_provider(providers)
            providers.append(p)
        pool["providers"] = providers
        data["llm_pool"] = pool
        return data

    def _section_docker(self, data: dict, non_interactive: bool = False, **kwargs) -> dict:
        docker = data.get("docker", {})

        if non_interactive:
            max_par = kwargs.get("docker_max_parallel", docker.get("max_parallel_containers", 2))
            max_par = int(max_par)
            if max_par < 1:
                raise ConfigValidationError(
                    f"docker.max_parallel_containers muss ≥ 1 sein, nicht {max_par}"
                )
            docker["max_parallel_containers"] = max_par
            data["docker"] = docker
            return data

        print("\n── Docker ──────────────────────────────────────────────")
        from .dev_container import resolve_runtime
        # Im Wizard liegt nur der docker-Teilbaum vor.
        runtime = _choice("Runtime", RUNTIMES,
                          default=resolve_runtime({"docker": docker}))
        image = _prompt("Image-Name", default=docker.get("image", "sdd-dev:latest"))
        dockerfile = _prompt("Dockerfile-Pfad", default=docker.get("dockerfile", ".sdd/Dockerfile"))
        max_par = _prompt_int("Maximale parallele Container", default=docker.get("max_parallel_containers", 2), min_val=1)
        cpu = _prompt("CPU-Limit (leer = kein Limit)", default=docker.get("resources", {}).get("cpu_limit", ""))
        mem = _prompt("Memory-Limit (leer = kein Limit)", default=docker.get("resources", {}).get("memory_limit", ""))
        on_success = _confirm("Container nach Erfolg löschen?", default=docker.get("cleanup", {}).get("on_success", True))
        on_failure = _confirm("Container bei Fehler löschen?", default=docker.get("cleanup", {}).get("on_failure", False))
        skip = _confirm("Fallback auf lokale Tests wenn Docker fehlt?", default=docker.get("skip_if_unavailable", False))
        reg_url = _prompt("Registry-URL (leer = keine)", default=docker.get("registry", {}).get("url", ""))
        reg_auth = ""
        if reg_url:
            reg_auth = _prompt("Registry Auth-Env-Var", default=docker.get("registry", {}).get("auth_env", ""))

        docker.update({
            "runtime": runtime,
            "image": image,
            "dockerfile": dockerfile,
            "max_parallel_containers": max_par,
            "resources": {k: v for k, v in [("cpu_limit", cpu), ("memory_limit", mem)] if v},
            "cleanup": {"on_success": on_success, "on_failure": on_failure},
            "registry": {"url": reg_url, "auth_env": reg_auth},
            "skip_if_unavailable": skip,
        })
        data["docker"] = docker
        return data

    def _section_evaluator(self, data: dict, non_interactive: bool = False, **kwargs) -> dict:
        return data

    def _section_orchestrator(self, data: dict, non_interactive: bool = False, **kwargs) -> dict:
        return data


# ── Helper I/O ────────────────────────────────────────────────────────────────

def _prompt(label: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    try:
        raw = input(f"  {label}{suffix}: ").strip()
    except EOFError:
        return default
    return raw or default


def _prompt_int(label: str, default: int = 1, min_val: int = 1) -> int:
    while True:
        raw = _prompt(label, str(default))
        try:
            val = int(raw)
        except ValueError:
            print(f"  Bitte eine ganze Zahl eingeben.")
            continue
        if val < min_val:
            print(f"  Muss mindestens {min_val} sein.")
            continue
        return val


def _choice(label: str, options: tuple, default: str = "") -> str:
    opts_str = " / ".join(options)
    while True:
        raw = _prompt(f"{label} ({opts_str})", default=default)
        if raw in options:
            return raw
        print(f"  Ungültig. Mögliche Werte: {opts_str}")


def _confirm(label: str, default: bool = True) -> bool:
    default_str = "J/n" if default else "j/N"
    raw = _prompt(f"{label} ({default_str})", "").lower()
    if not raw:
        return default
    return raw.startswith("j") or raw.startswith("y")


def _collect_provider(existing: list[dict]) -> dict:
    existing_ids = {p.get("id") for p in existing}
    while True:
        pid = _prompt("Provider-ID (einmalig, z.B. ollama-mistral)")
        if pid in existing_ids:
            print(f"  ID '{pid}' bereits vorhanden.")
            continue
        if pid:
            break

    ptype = _choice("Typ", ("local", "remote"), default="remote")
    model = _prompt("Modell-Name", default="mistral:7b" if ptype == "local" else "claude-sonnet-4-6")
    tier = _choice("Cost-Tier", ("cheap", "standard", "powerful"), default="cheap" if ptype == "local" else "standard")
    max_tok = int(_prompt("Max-Kontext-Tokens", default="32000" if ptype == "local" else "200000"))

    p: dict = {"id": pid, "type": ptype, "model": model, "cost_tier": tier, "max_context_tokens": max_tok}

    if ptype == "local":
        base_url = _prompt("Base-URL", default="http://localhost:11434")
        p["base_url"] = base_url
    else:
        while True:
            key_env = _prompt("API-Key Env-Var-Name (z.B. ANTHROPIC_API_KEY)")
            if any(key_env.startswith(pfx) for pfx in _KEY_PREFIX):
                print("  Sicherheit: Bitte keinen direkten API-Key eingeben, nur den Env-Var-Namen.")
                continue
            p["api_key_env"] = key_env
            break
    return p


def _write_wizard(path: Path, data: dict) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    import os
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
