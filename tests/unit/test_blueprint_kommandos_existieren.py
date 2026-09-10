"""Jeder sdd-Aufruf in den ausgelieferten Skill-Dateien muss es geben (#68).

Der Waechter aus #56 prueft die README. Die Skill-Dateien wiegen schwerer: sie
steuern, was der Agent tut, nicht nur was ein Mensch liest — und `sdd init`
kopiert sie in jedes neue Projekt. Nach SPEC-0044 verwiesen sie auf Befehle,
die es nicht mehr gibt.

Dieselbe Extraktion wie in test_readme_commands_exist.py, andere Dateiliste.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "tool"))

_SKILL_DIR = _ROOT / "tool" / "sdd_cli" / "blueprint" / "templates" / "agents-md"
_SETTINGS = _SKILL_DIR / "providers" / "claude" / "settings.json"

# `sdd <befehl>` am Wortanfang, auch in Prosa und in Backticks.
_AUFRUF_RE = re.compile(r"(?<![\w-])sdd\s+([a-z][a-z0-9-]*)")

# Woerter, die auf `sdd` folgen koennen, ohne ein Befehlsname zu sein.
_KEIN_BEFEHL = {
    "nicht", "erfolgreich", "installiert", "ist", "und", "oder", "im", "in",
    "auf", "mit", "vom", "wird", "kann", "hat", "der", "die", "das", "es",
    "selbst", "sonst", "dann", "noch", "nur", "auch", "als", "an", "aus",
}


def _cli_commands() -> dict[str, object]:
    from sdd_cli.main import cli
    return dict(cli.commands)


# Die repo-eigenen Skills unter .claude/commands/ sind eine zweite Kopie. #68
# hat nur das Blueprint geprueft; dort blieben `sdd dev exec` und dreimal
# `sdd regression-check` stehen (#90).
_REPO_SKILL_DIR = _ROOT / ".claude" / "commands"


def _skill_dateien() -> list[Path]:
    dateien = [p for p in _SKILL_DIR.rglob("*.md") if p.is_file()]
    if _REPO_SKILL_DIR.is_dir():
        dateien += [p for p in _REPO_SKILL_DIR.glob("*.md") if p.is_file()]
    return sorted(dateien)


# Ein Migrationshinweis MUSS den alten Namen nennen, sonst findet niemand den
# neuen ("`sdd evaluate` existiert seit … nicht mehr — Ersatz ist …"). Dieselbe
# Ausnahme wie fuer die Entfernt-Meldungen in main.py und die
# Migrationstabelle der README (#56). Die repo-eigenen Skills enthalten solche
# Hinweise, die richtige Anweisung steht jeweils daneben.
_FESTSTELLUNG_RE = re.compile(r"nicht mehr|entfallen|wurde entfernt|entfernt hatte")


def _aufrufe(text: str) -> list[tuple[int, str]]:
    """(Zeilennummer, Befehlsname) je sdd-Aufruf."""
    treffer: list[tuple[int, str]] = []
    for nr, zeile in enumerate(text.splitlines(), start=1):
        if _FESTSTELLUNG_RE.search(zeile):
            continue
        for m in _AUFRUF_RE.finditer(zeile):
            name = m.group(1)
            if name not in _KEIN_BEFEHL:
                treffer.append((nr, name))
    return treffer


def _alle_aufrufe() -> list[tuple[Path, int, str]]:
    ergebnis: list[tuple[Path, int, str]] = []
    for datei in _skill_dateien():
        for nr, name in _aufrufe(datei.read_text(encoding="utf-8")):
            ergebnis.append((datei, nr, name))
    return ergebnis


def _rel(p: Path) -> str:
    return str(p.relative_to(_ROOT))


def test_skills_enthalten_ueberhaupt_aufrufe():
    """Absicherung gegen einen Test, der nichts prueft."""
    assert len(_alle_aufrufe()) >= 40


def test_jeder_aufruf_existiert():
    bekannt = _cli_commands()
    unbekannt = [(d, nr, c) for d, nr, c in _alle_aufrufe() if c not in bekannt]
    assert not unbekannt, "\n".join(
        f"{_rel(d)}:{nr}: `sdd {c}` existiert nicht" for d, nr, c in unbekannt
    )


def test_kein_entfernter_befehl_wird_empfohlen():
    """`[Entfernt]`-Stubs bleiben aufrufbar, enden aber mit exit 1."""
    bekannt = _cli_commands()
    entfernt = [
        (d, nr, c) for d, nr, c in _alle_aufrufe()
        if c in bekannt and (getattr(bekannt[c], "help", "") or "").startswith("[Entfernt]")
    ]
    assert not entfernt, "\n".join(
        f"{_rel(d)}:{nr}: `sdd {c}` ist entfernt — {bekannt[c].help}"
        for d, nr, c in entfernt
    )


def test_settings_json_erlaubt_nur_existierende_befehle():
    """Eine Permission auf einen entfernten Befehl erlaubt nichts und
    verschleiert, welche Rechte das Projekt tatsaechlich vergibt."""
    bekannt = _cli_commands()
    settings = json.loads(_SETTINGS.read_text(encoding="utf-8"))
    erlaubt = settings.get("permissions", {}).get("allow", [])

    fehlend = []
    for eintrag in erlaubt:
        m = re.fullmatch(r"Bash\(sdd\s+([a-z][a-z0-9-]*)[^)]*\)", eintrag)
        if not m:
            continue
        name = m.group(1)
        if name not in bekannt:
            fehlend.append((eintrag, "existiert nicht"))
        elif (getattr(bekannt[name], "help", "") or "").startswith("[Entfernt]"):
            fehlend.append((eintrag, bekannt[name].help))
    assert not fehlend, "\n".join(
        f"{_rel(_SETTINGS)}: {e} — {grund}" for e, grund in fehlend
    )


@pytest.mark.parametrize("weg", ["pattern", "dev"])
def test_entfernte_gruppen_kommen_nicht_vor(weg):
    """`sdd pattern` und `sdd dev` sind mit SPEC-0044 ersatzlos entfallen."""
    treffer = [
        f"{_rel(d)}:{nr}" for d, nr, c in _alle_aufrufe() if c == weg
    ]
    assert not treffer, f"`sdd {weg}` noch genannt in: " + ", ".join(treffer)


# ── Laufzeitausgaben ─────────────────────────────────────────────────────────
#
# Der Hinweis nach `sdd review spec` nannte `sdd pattern accept` — einen Befehl,
# den SPEC-0044 entfernt hat. Was die CLI dem Nutzer als naechsten Schritt
# anbietet, muss existieren; sonst fuehrt die Ausgabe ins Leere.

_MAIN = _ROOT / "tool" / "sdd_cli" / "main.py"

# `sdd <befehl>` innerhalb eines String-Literals in main.py.
_HINWEIS_RE = re.compile(r"""["'][^"']*?(?<![\w-])sdd\s+([a-z][a-z0-9-]*)""")


def _hinweise() -> list[tuple[int, str]]:
    treffer: list[tuple[int, str]] = []
    for nr, zeile in enumerate(_MAIN.read_text(encoding="utf-8").splitlines(), start=1):
        # Nur Ausgabezeilen, nicht Kommentare oder Docstring-Prosa.
        if "console.print" not in zeile and "echo" not in zeile:
            continue
        # Eine Entfernt-Meldung MUSS den alten Namen nennen — sonst findet
        # niemand den Weg zum neuen. Dieselbe Ausnahme wie fuer die
        # Migrationstabelle der README (#56).
        if "wurde entfernt" in zeile or "[Entfernt]" in zeile:
            continue
        for m in _HINWEIS_RE.finditer(zeile):
            name = m.group(1)
            if name not in _KEIN_BEFEHL:
                treffer.append((nr, name))
    return treffer


def test_laufzeithinweise_nennen_existierende_befehle():
    bekannt = _cli_commands()
    unbekannt = [(nr, c) for nr, c in _hinweise() if c not in bekannt]
    assert not unbekannt, "\n".join(
        f"tool/sdd_cli/main.py:{nr}: Ausgabe verweist auf `sdd {c}` — existiert nicht"
        for nr, c in unbekannt
    )


def test_laufzeithinweise_empfehlen_keinen_entfernten_befehl():
    bekannt = _cli_commands()
    entfernt = [
        (nr, c) for nr, c in _hinweise()
        if c in bekannt and (getattr(bekannt[c], "help", "") or "").startswith("[Entfernt]")
    ]
    assert not entfernt, "\n".join(
        f"tool/sdd_cli/main.py:{nr}: Ausgabe verweist auf `sdd {c}` — {bekannt[c].help}"
        for nr, c in entfernt
    )
