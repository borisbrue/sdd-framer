"""Es gibt genau eine Web-API, und die Tests pruefen sie (#107).

Bis #107 lag die API zweimal im Repo: `tool/sdd_cli/web/api/` (die der Server
laedt) und `web/api/` im Root (die die Tests importierten). Zehn Dateien wichen
ab. Wer nur eine Kopie aenderte, bekam entweder einen ungetesteten Fix oder
einen getesteten, der nie lief — bei #103 fiel es auf.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_PAKET_API = _ROOT / "tool" / "sdd_cli" / "web" / "api"


def test_die_root_kopie_gibt_es_nicht_mehr():
    """Geprueft wird Quellcode, nicht das Verzeichnis: in jeder aelteren
    Arbeitskopie bleiben ungetrackte __pycache__-Reste nach dem Pull liegen, und
    ein exists() schlaege dort grundlos an."""
    reste = [
        str(p.relative_to(_ROOT))
        for p in (_ROOT / "web" / "api").rglob("*.py")
    ] if (_ROOT / "web" / "api").is_dir() else []
    assert not reste, (
        "Quellcode unter web/api/ — die zweite Kopie der Web-API ist wieder da (#107): "
        + ", ".join(reste[:5])
    )


def test_der_server_laedt_die_paket_kopie():
    """Worauf die Tests zeigen, muss das sein, was ui.py startet."""
    from sdd_cli.ui import _web_root

    assert (_web_root() / "api").resolve() == _PAKET_API.resolve()


def test_conftest_zeigt_auf_die_paket_kopie():
    """Geprueft wird die Wirkung von tests/conftest.py, nicht die Datei: pytest
    laedt sie unter einem eigenen Modulnamen, `import conftest` findet sie nicht."""
    pfade = {Path(p).resolve() for p in sys.path if p}
    assert _PAKET_API.resolve() in pfade
    assert (_ROOT / "web" / "api").resolve() not in pfade


def test_die_importierten_module_stammen_aus_dem_paket():
    """sys.modules behaelt die zuerst geladene Kopie — hier wird geprueft,
    welche es tatsaechlich ist."""
    import routes.auth
    import sdd_context

    for modul in (routes.auth, sdd_context):
        pfad = Path(modul.__file__).resolve()
        assert _PAKET_API.resolve() in pfad.parents, f"{modul.__name__} kommt aus {pfad}"


def test_kein_test_haengt_einen_anderen_api_pfad_an():
    """14 Testdateien hingen REPO_ROOT / "web" / "api" selbst an sys.path[0]."""
    falsch = []
    muster = re.compile(r'/ "web" / "api"')
    selbst = Path(__file__).resolve()
    for p in sorted((_ROOT / "tests").rglob("*.py")):
        if p.resolve() == selbst:
            continue  # dieser Test nennt das Muster zwangslaeufig selbst
        for nr, zeile in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if muster.search(zeile) and '"tool" / "sdd_cli" / "web" / "api"' not in zeile:
                falsch.append(f"{p.relative_to(_ROOT)}:{nr}")
    assert not falsch, "Pfad auf die entfernte Kopie: " + ", ".join(falsch)


class TestSpecsLiefertAdrs:
    """Der einzige Inhalt, den nur die Root-Kopie noch hatte (#107).

    Ging in 744b756 verloren; das UI deklariert das Feld weiter
    (web/ui/src/api.ts: `adrs: string[]`).
    """

    def test_feld_ist_im_ausgelieferten_endpunkt(self):
        quelle = (_PAKET_API / "routes" / "specs.py").read_text(encoding="utf-8")
        assert '"adrs": fm.get("adrs") or []' in quelle

    def test_ui_erwartet_das_feld(self):
        api_ts = _ROOT / "web" / "ui" / "src" / "api.ts"
        assert "adrs: string[]" in api_ts.read_text(encoding="utf-8")
