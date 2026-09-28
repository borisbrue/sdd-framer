"""`sdd stack verify` und `sdd stack diff` (SPEC-0057 FR-05, FR-06, CON-0228 INV-03/INV-04).

`verify` führt nur Deklariertes aus: `version_command` aus `requires`, die Sonden aus
`.sdd/quality.yaml` (über den Doctor, der die Test-Sonde einmal laufen lässt), `sdd arch check`
und die `verify`-Einträge der Vorlagen.
"""
from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from . import Stack, StackError, applied, find, sha

VERSION = re.compile(r"(\d+)\.(\d+)(?:\.(\d+))?")
TIMEOUT = 600


@dataclass
class Check:
    name: str
    ok: bool
    required: bool
    message: str

    @property
    def failed(self) -> bool:
        return self.required and not self.ok


def _version(text: str) -> tuple[int, ...] | None:
    treffer = VERSION.search(text)
    return tuple(int(t or 0) for t in treffer.groups()) if treffer else None


def _run(command: str, root: Path) -> tuple[int, str]:
    try:
        proc = subprocess.run(command, shell=True, cwd=root, capture_output=True, text=True,
                              timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return 124, "Zeitlimit überschritten"
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def check_requires(stack: Stack, root: Path) -> list[Check]:
    ergebnis = []
    for req in stack.data.get("requires") or []:
        pflicht = not req.get("optional", False)
        hinweis = f" – installieren: {req['install_hint']}" if req.get("install_hint") else ""
        code, ausgabe = _run(req["version_command"], root)
        name = f"Werkzeug {req['tool']}"
        if code != 0:
            ergebnis.append(Check(name, False, pflicht, f"fehlt{hinweis}"))
            continue
        gefunden = _version(ausgabe)
        if req.get("min") and (gefunden is None or gefunden < (_version(req["min"]) or ())):
            ergebnis.append(Check(name, False, pflicht,
                                  f"Version {ausgabe.splitlines()[0] if ausgabe else '?'} "
                                  f"< {req['min']}{hinweis}"))
            continue
        ergebnis.append(Check(name, True, pflicht, ausgabe.splitlines()[0] if ausgabe else "ok"))
    return ergebnis


def missing_tools(stack: Stack) -> list[str]:
    """Warnung beim Anwenden (CON-0229 INV-04): Pflichtwerkzeuge, deren Programm nicht im PATH
    liegt. Es wird kein Befehl der Vorlage ausgeführt, nur das erste Wort nachgeschlagen."""
    fehlend = []
    for req in stack.data.get("requires") or []:
        try:
            programm = shlex.split(req["version_command"])[0]
        except (ValueError, IndexError):
            continue
        if not req.get("optional", False) and shutil.which(programm) is None:
            hinweis = f" – installieren: {req['install_hint']}" if req.get("install_hint") else ""
            fehlend.append(f"{req['tool']}{hinweis}")
    return fehlend


def check_quality(root: Path) -> list[Check]:
    from ..quality.config import QualityConfigError
    from ..quality.doctor import run_doctor
    from ..quality.probe import REASON_NOT_FOUND

    try:
        eintraege = run_doctor(root)
    except FileNotFoundError:
        return [Check("quality doctor", False, True, ".sdd/quality.yaml fehlt")]
    except QualityConfigError as exc:
        return [Check("quality doctor", False, True, "; ".join(map(str, exc.problems[:3])))]
    ergebnis = []
    for e in eintraege:
        # Fehlt das Werkzeug einer Sonde, entscheidet `requires` über Pflicht oder Warnung.
        pflicht = not (not e.ready and e.messages[:1] == [REASON_NOT_FOUND])
        ergebnis.append(Check(f"Sonde {e.probe}", e.ready, pflicht, "; ".join(e.messages)))
        if "FR-Markierung erkannt" in e.messages:
            ergebnis.append(Check("FR-markierter Test", True, True,
                                  f"Test-Sonde {e.probe} meldet FR-Marker"))
    if not any(c.name == "FR-markierter Test" for c in ergebnis):
        ergebnis.append(Check("FR-markierter Test", False, True,
                              "die Test-Sonde meldet keinen Test mit FR-Marker "
                              "(Konvention siehe AGENTS.md-Abschnitt der Vorlage)"))
    return ergebnis


def check_arch(root: Path) -> Check:
    if not (root / ".sdd" / "architecture.yaml").is_file():
        return Check("arch check", True, False, "keine .sdd/architecture.yaml – übersprungen")
    # Dieselbe sdd-Installation wie der Aufrufer, unabhängig von PATH und relativem PYTHONPATH.
    paket = str(Path(__file__).resolve().parents[2])
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(
        [paket, *filter(None, [os.environ.get("PYTHONPATH")])])}
    proc = subprocess.run([sys.executable, "-m", "sdd_cli.main", "arch", "check"], cwd=root,
                          capture_output=True, text=True, timeout=TIMEOUT, env=env)
    if proc.returncode == 0:
        return Check("arch check", True, True, "ohne Verstöße")
    if proc.returncode == 1:
        return Check("arch check", True, True, "läuft, meldet Verstöße")
    zeilen = (proc.stdout + proc.stderr).strip().splitlines()
    return Check("arch check", False, True, zeilen[-1] if zeilen else f"Exit {proc.returncode}")


def check_entries(stack: Stack, root: Path, values: dict[str, str]) -> list[Check]:
    from .apply import render

    ergebnis = []
    for eintrag in stack.data.get("verify") or []:
        try:
            befehl = render(eintrag["command"], values)
        except KeyError as exc:
            ergebnis.append(Check(f"{stack.name}: {eintrag['name']}", False, True,
                                  f"Platzhalter {exc} ohne Wert im stack-Eintrag"))
            continue
        code, ausgabe = _run(befehl, root)
        letzte = ausgabe.splitlines()[-1] if ausgabe else ""
        ergebnis.append(Check(f"{stack.name}: {eintrag['name']}", code == 0,
                              not eintrag.get("optional", False),
                              "ok" if code == 0 else f"Exit {code} {letzte}".strip()))
    return ergebnis


def verify(root: Path, config_raw: dict) -> list[Check]:
    eintraege = applied(config_raw)
    if not eintraege:
        raise StackError("Keine Vorlage angewendet (stack: in config.yaml fehlt).")
    checks: list[Check] = []
    for eintrag in eintraege:
        try:
            stack = find(root, eintrag["name"])
        except StackError as exc:
            checks.append(Check(f"Vorlage {eintrag['name']}", False, True, str(exc)))
            continue
        checks += check_requires(stack, root)
    checks += check_quality(root)
    checks.append(check_arch(root))
    for eintrag in eintraege:
        try:
            checks += check_entries(find(root, eintrag["name"]), root,
                                    dict(eintrag.get("values") or {}))
        except StackError:
            continue
    return checks


# ── diff (FR-06) ─────────────────────────────────────────────────────────────

UNCHANGED = "unverändert"
PROJECT = "vom Projekt geändert"
TEMPLATE = "in der Vorlage neu oder geändert"
BOTH = "beides"
REMOVED = "im Projekt entfernt"


def diff(root: Path, config_raw: dict, name: str | None = None) -> dict[str, dict[str, str]]:
    """Je angewendeter Vorlage: Datei → Einordnung (Memento vs. Projekt vs. Vorlage)."""
    from .apply import plan

    ergebnis: dict[str, dict[str, str]] = {}
    eintraege = [e for e in applied(config_raw) if name is None or e["name"] == name]
    if name is not None and not eintraege:
        raise StackError(f"Vorlage {name!r} ist nicht angewendet.")
    for eintrag in eintraege:
        stack = find(root, eintrag["name"])
        vorlage = plan(stack, dict(eintrag.get("values") or {})).files
        memento = eintrag.get("files") or {}
        zeilen: dict[str, str] = {}
        for rel in sorted(set(memento) | set(vorlage)):
            datei = root / rel
            projekt = sha(datei.read_text(encoding="utf-8")) if datei.is_file() else None
            angewendet = memento.get(rel)
            neu = sha(vorlage[rel]) if rel in vorlage else None
            if projekt is None and angewendet is not None:
                zeilen[rel] = REMOVED
                continue
            vom_projekt = angewendet is not None and projekt != angewendet
            in_vorlage = neu is not None and neu != angewendet and neu != projekt
            if angewendet is None and projekt is None:
                in_vorlage = True
            zeilen[rel] = (BOTH if vom_projekt and in_vorlage else PROJECT if vom_projekt
                           else TEMPLATE if in_vorlage else UNCHANGED)
        ergebnis[stack.name] = zeilen
    return ergebnis
