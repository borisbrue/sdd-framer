"""Was die Blueprint-Konfiguration nennt, muss `sdd init` auch anlegen (#73).

Dreimal derselbe Fehler: #16 (AGENTS.md), #55 (GitHub-Workflow), #73
(Dockerfile). Die Konfiguration verwies auf eine Datei, die nie ausgeliefert
wurde, und es fiel erst auf, wenn ein Befehl sie brauchte — beim Dockerfile
also erst beim ersten Container-Schritt.

Der Test macht die Regel maschinell pruefbar: jeder Pfad unterhalb von `.sdd/`,
den die Blueprint-Konfiguration nennt, existiert im frisch erzeugten Projekt.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

_ROOT = Path(__file__).resolve().parents[2]
_BLUEPRINT = _ROOT / "tool" / "sdd_cli" / "blueprint"

# Ein Wert, der wie ein Pfad ins Projekt aussieht.
_PFAD_RE = re.compile(r"^\.sdd/[\w./-]+$")


def _werte(knoten, pfad=""):
    if isinstance(knoten, dict):
        for k, v in knoten.items():
            yield from _werte(v, f"{pfad}.{k}" if pfad else str(k))
    elif isinstance(knoten, list):
        for i, v in enumerate(knoten):
            yield from _werte(v, f"{pfad}[{i}]")
    else:
        yield pfad, knoten


def _genannte_pfade() -> list[tuple[str, str]]:
    baum = yaml.safe_load((_BLUEPRINT / "config.yaml").read_text(encoding="utf-8")) or {}
    return [
        (schluessel, wert)
        for schluessel, wert in _werte(baum)
        if isinstance(wert, str) and _PFAD_RE.match(wert)
    ]


@pytest.fixture(scope="module")
def projekt(tmp_path_factory):
    from sdd_cli.init import init_project

    ziel = tmp_path_factory.mktemp("projekt")
    init_project(ziel, title="Testprojekt")
    return ziel


def test_die_konfiguration_nennt_ueberhaupt_pfade():
    """Absicherung gegen einen Test, der nichts prueft."""
    assert _genannte_pfade(), "kein .sdd/-Pfad in der Blueprint-Konfiguration"


def test_jede_genannte_datei_existiert(projekt):
    fehlend = [
        f"{schluessel}: {wert}"
        for schluessel, wert in _genannte_pfade()
        if not (projekt / wert).exists()
    ]
    assert not fehlend, (
        "config.yaml nennt Dateien, die sdd init nicht anlegt: " + ", ".join(fehlend)
    )


class TestDevContainer:
    """Der konkrete Befund: Dockerfile und der von ihm eingebundene entrypoint."""

    def test_dockerfile_wird_ausgeliefert(self, projekt):
        assert (projekt / ".sdd" / "Dockerfile").exists()

    def test_entrypoint_wird_mitgeliefert(self, projekt):
        """Ohne ihn scheitert das COPY im Dockerfile."""
        assert (projekt / ".sdd" / "entrypoint.sh").exists()

    def test_entrypoint_ist_ausfuehrbar(self, projekt):
        assert (projekt / ".sdd" / "entrypoint.sh").stat().st_mode & 0o111

    def test_copy_pfade_sind_relativ_zur_projektwurzel(self, projekt):
        """Gebaut wird mit `build -f .sdd/Dockerfile .`, der Kontext ist also
        die Projektwurzel. `COPY entrypoint.sh` suchte dort — und brach ab."""
        text = (projekt / ".sdd" / "Dockerfile").read_text(encoding="utf-8")
        for zeile in text.splitlines():
            if not zeile.startswith("COPY "):
                continue
            quelle = zeile.split()[1]
            assert (projekt / quelle).exists(), (
                f"COPY {quelle}: im Build-Kontext (Projektwurzel) nicht vorhanden"
            )

    def test_venv_ziel_passt_zum_aufrufer(self, projekt):
        """dev_container.py mountet ein leeres Volume ueber /workspace/.venv und
        setzt UV_PROJECT_ENVIRONMENT (#60). Das Image muss denselben Ort meinen."""
        from sdd_cli.dev_container import CONTAINER_VENV

        text = (projekt / ".sdd" / "Dockerfile").read_text(encoding="utf-8")
        assert f"UV_PROJECT_ENVIRONMENT={CONTAINER_VENV}" in text


class TestEigenesRepo:
    """Der Dockerfile dieses Repos hatte denselben Fehler und baute nie durch."""

    def test_eigener_dockerfile_kopiert_aus_der_wurzel(self):
        text = (_ROOT / ".sdd" / "Dockerfile").read_text(encoding="utf-8")
        for zeile in text.splitlines():
            if zeile.startswith("COPY "):
                quelle = zeile.split()[1]
                assert (_ROOT / quelle).exists(), f"COPY {quelle} zeigt ins Leere"
