"""Quality-Gates (SPEC-0054 FR-10, CON-0196 INV-04/INV-07/INV-08).

Score-Pfade (Werte in [0, 1]) und Zähler-Pfade (`count.…`, ganze Zahlen) sind getrennt.
Gates sind fail-closed: ein Pfad ohne Wert gilt als nicht bestanden.
"""
from __future__ import annotations

import operator
import re

DIMENSIONS = ("requirements", "architecture", "code_quality", "judge")
COUNTERS = ("count.architecture.errors", "count.architecture.warnings", "count.frs_missing",
            "count.probes_na")
_GATE_RE = re.compile(r"^\s*(?P<path>[a-z_][a-z0-9_.]*)\s*(?P<op>>=|<=|==|>|<)\s*"
                      r"(?P<value>-?\d+(?:\.\d+)?)\s*$")
_OPS = {">=": operator.ge, "<=": operator.le, "==": operator.eq, ">": operator.gt,
        "<": operator.lt}


def _is_score_path(path: str) -> bool:
    teile = path.split(".")
    if path == "total":
        return True
    return teile[0] in DIMENSIONS and len(teile) <= 2


def validate_gate(gate: str) -> str | None:
    m = _GATE_RE.match(gate)
    if not m:
        return "ungültige Syntax"
    path, wert = m["path"], m["value"]
    if path.startswith("count."):
        if path not in COUNTERS:
            return "unbekannter Pfad"
        return None if re.fullmatch(r"\d+", wert) else "ganze Zahl erwartet"
    if not _is_score_path(path):
        return "unbekannter Pfad"
    return None if 0 <= float(wert) <= 1 else "Wert in [0, 1] erwartet"


def _node(tree: dict, path: str) -> float | None:
    if path == "total":
        return tree.get("score")
    aktuell = tree
    for teil in path.split("."):
        kinder = {k["name"]: k for k in aktuell.get("children", [])}
        metriken = {m["name"]: m for m in aktuell.get("metrics", [])}
        if teil in kinder:
            aktuell = kinder[teil]
        elif teil in metriken:
            return metriken[teil].get("normalized")
        else:
            return None
    return aktuell.get("score")


def _counter(report: dict, path: str) -> int:
    arch = report.get("architecture") or {}
    verstoesse = arch.get("violations") or []
    return {
        "count.architecture.errors": sum(v.get("severity") == "error" for v in verstoesse),
        "count.architecture.warnings": sum(v.get("severity") == "warn" for v in verstoesse),
        "count.frs_missing": sum(f.get("status") == "fehlt"
                                 for f in (report.get("requirements") or {}).get("frs", [])),
        "count.probes_na": sum(p.get("status") == "n/a" for p in report.get("probes") or []),
    }[path]


def evaluate_gates(gates: list[str], report: dict) -> list[dict]:
    ergebnisse = []
    for gate in gates:
        fehler = validate_gate(gate)
        if fehler:
            ergebnisse.append({"expression": gate, "passed": False, "reason": fehler})
            continue
        m = _GATE_RE.match(gate)
        path, op, soll = m["path"], _OPS[m["op"]], float(m["value"])
        ist = _counter(report, path) if path.startswith("count.") else _node(report["tree"], path)
        if ist is None:
            ergebnisse.append({"expression": gate, "passed": False,
                               "reason": f"{path} ist n/a (fail-closed)"})
            continue
        bestanden = bool(op(ist, soll))
        eintrag = {"expression": gate, "passed": bestanden}
        if not bestanden:
            eintrag["reason"] = f"{path} = {round(ist, 4)}"
        ergebnisse.append(eintrag)
    return ergebnisse
