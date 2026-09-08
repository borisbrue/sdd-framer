"""Jeder in der README gezeigte sdd-Aufruf muss es auch geben.

SPEC-0044 hat CLI-Gruppen entfernt und Befehle umbenannt; die README wurde nie
nachgezogen und dokumentierte 34 Nennungen von Befehlen, die es nicht mehr gibt.
Wer die README beim Einarbeiten als massgeblich nimmt, haelt geplante
Entfernungen fuer Defekte.

Der Test ist maschinell entscheidbar, weil die CLI ihre Befehlsliste selbst
kennt — und er haette die Drift beim Merge von SPEC-0044 sofort gezeigt.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tool"))

_README = Path(__file__).resolve().parents[2] / "README.md"


def _cli_commands() -> dict[str, object]:
    """Top-Level-Befehle der CLI, inklusive versteckter."""
    from sdd_cli.main import cli
    return dict(cli.commands)


def _readme_calls() -> list[tuple[int, str]]:
    """(Zeilennummer, Befehlsname) je sdd-Aufruf in einem ```bash-Block."""
    text = _README.read_text(encoding="utf-8")
    zeilen = text.splitlines()
    calls: list[tuple[int, str]] = []
    in_bash = False
    for nr, zeile in enumerate(zeilen, start=1):
        if zeile.startswith("```bash"):
            in_bash = True
            continue
        if zeile.startswith("```"):
            in_bash = False
            continue
        if not in_bash:
            continue
        blank = zeile.strip()
        if not blank.startswith("sdd "):
            continue
        # Optionen und Platzhalter ausklammern
        toks = [t for t in blank.split() if not t.startswith("-")]
        if len(toks) >= 2 and re.fullmatch(r"[a-z][a-z0-9-]*", toks[1]):
            calls.append((nr, toks[1]))
    return calls


class TestReadmeMatchesTheCli:
    def test_readme_contains_examples_at_all(self):
        """Absicherung gegen einen Test, der nichts prueft."""
        assert len(_readme_calls()) >= 20

    def test_every_command_exists(self):
        bekannt = _cli_commands()
        unbekannt = [(nr, c) for nr, c in _readme_calls() if c not in bekannt]
        assert not unbekannt, "\n".join(
            f"README.md:{nr}: `sdd {c}` existiert nicht" for nr, c in unbekannt
        )

    def test_no_removed_command_is_advertised(self):
        """`[Entfernt]`-Stubs bleiben aufrufbar, duerfen aber nicht als Weg
        gezeigt werden — sie enden mit exit 1 und verweisen weiter."""
        bekannt = _cli_commands()
        entfernt = [
            (nr, c) for nr, c in _readme_calls()
            if c in bekannt and (bekannt[c].help or "").startswith("[Entfernt]")
        ]
        assert not entfernt, "\n".join(
            f"README.md:{nr}: `sdd {c}` ist entfernt — {bekannt[c].help}"
            for nr, c in entfernt
        )


class TestMigrationNoteExists:
    """SPEC-0044 US-03: alte Workflows muessen auffindbar bleiben."""

    def test_readme_has_a_migration_section(self):
        text = _README.read_text(encoding="utf-8")
        assert "Migration: umbenannte und entfernte Befehle" in text

    @pytest.mark.parametrize("alt,neu", [
        ("sdd evaluate", "sdd holdout run"),
        ("sdd solid-check", "sdd spec solid"),
        ("sdd review-contract", "sdd review contract"),
        ("sdd review-pending", "sdd review pending"),
        ("sdd mark-false-positive", "sdd autonomy false-positive"),
        ("sdd regression-check", "sdd spec regression"),
    ])
    def test_renames_are_documented(self, alt, neu):
        text = _README.read_text(encoding="utf-8")
        assert f"`{alt}`" in text and f"`{neu}`" in text

    def test_removed_groups_are_named(self):
        text = _README.read_text(encoding="utf-8")
        for entfernt in ("sdd dev", "sdd pattern", "sdd status-check"):
            assert entfernt in text, f"{entfernt} fehlt in der Migrationsnotiz"
