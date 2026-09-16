"""Generator und Runner sind nicht mehr auf Python festgelegt (HF-0010).

Der gemeldete Fall: ein Rust-Projekt mit zehn fertigen `.rs`-Testdateien. `sdd test
generate` pruefte jede mit `ast.parse`, erklaerte sie fuer "nicht auswertbar" und
markierte die Gate-Phase `tests-generated` als fehlgeschlagen — `sdd spec approve`
blieb damit unerreichbar, obwohl die Tests existierten und liefen. `sdd test run`
haengte an `cargo test` die pytest-Argumente `--tb=short -q` und machte jeden Lauf rot.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tool"))

from sdd_cli import test_runner
from sdd_cli.config import load_config
from sdd_cli.test_generator import TestGenerator as Generator
from sdd_cli.test_languages import (
    GO,
    NODE,
    PYTHON,
    RUST,
    language_for_path,
    language_for_runner,
)

_FEATURE = """Feature: Beispiel
  Scenario: Happy Path
    Given etwas
    When ich handle
    Then passiert etwas
"""


@pytest.fixture(autouse=True)
def _cache_leeren():
    test_runner._RUNNER_CACHE.clear()
    yield
    test_runner._RUNNER_CACHE.clear()


def _projekt(root: Path, runner: str = "pytest") -> Path:
    (root / ".sdd").mkdir(parents=True, exist_ok=True)
    (root / ".sdd" / "config.yaml").write_text(
        f"version: 1.0.0\nproject:\n  name: T\ntest_runner:\n  command: {runner}\n"
        f"  extra_args: []\n  timeout_per_spec: 30\n",
        encoding="utf-8",
    )
    return root


def _contract(root: Path, con_id: str = "CON-0001") -> None:
    d = root / ".sdd" / "contracts" / "behavior"
    d.mkdir(parents=True, exist_ok=True)
    artifact = f"contracts/behavior/{con_id.lower()}.feature"
    (root / artifact).parent.mkdir(parents=True, exist_ok=True)
    (root / artifact).write_text(_FEATURE, encoding="utf-8")
    (d / f"{con_id}-x.md").write_text(
        f"---\nid: {con_id}\ntitle: T\ntype: behavior\nformat: gherkin\n"
        f'spec: SPEC-0001\nartifact: "{artifact}"\n---\n\n# C\n',
        encoding="utf-8",
    )


def _test_doc(root: Path, artifact: str | None, tst_id: str = "TST-0001",
              con_id: str = "CON-0001", level: str = "contract") -> None:
    d = root / ".sdd" / "tests" / level
    d.mkdir(parents=True, exist_ok=True)
    art = f'artifact: "{artifact}"\n' if artifact else ""
    (d / f"{tst_id}-x.md").write_text(
        f"---\nid: {tst_id}\ntitle: T\nlevel: {level}\nspec: SPEC-0001\n"
        f"contract: {con_id}\nstatus: planned\n{art}---\n\n# T\n",
        encoding="utf-8",
    )


class TestSpracherkennung:
    @pytest.mark.parametrize("pfad,erwartet", [
        ("tests/unit/test_a.py", PYTHON),
        ("crates/core/tests/change_watcher.rs", RUST),
        ("src/app.test.ts", NODE),
        ("web/app.spec.js", NODE),
        ("pkg/server/handler_test.go", GO),
    ])
    def test_endung_bestimmt_die_sprache(self, pfad, erwartet):
        assert language_for_path(pfad) is erwartet

    def test_unbekannte_endung_hat_kein_profil(self):
        assert language_for_path("spec/a_spec.rb") is None

    @pytest.mark.parametrize("kommando,erwartet", [
        ("pytest", PYTHON),
        ("uv run pytest", PYTHON),
        ("cargo test --workspace", RUST),
        ("npm test", NODE),
        ("go test ./...", GO),
    ])
    def test_kommando_verraet_die_sprache(self, kommando, erwartet):
        """`uv run pytest` beginnt mit uv, meint aber Python."""
        assert language_for_runner(kommando) is erwartet

    def test_unbekanntes_kommando(self):
        assert language_for_runner("meinrunner --alles") is None


class TestKommandoBau:
    def test_python_bekommt_den_pfad_und_pytest_argumente(self):
        argv = PYTHON.run_argv(["uv", "run", "pytest"], Path("/r/tests/a.py"), Path("/r"))
        assert argv == ["uv", "run", "pytest", "/r/tests/a.py", "--tb=short", "-q"]

    def test_rust_waehlt_das_testziel_ueber_den_dateinamen(self):
        """Der gemeldete Fehler: `cargo test <pfad> --tb=short -q` kennt cargo nicht."""
        argv = RUST.run_argv(["cargo", "test", "--workspace"],
                             Path("/r/crates/core/tests/change_watcher.rs"), Path("/r"))
        assert argv == ["cargo", "test", "--workspace", "--test", "change_watcher"]

    def test_rust_laesst_ein_eigenes_testziel_stehen(self):
        argv = RUST.run_argv(["cargo", "test", "--test", "alles"],
                             Path("/r/crates/core/tests/x.rs"), Path("/r"))
        assert argv == ["cargo", "test", "--test", "alles"]

    def test_paketmanager_reicht_erst_nach_doppelstrich_durch(self):
        argv = NODE.run_argv(["npm", "test"], Path("/r/src/a.test.ts"), Path("/r"))
        assert argv == ["npm", "test", "--", "src/a.test.ts"]

    def test_direkter_node_runner_ohne_doppelstrich(self):
        argv = NODE.run_argv(["vitest", "run"], Path("/r/src/a.test.ts"), Path("/r"))
        assert argv == ["vitest", "run", "src/a.test.ts"]

    def test_go_adressiert_das_paketverzeichnis(self):
        argv = GO.run_argv(["go", "test"], Path("/r/pkg/server/handler_test.go"), Path("/r"))
        assert argv == ["go", "test", "./pkg/server"]

    def test_nur_python_bringt_eine_syntaxpruefung_mit(self):
        assert PYTHON.syntax_error("def f(:") is not None
        assert PYTHON.syntax_error("def f():\n    pass\n") is None
        assert RUST.syntax_error("fn f( {") is None, "ohne Parser kein Urteil"


class TestGeneratorFremdeSprache:
    def test_vorhandene_rust_datei_wird_anerkannt(self, tmp_path):
        """Der gemeldete Fall: zehn fertige .rs-Dateien blockierten das Gate."""
        _projekt(tmp_path, runner="cargo test --workspace")
        _contract(tmp_path)
        _test_doc(tmp_path, "crates/core/tests/change_watcher.rs")
        ziel = tmp_path / "crates" / "core" / "tests" / "change_watcher.rs"
        ziel.parent.mkdir(parents=True)
        inhalt = "#[test]\nfn a() { assert!(true); }\n"
        ziel.write_text(inhalt, encoding="utf-8")

        result = Generator(tmp_path).generate("SPEC-0001", ["CON-0001"])

        assert result.success, "vorhandene Testdatei darf die Phase nicht scheitern lassen"
        assert result.generated_files[0]["status"] == "foreign"
        assert ziel.read_text(encoding="utf-8") == inhalt
        assert not list(ziel.parent.glob("*.bak"))

    def test_fehlende_rust_datei_wird_gemeldet_statt_erfunden(self, tmp_path):
        _projekt(tmp_path, runner="cargo test --workspace")
        _contract(tmp_path)
        _test_doc(tmp_path, "crates/core/tests/change_watcher.rs")

        result = Generator(tmp_path).generate("SPEC-0001", ["CON-0001"])

        assert not result.success
        assert result.generated_files[0]["status"] == "foreign-missing"
        assert len(result.fehlende_dateien) == 1
        meldung = result.fehlende_dateien[0]
        assert "change_watcher.rs" in meldung and "Rust" in meldung
        assert not (tmp_path / "crates").exists(), "kein erfundener Code"

    def test_kein_python_rumpf_in_einer_rust_datei(self, tmp_path):
        _projekt(tmp_path, runner="cargo test")
        _contract(tmp_path)
        _test_doc(tmp_path, "crates/core/tests/x.rs")
        ziel = tmp_path / "crates" / "core" / "tests" / "x.rs"
        ziel.parent.mkdir(parents=True)
        ziel.write_text("#[test]\nfn a() {}\n", encoding="utf-8")

        Generator(tmp_path).generate("SPEC-0001", ["CON-0001"])

        assert "pytest" not in ziel.read_text(encoding="utf-8")

    def test_rueckfall_erfindet_in_einem_rust_projekt_keine_py_datei(self, tmp_path):
        """Ohne artifact im TST-Dokument entschied bisher die Format-Tabelle — immer .py."""
        _projekt(tmp_path, runner="cargo test --workspace")
        _contract(tmp_path)
        _test_doc(tmp_path, artifact=None)

        result = Generator(tmp_path).generate("SPEC-0001", ["CON-0001"])

        assert not result.success
        assert not list(tmp_path.rglob("*.py"))
        assert "Rust" in result.fehlende_dateien[0]

    def test_python_verhaelt_sich_unveraendert(self, tmp_path):
        _projekt(tmp_path)
        _contract(tmp_path)
        _test_doc(tmp_path, "tests/contract/test_beispiel.py")

        result = Generator(tmp_path).generate("SPEC-0001", ["CON-0001"])

        ziel = tmp_path / "tests" / "contract" / "test_beispiel.py"
        assert result.success and ziel.exists()
        assert result.generated_files[0]["status"] == "created"
        assert "AUTO-GENERATED" in ziel.read_text(encoding="utf-8")


class TestRunnerFremdeSprache:
    def _projekt_mit_test(self, tmp_path: Path, artifact: str, runner: str) -> Path:
        _projekt(tmp_path, runner=runner)
        _test_doc(tmp_path, artifact)
        ziel = tmp_path / artifact
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text("#[test]\nfn a() {}\n", encoding="utf-8")
        return tmp_path

    def test_rust_artefakt_gilt_als_ausfuehrbar(self, tmp_path):
        root = self._projekt_mit_test(tmp_path, "crates/core/tests/a.rs", "cargo test")
        pfad, status, meldung = test_runner._resolve_artifact(load_config(root), "TST-0001")
        assert status == "passed", meldung

    def test_endung_ohne_profil_wird_uebersprungen_mit_hinweis(self, tmp_path):
        root = self._projekt_mit_test(tmp_path, "spec/a_spec.rb", "rspec")
        _pfad, status, meldung = test_runner._resolve_artifact(load_config(root), "TST-0001")
        assert status == "skipped"
        assert "Sprachprofil" in meldung

    def test_default_pytest_wird_in_rust_zu_cargo_test(self, tmp_path):
        """Der Blueprint-Default darf nicht bedeuten: pytest auf eine .rs-Datei."""
        with patch.object(test_runner.shutil, "which", lambda n: f"/usr/bin/{n}"), \
             patch.object(test_runner.subprocess, "run",
                          lambda cmd, **kw: type("R", (), {"returncode": 0})()):
            assert test_runner._resolve_runner("pytest", tmp_path, RUST) == ["cargo", "test"]

    def test_fehlendes_cargo_nennt_den_konfigurationsschluessel(self, tmp_path):
        with patch.object(test_runner.shutil, "which", lambda n: None):
            with pytest.raises(RuntimeError) as exc:
                test_runner._resolve_runner("pytest", tmp_path, RUST)
        assert "test_runner.command" in str(exc.value)
        assert "cargo test" in str(exc.value)

    def test_python_aufloesung_bleibt_wie_sie_war(self, tmp_path):
        with patch.object(test_runner.shutil, "which", lambda n: f"/usr/bin/{n}"), \
             patch.object(test_runner.subprocess, "run",
                          lambda cmd, **kw: type("R", (), {"returncode": 0})()):
            assert test_runner._resolve_runner("pytest", tmp_path) == [
                sys.executable, "-m", "pytest"]


class TestExitcodes:
    def _lauf(self, tmp_path: Path, artifact: str, runner: str, returncode: int):
        _projekt(tmp_path, runner=runner)
        ziel = tmp_path / artifact
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text("x\n", encoding="utf-8")
        ergebnis = subprocess.CompletedProcess(args=[], returncode=returncode, stdout="", stderr="")
        with patch.object(test_runner, "_resolve_runner", lambda *a, **k: ["runner"]), \
             patch.object(test_runner.subprocess, "run", lambda *a, **k: ergebnis):
            return test_runner._run_artifact_tests(load_config(tmp_path), artifact, 30)

    def test_pytest_exitcode_5_bleibt_leerer_lauf(self, tmp_path):
        status, _dauer, meldung = self._lauf(tmp_path, "tests/a.py", "pytest", 5)
        assert status == "skipped" and "Keine Tests gesammelt" in meldung

    def test_cargo_exitcode_101_ist_rot(self, tmp_path):
        """101 ist bei cargo ein Compile- oder Testfehler, kein leerer Lauf."""
        status, _dauer, _meldung = self._lauf(tmp_path, "crates/c/tests/a.rs", "cargo test", 101)
        assert status == "failed"

    def test_cargo_exitcode_5_ist_ebenfalls_rot(self, tmp_path):
        status, _dauer, _meldung = self._lauf(tmp_path, "crates/c/tests/a.rs", "cargo test", 5)
        assert status == "failed"

    def test_gruener_lauf_bleibt_gruen(self, tmp_path):
        status, _dauer, _meldung = self._lauf(tmp_path, "crates/c/tests/a.rs", "cargo test", 0)
        assert status == "passed"
