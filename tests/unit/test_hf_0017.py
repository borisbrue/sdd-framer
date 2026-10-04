"""HF-0017: `sdd start` legt für Nicht-Python-Artefakte keine pytest-Stubs an (#141).

Im Rust/Tauri-Projekt standen danach `import pytest`-Platzhalter und LLM-generierte
pytest-Module in `crates/<crate>/tests/*.rs`; `cargo test` brach ab, und für ein
noch nicht existierendes Crate entstand ein Verzeichnis ohne `Cargo.toml`.
"""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from sdd_cli.config import load_config
from sdd_cli.lifecycle import start_spec
from sdd_cli.llm.base import CompletionResult, UsageMetadata
from sdd_cli.main import cli

PYTEST_CODE = "import pytest\n\n\nclass TestX:\n    def test_a(self):\n        assert True\n"


def _projekt(root: Path) -> Path:
    sdd = root / ".sdd"
    (sdd / "specs").mkdir(parents=True)
    (sdd / "tests" / "unit").mkdir(parents=True)
    (sdd / "config.yaml").write_text("project:\n  id: PRJ-0001\n  name: T\n", encoding="utf-8")
    (sdd / "specs" / "SPEC-0001-demo.md").write_text(
        "---\nid: SPEC-0001\ntitle: Demo\nstatus: approved\nowner: B\n"
        "version: 0.1.0\ntests:\n- TST-0001\n- TST-0002\n---\n\n# Demo\n", encoding="utf-8")
    for tst, artifact, framework in (
        ("TST-0001", "crates/neu/tests/import_plan.rs", "cargo test"),
        ("TST-0002", "tests/unit/test_py.py", "pytest"),
    ):
        (sdd / "tests" / "unit" / f"{tst}-x.md").write_text(
            f"---\nid: {tst}\ntitle: T\nlevel: unit\nspec: SPEC-0001\ncontract: CON-0001\n"
            f'artifact: "{artifact}"\nframework: "{framework}"\n---\n\n# T\n',
            encoding="utf-8")
    return root


def _provider() -> MagicMock:
    provider = MagicMock()
    provider.complete.return_value = CompletionResult(text=PYTEST_CODE, usage=UsageMetadata())
    return provider


def test_rs_artefakt_wird_nicht_angelegt(tmp_path):
    root = _projekt(tmp_path)
    provider = _provider()
    with patch("sdd_cli.llm.factory.get_completion_provider", return_value=provider):
        result = start_spec(load_config(root), "SPEC-0001")

    assert not (root / "crates").exists()
    assert result.stubs_unsupported == [root / "crates/neu/tests/import_plan.rs"]
    assert root / "crates/neu/tests/import_plan.rs" not in result.stubs_created
    # Der LLM-Lauf passiert nur für den Python-Test
    assert provider.complete.call_count == 1


def test_py_artefakt_wird_weiter_generiert(tmp_path):
    root = _projekt(tmp_path)
    with patch("sdd_cli.llm.factory.get_completion_provider", return_value=_provider()):
        result = start_spec(load_config(root), "SPEC-0001")

    py = root / "tests/unit/test_py.py"
    assert result.stubs_generated == [py]
    assert py.read_text(encoding="utf-8") == PYTEST_CODE.strip()


def test_cli_nennt_nicht_angelegte_datei(tmp_path):
    root = _projekt(tmp_path)
    alt = Path.cwd()
    os.chdir(root)
    try:
        with patch("sdd_cli.llm.factory.get_completion_provider", return_value=_provider()):
            result = CliRunner().invoke(cli, ["start", "SPEC-0001", "--no-container"])
    finally:
        os.chdir(alt)

    assert "crates/neu/tests/import_plan.rs" in result.output
    assert "Nicht angelegt" in result.output
