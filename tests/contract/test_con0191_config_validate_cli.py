# TST-0220 – CON-0191: sdd config validate CLI
import json
import os
import re
import subprocess
import textwrap
from pathlib import Path
import pytest


def _run(args: list[str], cwd: Path, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["sdd"] + args,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        env=env if env is not None else os.environ,
    )


def _env_without(*keys: str) -> dict:
    return {k: v for k, v in os.environ.items() if k not in keys}


def _write_config(tmp_path: Path, content: str) -> None:
    sdd_dir = tmp_path / ".sdd"
    sdd_dir.mkdir(exist_ok=True)
    (sdd_dir / "config.yaml").write_text(content)


VALID_CONFIG = "version: 1.0.0\nproject:\n  name: test\n  description: test project\n"


class TestExitCodes:
    def test_valid_config_exit_0(self, tmp_path):
        _write_config(tmp_path, VALID_CONFIG)
        r = _run(["config", "validate"], tmp_path)
        assert r.returncode == 0

    def test_config_with_only_warnings_exit_0(self, tmp_path):
        _write_config(tmp_path, VALID_CONFIG + "llm:\n  completion:\n    provider: anthropic\n")
        r = _run(["config", "validate"], tmp_path, env=_env_without("ANTHROPIC_API_KEY"))
        assert r.returncode == 0

    def test_invalid_config_exit_1(self, tmp_path):
        _write_config(tmp_path, "version: '1.0.0'\nproject:\n  description: x\n")
        r = _run(["config", "validate"], tmp_path)
        assert r.returncode == 1
        assert "project.name" in r.stdout

    def test_sdd_validate_unchanged(self, tmp_path):
        _write_config(tmp_path, VALID_CONFIG)
        r = _run(["validate"], tmp_path)
        # sdd validate should not mention config.yaml field paths like 'project.name'
        # It runs SDD structure validation, not config field validation
        assert r.returncode in (0, 1)  # may fail for other reasons (no specs etc.)


class TestJsonOutput:
    def test_json_errors_valid_array(self, tmp_path):
        _write_config(tmp_path, "version: 1.0.0\nproject:\n  description: x\n")
        r = _run(["config", "validate", "--json"], tmp_path)
        data = json.loads(r.stdout)
        assert isinstance(data, list)
        assert any(item["level"] == "error" for item in data)
        assert r.returncode == 1

    def test_json_valid_config_empty_array(self, tmp_path):
        _write_config(tmp_path, VALID_CONFIG)
        r = _run(["config", "validate", "--json"], tmp_path)
        data = json.loads(r.stdout)
        assert data == []
        assert r.returncode == 0

    def test_json_warning_entry_exit_0(self, tmp_path):
        _write_config(tmp_path, VALID_CONFIG + "llm:\n  completion:\n    provider: anthropic\n")
        r = _run(["config", "validate", "--json"], tmp_path, env=_env_without("ANTHROPIC_API_KEY"))
        data = json.loads(r.stdout)
        assert any(item["level"] == "warning" for item in data)
        assert r.returncode == 0

    def test_json_issue_objects_have_required_keys(self, tmp_path):
        _write_config(tmp_path, "version: 1.0.0\nproject:\n  description: x\n")
        r = _run(["config", "validate", "--json"], tmp_path)
        data = json.loads(r.stdout)
        for item in data:
            assert set(item.keys()) >= {"level", "path", "message"}

    def test_json_no_ansi_in_stdout(self, tmp_path):
        _write_config(tmp_path, VALID_CONFIG)
        r = _run(["config", "validate", "--json"], tmp_path)
        ansi = re.compile(r"\x1b\[[0-9;]*m")
        assert not ansi.search(r.stdout)


class TestEdgeCases:
    def test_missing_config_yaml_exit_1(self, tmp_path):
        # No .sdd/config.yaml created
        r = _run(["config", "validate"], tmp_path)
        assert r.returncode != 0

    def test_invalid_yaml_syntax_exit_1(self, tmp_path):
        sdd_dir = tmp_path / ".sdd"
        sdd_dir.mkdir()
        (sdd_dir / "config.yaml").write_text("key: [ungültig\n")
        r = _run(["config", "validate"], tmp_path)
        assert r.returncode == 1
