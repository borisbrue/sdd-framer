"""Test-Hilfe für SPEC-0057: Stack-Vorlagen in temporären Quellen und Projekten.

Nutzervorlagen liegen unter ``SDD_STACKS_HOME`` im tmp-Verzeichnis. Die schnelle Vorlage ``demo``
bringt eine ``.sdd/quality.yaml`` mit einer Test-Sonde, die ein vorbereitetes JUnit kopiert; so
prüfen die Tests ``sdd stack verify`` ohne echte Testläufe. Nur die Blueprint-Szenarien starten
die Referenz-Toolchain.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from tests.support.quality_project import QualityProject, junit, make_project

REPO = Path(__file__).resolve().parents[2]
BLUEPRINT_STACKS = REPO / "tool/sdd_cli/blueprint/stacks"
STACK_SCHEMA = (REPO / ".sdd/contracts/data/stack-vorlage-und-stack-eintrag.schema.json")


def write_stack(basis: Path, name: str, files: dict[str, str], *, agents: dict | None = None,
                **stack: object) -> Path:
    """Legt eine Vorlage `basis/name` an; `stack` ergänzt oder ersetzt Felder von stack.yaml."""
    ordner = basis / name
    daten = {"name": name, "version": "1.0.0", "description": f"Testvorlage {name}",
             "languages": ["shell"], **stack}
    (ordner / "files").mkdir(parents=True, exist_ok=True)
    (ordner / "stack.yaml").write_text(yaml.safe_dump(daten, sort_keys=False,
                                                      allow_unicode=True), encoding="utf-8")
    for rel, text in files.items():
        datei = ordner / "files" / rel
        datei.parent.mkdir(parents=True, exist_ok=True)
        datei.write_text(text, encoding="utf-8")
    for abschnitt, text in (agents or {}).items():
        datei = ordner / "agents-md" / f"{abschnitt}.md"
        datei.parent.mkdir(parents=True, exist_ok=True)
        datei.write_text(text, encoding="utf-8")
    return ordner


def demo_files(*, fr: bool = True) -> dict[str, str]:
    """quality.yaml mit einer Test-Sonde, die `.fixtures/tests.xml` kopiert."""
    quality = {"version": 1, "probes": {"tests": {
        "command": "cp .fixtures/tests.xml {out}", "format": "junit", "role": "tests",
        "fr_marker": "property"}}}
    return {
        ".sdd/quality.yaml": yaml.safe_dump(quality, sort_keys=False),
        ".fixtures/tests.xml": junit([("t_skeleton", "passed", ["FR-01"] if fr else [])]),
        "src/{{package_name}}.txt": "Paket {{package_name}} von {{project_name}}\n",
    }


def demo_stack(home: Path, name: str = "demo", *, fr: bool = True, **stack: object) -> Path:
    stack.setdefault("placeholders", [{"name": "project_name"},
                                      {"name": "package_name", "default": "kern"}])
    return write_stack(home, name, demo_files(fr=fr),
                       agents={"stack": "## Stack: demo\n\nPaket `{{package_name}}`.\n"},
                       **stack)


def make_stacks_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "nutzer-stacks"
    home.mkdir()
    monkeypatch.setenv("SDD_STACKS_HOME", str(home))
    return home


def make_stack_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> QualityProject:
    root = tmp_path / "projekt"
    root.mkdir(parents=True)
    return make_project(root, monkeypatch)


def use_reference_toolchain(monkeypatch: pytest.MonkeyPatch) -> None:
    """`python3` der Vorlagen ist der Interpreter der Testsuite (mit pytest)."""
    bin_dir = Path(sys.executable).parent
    if not (bin_dir / "python3").exists():
        pytest.skip("kein python3 neben dem Test-Interpreter")
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")


def git_init(root: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)


def snapshot(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*"))
            if p.is_file() and ".git" not in p.relative_to(root).parts}


def config(root: Path) -> dict:
    return yaml.safe_load((root / ".sdd/config.yaml").read_text(encoding="utf-8")) or {}


def copy_blueprint(name: str, ziel: Path) -> Path:
    zielordner = ziel / name
    shutil.copytree(BLUEPRINT_STACKS / name, zielordner,
                    ignore=shutil.ignore_patterns("__pycache__"))
    return zielordner
