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


def _make_sdd_project(base: Path, name: str = "My Project", port: int | None = None) -> Path:
    sdd_dir = base / ".sdd"
    sdd_dir.mkdir(parents=True)
    cfg: dict = {"project": {"name": name}}
    if port:
        cfg["hub"] = {"port": port}
    import yaml
    (sdd_dir / "config.yaml").write_text(yaml.dump(cfg))
    return base


def test_hub_add_registers_project(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / ".config" / "sdd").mkdir(parents=True)
    project_dir = _make_sdd_project(tmp_path / "myproject", name="My App")

    result = _runner().invoke(cli, ["hub", "add", str(project_dir)])
    assert result.exit_code == 0
    assert "My App" in result.output

    status = _runner().invoke(cli, ["hub", "status"])
    assert "my-app" in status.output


def test_hub_add_saves_port_to_config(tmp_path, monkeypatch):
    import yaml
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / ".config" / "sdd").mkdir(parents=True)
    project_dir = _make_sdd_project(tmp_path / "porttest", name="Port Test")

    _runner().invoke(cli, ["hub", "add", str(project_dir)])

    saved = yaml.safe_load((project_dir / ".sdd" / "config.yaml").read_text())
    assert "hub" in saved
    assert isinstance(saved["hub"]["port"], int)


def test_hub_add_reuses_existing_port(tmp_path, monkeypatch):
    import yaml
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / ".config" / "sdd").mkdir(parents=True)
    project_dir = _make_sdd_project(tmp_path / "reuseport", name="Reuse", port=9321)

    _runner().invoke(cli, ["hub", "add", str(project_dir)])

    saved = yaml.safe_load((project_dir / ".sdd" / "config.yaml").read_text())
    assert saved["hub"]["port"] == 9321


def test_hub_add_fails_without_sdd_project(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / ".config" / "sdd").mkdir(parents=True)
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    result = _runner().invoke(cli, ["hub", "add", str(empty_dir)])
    assert result.exit_code != 0


def test_hub_add_duplicate_fails_without_force(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / ".config" / "sdd").mkdir(parents=True)
    project_dir = _make_sdd_project(tmp_path / "dup", name="Dup App")

    _runner().invoke(cli, ["hub", "add", str(project_dir)])
    result = _runner().invoke(cli, ["hub", "add", str(project_dir)])
    assert result.exit_code != 0


def test_hub_add_force_overwrites(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / ".config" / "sdd").mkdir(parents=True)
    project_dir = _make_sdd_project(tmp_path / "forcedup", name="Force App")

    _runner().invoke(cli, ["hub", "add", str(project_dir)])
    result = _runner().invoke(cli, ["hub", "add", "--force", str(project_dir)])
    assert result.exit_code == 0
