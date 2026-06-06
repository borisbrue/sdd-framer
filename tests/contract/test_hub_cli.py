"""Hub CLI Contract-Tests – sdd hub register, sdd hub status."""
from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from sdd_cli.main import cli


def _runner() -> CliRunner:
    return CliRunner()


def test_hub_register_creates_entry(tmp_path, monkeypatch):
    reg_path = tmp_path / "registry.yaml"
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / ".config" / "sdd").mkdir(parents=True)
    reg_path = tmp_path / ".config" / "sdd" / "hub-registry.yaml"

    result = _runner().invoke(cli, [
        "hub", "register",
        "--name", "myapp",
        "--path", str(tmp_path),
        "--cmd", "python", "--cmd", "app.py",
        "--port", "3000",
    ])
    assert result.exit_code == 0
    assert "myapp" in result.output
    assert reg_path.exists()


def test_hub_register_duplicate_fails(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / ".config" / "sdd").mkdir(parents=True)

    args = ["hub", "register", "--name", "dup", "--path", str(tmp_path), "--cmd", "x", "--port", "1111"]
    _runner().invoke(cli, args)
    result = _runner().invoke(cli, args)
    assert result.exit_code != 0


def test_hub_register_force_overwrites(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / ".config" / "sdd").mkdir(parents=True)

    args = ["hub", "register", "--name", "dup", "--path", str(tmp_path), "--cmd", "x", "--port", "1111"]
    _runner().invoke(cli, args)
    result = _runner().invoke(cli, args + ["--force"])
    assert result.exit_code == 0


def test_hub_status_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / ".config" / "sdd").mkdir(parents=True)
    (tmp_path / ".config" / "sdd" / "hub-registry.yaml").write_text("[]")

    result = _runner().invoke(cli, ["hub", "status"])
    assert result.exit_code == 0
    assert "registriert" in result.output.lower() or result.output.strip() != ""


def test_hub_status_shows_registered_project(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / ".config" / "sdd").mkdir(parents=True)

    _runner().invoke(cli, [
        "hub", "register",
        "--name", "shown-app",
        "--path", str(tmp_path),
        "--cmd", "python", "--cmd", "app.py",
        "--port", "5000",
    ])
    result = _runner().invoke(cli, ["hub", "status"])
    assert result.exit_code == 0
    assert "shown-app" in result.output


def test_hub_unregister_removes_entry(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / ".config" / "sdd").mkdir(parents=True)

    _runner().invoke(cli, [
        "hub", "register",
        "--name", "remove-me",
        "--path", str(tmp_path),
        "--cmd", "python", "--cmd", "app.py",
        "--port", "6000",
    ])
    result = _runner().invoke(cli, ["hub", "unregister", "remove-me"])
    assert result.exit_code == 0
    assert "entfernt" in result.output

    status = _runner().invoke(cli, ["hub", "status"])
    assert "remove-me" not in status.output


def test_hub_unregister_unknown_fails(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / ".config" / "sdd").mkdir(parents=True)
    (tmp_path / ".config" / "sdd" / "hub-registry.yaml").write_text("[]")

    result = _runner().invoke(cli, ["hub", "unregister", "ghost"])
    assert result.exit_code != 0
