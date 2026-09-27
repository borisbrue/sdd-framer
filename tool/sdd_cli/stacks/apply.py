"""`sdd stack apply` und `sdd stack extract` (SPEC-0057 FR-03, FR-04, FR-07, CON-0229).

Anwenden schreibt neue Dateien, lässt gleiche unberührt und legt für abweichende `<datei>.new` an.
AGENTS.md-Abschnitte stehen zwischen Markierungen. Das Memento in `config.yaml` (`stack:`) hält
Version, Quelle, Platzhalterwerte und je Datei den Hash des angewendeten Inhalts.
"""
from __future__ import annotations

import difflib
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from ..quality.presets import InstallResult, write_or_propose
from . import PLACEHOLDER, QUALITY_ONLY, Stack, StackError, applied, errors, load, sha

AGENTS = "AGENTS.md"


def begin(stack: str, abschnitt: str) -> str:
    return f"<!-- sdd-stack:{stack}:{abschnitt} -->"


def end(stack: str, abschnitt: str) -> str:
    return f"<!-- /sdd-stack:{stack}:{abschnitt} -->"


def render(text: str, values: dict[str, str]) -> str:
    return PLACEHOLDER.sub(lambda m: values[m.group(1)], text)


def resolve_values(stack: Stack, *, given: dict[str, str], stored: dict[str, str],
                   title: str, ask=None) -> dict[str, str]:
    """`--set` vor gespeicherten Werten vor Default; `project_name` ist der Projekttitel."""
    werte: dict[str, str] = {}
    for name, spec in stack.placeholders().items():
        wert = given.get(name, stored.get(name, spec.get("default")))
        if wert is None and name == "project_name":
            wert = title
        if wert is None and ask is not None:
            wert = ask(name, spec.get("description", ""))
        if wert is None:
            raise StackError(f"Platzhalter {name!r} ohne Wert (--set {name}=…).")
        werte[name] = str(wert)
    return werte


@dataclass
class Plan:
    stack: Stack
    values: dict[str, str]
    files: dict[str, str]  # Projektpfad → Inhalt
    sections: dict[str, str] = field(default_factory=dict)  # Abschnitt → Inhalt

    def preview(self, root: Path) -> str:
        zeilen = []
        for rel, inhalt in self.files.items():
            ziel = root / rel
            if not ziel.exists():
                zeilen.append(f"+ {rel}")
            elif ziel.read_text(encoding="utf-8") == inhalt:
                zeilen.append(f"= {rel}")
            else:
                zeilen.append(f"! {rel} (weicht ab → {rel}.new)")
                zeilen += difflib.unified_diff(
                    ziel.read_text(encoding="utf-8").splitlines(), inhalt.splitlines(),
                    rel, f"{rel}.new", lineterm="")
        zeilen += [f"~ {AGENTS}: Abschnitt {s}" for s in self.sections]
        return "\n".join(zeilen)


def plan(stack: Stack, values: dict[str, str], *, only_quality: bool = False) -> Plan:
    dateien = {}
    for quelle in stack.files():
        rel = render(quelle.relative_to(stack.files_dir).as_posix(), values)
        if only_quality and not rel.startswith(QUALITY_ONLY):
            continue
        dateien[rel] = render(quelle.read_text(encoding="utf-8"), values)
    abschnitte = {} if only_quality else {
        p.stem: render(p.read_text(encoding="utf-8"), values).rstrip("\n")
        for p in stack.agents_sections()}
    return Plan(stack, values, dateien, abschnitte)


def merge_agents(text: str, stack: str, abschnitte: dict[str, str]) -> str:
    """Ersetzt vorhandene markierte Abschnitte, hängt neue an; der Rest bleibt byte-gleich."""
    for name, inhalt in abschnitte.items():
        block = f"{begin(stack, name)}\n{inhalt}\n{end(stack, name)}"
        muster = re.compile(re.escape(begin(stack, name)) + r".*?" + re.escape(end(stack, name)),
                            re.DOTALL)
        if muster.search(text):
            text = muster.sub(lambda _m, b=block: b, text, count=1)
        else:
            text = (text.rstrip("\n") + "\n\n" if text.strip() else "") + block + "\n"
    return text


def write(root: Path, p: Plan) -> InstallResult:
    ergebnis = InstallResult()
    for rel, inhalt in p.files.items():
        write_or_propose(root, rel, inhalt, ergebnis)
    if p.sections:
        agents = root / AGENTS
        alt = agents.read_text(encoding="utf-8") if agents.is_file() else ""
        neu = merge_agents(alt, p.stack.name, p.sections)
        if neu != alt:
            agents.write_text(neu, encoding="utf-8")
            ergebnis.written.append(AGENTS)
    _memento(root, p)
    return ergebnis


def _memento(root: Path, p: Plan) -> None:
    """`stack:` in config.yaml fortschreiben (zeilenbasiert, Kommentare bleiben)."""
    pfad = root / ".sdd" / "config.yaml"
    text = pfad.read_text(encoding="utf-8")
    daten = yaml.safe_load(text) or {}
    alt = {e["name"]: e for e in applied(daten)}
    vorher = alt.get(p.stack.name, {})
    dateien = dict(vorher.get("files") or {}) if p.files and set(p.files) < set(
        vorher.get("files") or {}) else {}
    for rel, inhalt in p.files.items():
        if (root / rel).is_file() and (root / rel).read_text(encoding="utf-8") == inhalt:
            dateien[rel] = sha(inhalt)
        else:
            dateien[rel] = vorher.get("files", {}).get(rel) or sha(inhalt)
    eintrag = {"name": p.stack.name, "version": p.stack.version, "source": p.stack.source,
               "values": p.values, "files": dict(sorted(dateien.items()))}
    alt[p.stack.name] = eintrag
    liste = list(alt.values())
    fehler = [f for e in liste for f in errors("entry", e)]
    if fehler:
        raise StackError(f"stack-Eintrag verletzt CON-0227: {fehler[0]}")
    zeilen = text.splitlines(keepends=True)
    block = yaml.safe_dump({"stack": liste}, sort_keys=False, allow_unicode=True)
    start = next((i for i, z in enumerate(zeilen) if z.startswith("stack:")), None)
    if start is None:
        neu = text.rstrip("\n") + "\n" + block
    else:
        ende = start + 1
        while ende < len(zeilen) and (not zeilen[ende].strip() or zeilen[ende][:1] in " -#"):
            ende += 1
        neu = "".join(zeilen[:start]) + block + "".join(zeilen[ende:])
    pfad.write_text(neu, encoding="utf-8")


# ── extract (FR-07) ──────────────────────────────────────────────────────────

EXTRACT_FILES = (".sdd/quality.yaml", ".sdd/architecture.yaml", ".sdd/Dockerfile")
EXTRACT_DIRS = (".sdd/quality", "docs/adr")


def extract(root: Path, name: str, ziel_basis: Path, *, title: str,
            config_raw: dict) -> Stack:
    ziel = ziel_basis / name
    if ziel.exists():
        raise StackError(f"Vorlage {ziel} existiert bereits.")
    dateien: set[str] = {f for f in EXTRACT_FILES if (root / f).is_file()}
    for ordner in EXTRACT_DIRS:
        if (root / ordner).is_dir():
            dateien |= {p.relative_to(root).as_posix() for p in (root / ordner).rglob("*")
                        if p.is_file() and "__pycache__" not in p.parts
                        and not p.name.endswith(".new")}
    werte: dict[str, str] = {}
    for eintrag in applied(config_raw):
        dateien |= {f for f in eintrag.get("files", {}) if (root / f).is_file()}
        werte.update(eintrag.get("values") or {})
    ersetzungen = {"project_name": werte.get("project_name") or title}
    if werte.get("package_name"):
        ersetzungen["package_name"] = werte["package_name"]

    def generalisieren(text: str) -> str:
        for platzhalter, wert in sorted(ersetzungen.items(), key=lambda kv: -len(kv[1])):
            if wert:
                text = re.sub(rf"(?<![\w-]){re.escape(wert)}(?![\w-])",
                              "{{" + platzhalter + "}}", text)
        return text

    try:
        for rel in sorted(dateien):
            quelle = root / rel
            text = quelle.read_text(encoding="utf-8")
            datei = ziel / "files" / generalisieren(rel)
            datei.parent.mkdir(parents=True, exist_ok=True)
            datei.write_text(generalisieren(text), encoding="utf-8")
        agents = root / AGENTS
        if agents.is_file():
            muster = re.compile(r"<!-- sdd-stack:([a-z0-9-]+):([A-Za-z0-9_-]+) -->\n(.*?)\n"
                                r"<!-- /sdd-stack:\1:\2 -->", re.DOTALL)
            for treffer in muster.finditer(agents.read_text(encoding="utf-8")):
                abschnitt = ziel / "agents-md" / f"{treffer.group(2)}.md"
                abschnitt.parent.mkdir(parents=True, exist_ok=True)
                abschnitt.write_text(generalisieren(treffer.group(3)) + "\n", encoding="utf-8")
        genutzt = set()
        for p in ziel.rglob("*"):
            if p.is_file():
                genutzt |= set(PLACEHOLDER.findall(p.read_text(encoding="utf-8")))
                genutzt |= set(PLACEHOLDER.findall(str(p.relative_to(ziel))))
        stack_yaml = {"name": name, "version": "0.1.0",
                      "description": f"Aus Projekt {title} extrahiert (sdd stack extract)",
                      "languages": ["unbekannt"],
                      "placeholders": [{"name": n, **({"default": ersetzungen[n]}
                                                      if n == "package_name" else {})}
                                       for n in sorted(genutzt)]}
        (ziel / "files").mkdir(parents=True, exist_ok=True)
        (ziel / "stack.yaml").write_text(yaml.safe_dump(stack_yaml, sort_keys=False,
                                                        allow_unicode=True), encoding="utf-8")
        return load(ziel, "extracted")
    except (OSError, StackError):
        shutil.rmtree(ziel, ignore_errors=True)
        raise
