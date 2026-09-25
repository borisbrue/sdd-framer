"""Testhilfen für SPEC-0060 (Usage-Erfassung)."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
ENVELOPE = REPO / "tests/fixtures/usage/claude_envelope.json"


def _erfassung_vorhanden() -> bool:
    from sdd_cli.llm.base import UsageMetadata

    return "source" in UsageMetadata.__dataclass_fields__


requires_usage_capture = pytest.mark.skipif(
    not _erfassung_vorhanden(), reason="Usage-Erfassung noch nicht implementiert (SPEC-0060)")


class FakeSink:
    def __init__(self) -> None:
        self.records: list = []

    def record(self, record) -> None:
        self.records.append(record)


class KaputteSink:
    def record(self, record) -> None:
        raise OSError("Datenbank gesperrt")


def claude_prozess(monkeypatch, envelope: dict | str) -> None:
    """Ersetzt `claude --print` durch eine vorbereitete Ausgabe."""
    from sdd_cli.llm.providers import claude_cli

    stdout = envelope if isinstance(envelope, str) else json.dumps(envelope)
    monkeypatch.setattr(claude_cli, "_find_claude", lambda: "/usr/bin/claude")
    monkeypatch.setattr(claude_cli.subprocess, "run",
                        lambda *a, **k: subprocess.CompletedProcess(a, 0, stdout, ""))


def projekt_mit_llm(root: Path, base_url: str) -> None:
    """sdd-Projekt, dessen Komponenten alle auf den Fake-Server zeigen."""
    from sdd_cli.init import init_project

    init_project(root, title="Usage")
    pfad = root / ".sdd/config.yaml"
    daten = yaml.safe_load(pfad.read_text()) or {}
    block = {"provider": "openai-compat", "base_url": base_url, "api_key": "fake"}
    daten["llm"] = {k: {**block, "model": f"fake-{k}"} for k in
                    ("completion", "evaluator", "analyzer", "ai_routes", "local_llm",
                     "orchestrator")}
    pfad.write_text(yaml.safe_dump(daten, sort_keys=False))
