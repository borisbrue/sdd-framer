"""Erzeugte Testdateien tragen importierbare Modulnamen (#101).

#79 hat den Generator umgestellt: `test_con-0014.py` -> `test_con_0014.py`.
CON-0028 definiert `{con_id_lower}` seither mit Unterstrich. Sechs bestehende
Dateien trugen den alten Namen weiter — pytest sammelt sie ueber den Pfad ein,
aber kein Modul kann aus ihnen importieren.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

_ROOT = Path(__file__).resolve().parents[2]


def _testdateien() -> list[Path]:
    return sorted(p for p in (_ROOT / "tests").rglob("test_*.py"))


def test_es_gibt_ueberhaupt_testdateien():
    """Absicherung gegen einen Test, der nichts prueft."""
    assert len(_testdateien()) >= 50


def test_jeder_modulname_ist_ein_gueltiger_bezeichner():
    ungueltig = [
        str(p.relative_to(_ROOT)) for p in _testdateien() if not p.stem.isidentifier()
    ]
    assert not ungueltig, (
        "nicht importierbare Modulnamen: " + ", ".join(ungueltig)
    )


def test_kein_tst_dokument_zeigt_auf_einen_bindestrich_namen():
    """Das `artifact:`-Feld erzeugt die Datei — dort faengt der Name an."""
    falsch = []
    for md in sorted((_ROOT / "tests").rglob("TST-*.md")) + sorted(
        (_ROOT / ".sdd" / "tests").rglob("TST-*.md")
    ):
        m = re.match(r"^---\n(.*?)\n---", md.read_text(encoding="utf-8"), re.DOTALL)
        if not m:
            continue
        fm = yaml.safe_load(m.group(1)) or {}
        if not isinstance(fm, dict):
            continue
        artefakt = str(fm.get("artifact") or "").strip().strip('"')
        if artefakt.endswith(".py") and not Path(artefakt).stem.isidentifier():
            falsch.append(f"{md.name} -> {artefakt}")
    assert not falsch, "TST-Dokumente mit nicht importierbarem Ziel: " + "; ".join(falsch)


class TestDasProtokollBleibtStehen:
    """Die bewusste Ausnahme aus #101 — festgehalten, damit sie niemand
    stillschweigend 'repariert'.

    `.sdd/pipeline/SPEC-0014-gate.json` haelt fest, welche Dateien der Lauf
    **damals** erzeugt hat. Ein Protokoll, das man an die Gegenwart anpasst, ist
    kein Protokoll mehr. Der Eintrag weicht deshalb absichtlich vom
    Dateisystem ab.
    """

    GATE = _ROOT / ".sdd" / "pipeline" / "SPEC-0014-gate.json"

    def _erzeugte_dateien(self) -> list[str]:
        daten = json.loads(self.GATE.read_text(encoding="utf-8"))
        for eintrag in daten.get("phase_history", []):
            if eintrag.get("phase") == "tests-generated":
                return list(eintrag.get("files_generated") or [])
        return []

    def test_gate_nennt_weiter_die_damaligen_namen(self):
        namen = self._erzeugte_dateien()
        assert namen, "kein tests-generated-Eintrag im Gate gefunden"
        assert all("test_con-" in n for n in namen), (
            "Das Gate-Protokoll wurde nachtraeglich umgeschrieben. Es haelt fest, "
            "was der Lauf damals erzeugt hat — siehe #101."
        )

    def test_die_dateien_von_damals_gibt_es_unter_dem_neuen_namen(self):
        """Die Abweichung ist eine Umbenennung, kein Verlust."""
        for alt in self._erzeugte_dateien():
            neu = _ROOT / alt.replace("test_con-", "test_con_")
            assert neu.exists(), f"{alt} hat keine Entsprechung: {neu}"
