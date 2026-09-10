"""Das ausgelieferte Blueprint enthaelt keine Geheimnisse (#69).

`sdd init` kopiert `blueprint/config.yaml` woertlich in jedes neue Projekt und
`.sdd/config.yaml` ist versioniert. Ein Literal an dieser Stelle ist damit
dasselbe Geheimnis in allen erzeugten Projekten — und in deren Historie.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

BLUEPRINT = Path(__file__).resolve().parents[2] / "tool" / "sdd_cli" / "blueprint"
CONFIG = BLUEPRINT / "config.yaml"

# Schluessel, deren Wert im Blueprint leer sein muss.
_GEHEIM_SCHLUESSEL = re.compile(r"token|secret|password|passwd|private_key|api_key", re.I)

# Ein Wert, der nach Zufall aussieht: >=24 Zeichen, reines Hex oder Base64.
_ENTROPIE = re.compile(r"^(?:[0-9a-fA-F]{24,}|[A-Za-z0-9+/_-]{32,}={0,2})$")


def _paare(knoten, pfad=""):
    """Alle (Pfad, Wert)-Paare des YAML-Baums."""
    if isinstance(knoten, dict):
        for k, v in knoten.items():
            yield from _paare(v, f"{pfad}.{k}" if pfad else str(k))
    elif isinstance(knoten, list):
        for i, v in enumerate(knoten):
            yield from _paare(v, f"{pfad}[{i}]")
    else:
        yield pfad, knoten


@pytest.fixture(scope="module")
def config_baum():
    return yaml.safe_load(CONFIG.read_text(encoding="utf-8")) or {}


def test_geheime_schluessel_sind_leer(config_baum):
    """Kein Schluessel mit geheimnisverdaechtigem Namen traegt einen Wert."""
    belegt = [
        (pfad, wert)
        for pfad, wert in _paare(config_baum)
        if _GEHEIM_SCHLUESSEL.search(pfad.rsplit(".", 1)[-1]) and wert not in ("", None)
    ]
    assert not belegt, (
        "Blueprint-Konfiguration enthaelt belegte Geheimnisfelder: "
        + ", ".join(f"{p} = {str(w)[:12]}…" for p, w in belegt)
    )


def test_keine_zufallswerte_im_blueprint(config_baum):
    """Kein Wert sieht aus wie ein erzeugtes Geheimnis, unabhaengig vom Namen."""
    verdaechtig = [
        (pfad, wert)
        for pfad, wert in _paare(config_baum)
        if isinstance(wert, str) and _ENTROPIE.match(wert)
    ]
    assert not verdaechtig, (
        "Werte mit Geheimnis-Charakteristik im Blueprint: "
        + ", ".join(f"{p} = {w[:12]}…" for p, w in verdaechtig)
    )


def test_pwa_token_ist_leer(config_baum):
    """Der konkrete Befund aus #69: pwa.auth.token war fest verdrahtet.

    Der Schluessel bleibt im Blueprint stehen — er dokumentiert die Stelle —
    aber ohne Wert. Den ersten Token erzeugt POST /api/auth/generate-token.
    """
    assert config_baum.get("pwa", {}).get("auth", {}).get("token", "") == ""


def test_init_erzeugt_projekt_ohne_token(tmp_path):
    """Ein frisch initialisiertes Projekt traegt keinen Token."""
    from sdd_cli.init import init_project

    init_project(tmp_path, title="Testprojekt")
    erzeugt = yaml.safe_load(
        (tmp_path / ".sdd" / "config.yaml").read_text(encoding="utf-8")
    )
    assert erzeugt.get("pwa", {}).get("auth", {}).get("token", "") == ""


def test_zwei_projekte_teilen_kein_geheimnis(tmp_path):
    """Der eigentliche Schaden aus #69: zwei Projekte mit demselben Schluessel.

    Sobald `sdd init` einen Token erzeugen wuerde, muessten sich beide
    unterscheiden. Solange er leer bleibt, ist die Bedingung trivial erfuellt —
    der Test faellt aber, sobald jemand wieder einen festen Wert einsetzt.
    """
    from sdd_cli.init import init_project

    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir()
    b.mkdir()
    init_project(a, title="A")
    init_project(b, title="B")

    def token(p: Path) -> str:
        raw = yaml.safe_load((p / ".sdd" / "config.yaml").read_text(encoding="utf-8"))
        return raw.get("pwa", {}).get("auth", {}).get("token", "")

    tok_a, tok_b = token(a), token(b)
    assert not (tok_a and tok_a == tok_b), (
        f"Beide Projekte tragen denselben Token: {tok_a[:12]}…"
    )
