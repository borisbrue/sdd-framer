"""Sprachprofile fuer Testcode (HF-0010).

`sdd test generate` pruefte jede vorhandene Testdatei mit `ast.parse`, und `sdd test run`
haengte pytest-Argumente an jedes konfigurierte Kommando. In einem Rust-, Node- oder
Go-Projekt galt damit jede Testdatei als Syntaxfehler: die Gate-Phase `tests-generated`
liess sich nicht abschliessen, und `sdd spec approve` blieb unerreichbar, obwohl die Tests
vorhanden und lauffaehig waren.

Hier steht je Sprache, was gilt: welche Dateiendungen zu ihr gehoeren, welches Kommando
ihre Tests ausfuehrt, ob sdd fuer sie Ruempfe erzeugen kann und welche Exitcodes
"nichts ausgefuehrt" bedeuten. Eine weitere Sprache ist ein weiterer Eintrag in
`LANGUAGES`; Generator und Runner bleiben unveraendert.

Ruempfe erzeugt sdd bisher nur fuer Python. Fuer die uebrigen Sprachen gilt: eine
vorhandene Datei wird anerkannt und nicht angetastet, eine fehlende wird gemeldet mit
der Bitte, sie anzulegen. Falsch geratener Code in einer fremden Sprache waere schlimmer
als keiner.
"""
from __future__ import annotations

import ast
import shlex
from pathlib import Path


class TestLanguage:
    """Ein Sprachprofil. Unterklassen ueberschreiben nur, was von den Defaults abweicht."""

    name: str = "unbekannt"
    suffixes: tuple[str, ...] = ()
    #: Kommando, wenn `test_runner.command` noch auf dem Blueprint-Default `pytest` steht.
    default_runner: tuple[str, ...] = ()
    #: Erkennt die Sprache am konfigurierten Kommando (erstes Token oder ein Wort darin).
    runner_tokens: tuple[str, ...] = ()
    #: Kann sdd fuer diese Sprache Testruempfe erzeugen?
    generates_stubs: bool = False
    #: Exitcodes, die "kein Test ausgefuehrt" bedeuten — kein rotes Ergebnis.
    empty_run_exit_codes: tuple[int, ...] = ()

    def syntax_error(self, quelltext: str) -> str | None:
        """Meldung, wenn die Sprache eine Syntaxpruefung mitbringt und sie fehlschlaegt.

        Ohne eigenen Parser gibt es kein Urteil — und damit auch keinen Vorwurf an eine
        Datei, die sdd nicht lesen kann.
        """
        return None

    def run_argv(self, runner: list[str], artifact: Path, root: Path) -> list[str]:
        """Vollstaendiges Kommando, das genau diese Testdatei ausfuehrt."""
        return [*runner, str(artifact)]

    def _relativ(self, artifact: Path, root: Path) -> Path:
        try:
            return artifact.relative_to(root)
        except ValueError:
            return artifact


class PythonLanguage(TestLanguage):
    name = "Python"
    suffixes = (".py",)
    default_runner = ("pytest",)
    runner_tokens = ("pytest",)
    generates_stubs = True
    # pytest-Exitcode 5: keine Tests gesammelt.
    empty_run_exit_codes = (5,)

    def syntax_error(self, quelltext: str) -> str | None:
        try:
            ast.parse(quelltext)
        except SyntaxError as exc:
            return f"{exc.lineno}: {exc.msg}"
        return None

    def run_argv(self, runner: list[str], artifact: Path, root: Path) -> list[str]:
        return [*runner, str(artifact), "--tb=short", "-q"]


class RustLanguage(TestLanguage):
    name = "Rust"
    suffixes = (".rs",)
    default_runner = ("cargo", "test")
    runner_tokens = ("cargo",)

    def run_argv(self, runner: list[str], artifact: Path, root: Path) -> list[str]:
        """cargo waehlt Integrationstests ueber den Dateinamen, nicht ueber den Pfad."""
        if runner and Path(runner[0]).name == "cargo" and "--test" not in runner:
            return [*runner, "--test", artifact.stem]
        return list(runner)


class NodeLanguage(TestLanguage):
    name = "Node"
    suffixes = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")
    default_runner = ("npm", "test")
    runner_tokens = ("npm", "pnpm", "yarn", "npx", "vitest", "jest", "deno")

    def run_argv(self, runner: list[str], artifact: Path, root: Path) -> list[str]:
        pfad = str(self._relativ(artifact, root))
        if runner and Path(runner[0]).name in {"npm", "pnpm", "yarn"}:
            # Paketmanager reichen erst nach `--` an den Test-Runner durch.
            return [*runner, "--", pfad]
        return [*runner, pfad]


class GoLanguage(TestLanguage):
    name = "Go"
    suffixes = (".go",)
    default_runner = ("go", "test")
    runner_tokens = ("go",)

    def run_argv(self, runner: list[str], artifact: Path, root: Path) -> list[str]:
        """go test adressiert Pakete, also das Verzeichnis der Datei."""
        paket = self._relativ(artifact, root).parent.as_posix()
        return [*runner, f"./{paket}" if paket not in ("", ".") else "./..."]


PYTHON = PythonLanguage()
RUST = RustLanguage()
NODE = NodeLanguage()
GO = GoLanguage()

LANGUAGES: tuple[TestLanguage, ...] = (PYTHON, RUST, NODE, GO)


def language_for_path(path: str | Path) -> TestLanguage | None:
    """Sprachprofil zur Dateiendung, oder None fuer eine Endung ohne Profil."""
    suffix = Path(str(path)).suffix.lower()
    for lang in LANGUAGES:
        if suffix in lang.suffixes:
            return lang
    return None


def language_for_runner(command: str) -> TestLanguage | None:
    """Sprachprofil zum konfigurierten Testkommando.

    `uv run pytest` beginnt mit `uv`, meint aber Python. Deshalb zaehlt jedes Token,
    nicht nur das erste.
    """
    tokens = [Path(t).name for t in shlex.split(command or "")]
    for lang in LANGUAGES:
        if any(t in lang.runner_tokens for t in tokens):
            return lang
    return None


def suffixes_mit_generator() -> list[str]:
    """Endungen, fuer die sdd Ruempfe erzeugen kann — fuer Hinweistexte."""
    return [s for lang in LANGUAGES if lang.generates_stubs for s in lang.suffixes]


def bekannte_suffixe() -> list[str]:
    return [s for lang in LANGUAGES for s in lang.suffixes]
