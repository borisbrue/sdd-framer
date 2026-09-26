"""Ratchet-Regel und Übernahme (SPEC-0055 FR-07, FR-08, CON-0220).

`compare` entscheidet über `accept`/`reject`; `accept` übernimmt eine Kandidatenversion in
getrennten Schritten: Version bestimmen, Rollendatei schreiben, `baseline.json` ersetzen (Memento),
CHANGELOG ergänzen.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from ..roles import split_frontmatter
from .cases import RoleHome
from .report import report_errors


class RatchetError(Exception):
    """Report ungültig, Rollen verschieden oder Kandidat passt nicht zum Report."""


@dataclass
class Verdict:
    accept: bool
    reasons: list[str] = field(default_factory=list)
    deltas: list[dict] = field(default_factory=list)

    @property
    def label(self) -> str:
        return "accept" if self.accept else "reject"


def load(path: Path) -> dict:
    try:
        daten = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RatchetError(f"{path}: {exc}") from exc
    fehler = report_errors(daten)
    if fehler:
        raise RatchetError(f"{path}: kein gültiger Report oder Baseline ({fehler[0]})")
    return daten


def _cases(daten: dict) -> dict[str, dict]:
    if daten["kind"] == "role-baseline":
        return dict(daten["cases"])
    return {c["id"]: {"score": c["score"], "passed": c["passed"]} for c in daten["visible"]}


def _holdout_mean(daten: dict) -> float | None:
    holdout = daten["holdout"]
    if isinstance(holdout, list):
        return (sum(c["score"] for c in holdout) / len(holdout)) if holdout else None
    return holdout.get("mean")


def compare(a: dict, b: dict) -> Verdict:
    """B gegen A nach CON-0220 INV-01; Holdout-Fälle werden nie einzeln genannt."""
    if a["role"] != b["role"]:
        raise RatchetError(f"Reports verschiedener Rollen ({a['role']}, {b['role']})")
    gruende: list[str] = []
    fa, fb = _cases(a), _cases(b)
    deltas = [{"id": cid, "before": fa[cid]["score"] if cid in fa else None,
               "after": fb[cid]["score"] if cid in fb else None,
               "passed_before": fa.get(cid, {}).get("passed"),
               "passed_after": fb.get(cid, {}).get("passed")} for cid in sorted({*fa, *fb})]
    ta, tb = a["total"]["mean"], b["total"]["mean"]
    if ta is not None and (tb is None or tb < ta):
        gruende.append(f"Gesamtscore sinkt ({ta} → {tb})")
    ha, hb = _holdout_mean(a), _holdout_mean(b)
    if ha is not None and (hb is None or hb < ha):
        gruende.append(f"Holdout-Score sinkt ({ha:.4f} → "
                       f"{'–' if hb is None else f'{hb:.4f}'})")
    for d in deltas:
        if d["passed_before"] and not d["passed_after"]:
            gruende.append(f"{d['id']} fällt von pass auf fail")
    if a["output_schema"] != b["output_schema"]:
        gruende.append(f"output_schema geändert ({a['output_schema']} → {b['output_schema']}); "
                       f"das braucht eine Contract-Änderung nach SPEC-0053")
    return Verdict(not gruende, gruende, deltas)


def baseline_from(report: dict, *, version: str, reason: str | None = None) -> dict:
    daten = {"kind": "role-baseline", "role": report["role"], "role_version": version,
             "prompt_hash": report["prompt_hash"], "output_schema": report["output_schema"],
             "profile": report["profile"],
             "accepted_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
             "cases": _cases(report),
             "holdout": report["holdout"] if isinstance(report["holdout"], dict) else {
                 "cases": len(report["holdout"]),
                 "mean": _holdout_mean(report), "std": None, "pass_at_1": None,
                 "pass_all": None},
             "total": report["total"]}
    if reason:
        daten["forced"] = {"reason": reason}
    return daten


def bump(version: str, *, prompt_changed: bool) -> str:
    major, minor, patch = (int(x) for x in version.split("."))
    return f"{major}.{minor + 1}.0" if prompt_changed else f"{major}.{minor}.{patch + 1}"


@dataclass
class Acceptance:
    old_version: str
    new_version: str
    target: Path
    verdict: Verdict
    forced: bool


def _prompt_hash(text: str) -> str:
    import hashlib

    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def accept(home: RoleHome, report_path: Path, *, force: bool = False,
           reason: str | None = None) -> Acceptance:
    report = load(report_path)
    if report["kind"] != "role-eval-report":
        raise RatchetError(f"{report_path}: kein Eval-Report")
    if report["role"] != home.role:
        raise RatchetError(f"Report gehört zu {report['role']}, nicht zu {home.role}")
    kandidat = Path(report.get("role_file") or home.role_file)
    if not kandidat.is_file():
        raise RatchetError(f"Kandidatendatei {kandidat} fehlt")
    kopf, prompt = split_frontmatter(kandidat.read_text(encoding="utf-8"))
    if _prompt_hash(prompt) != report["prompt_hash"]:
        raise RatchetError(f"{kandidat} passt nicht zum Report (Prompt-Hash verschieden)")

    basis = load(home.baseline) if home.baseline.is_file() else None
    urteil = compare(basis, report) if basis else Verdict(True)
    if not urteil.accept and not force:
        return Acceptance("", "", home.role_file, urteil, forced=False)

    alt_text = home.role_file.read_text(encoding="utf-8") if home.role_file.is_file() else None
    alt_kopf, alt_prompt = split_frontmatter(alt_text) if alt_text else ({}, "")
    alt_version = str(alt_kopf.get("version") or kopf["version"])
    neu = bump(alt_version, prompt_changed=_prompt_hash(alt_prompt) != report["prompt_hash"])

    # 1. Rollendatei mit neuer Version schreiben
    kopf["version"] = neu
    home.role_file.parent.mkdir(parents=True, exist_ok=True)
    home.role_file.write_text("---\n" + yaml.safe_dump(kopf, sort_keys=False, allow_unicode=True)
                              + "---\n" + prompt + "\n", encoding="utf-8")
    # 2. Baseline ersetzen (Memento)
    home.data_dir.mkdir(parents=True, exist_ok=True)
    home.baseline.write_text(json.dumps(baseline_from(report, version=neu,
                                                      reason=reason if force else None),
                                        ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # 3. CHANGELOG
    vorher = basis["total"]["mean"] if basis else None
    zeile = (f"- {date.today().isoformat()}: {home.role} {alt_version} → {neu}, Score "
             f"{'–' if vorher is None else vorher} → {report['total']['mean']} "
             f"(Profil {report['profile']['name']}, Report {report_path.name})")
    if force and not urteil.accept:
        zeile += f"; erzwungen: {reason} ({'; '.join(urteil.reasons)})"
    kopfzeile = f"# CHANGELOG {home.role}\n\n"
    bisher = home.changelog.read_text(encoding="utf-8") if home.changelog.is_file() \
        else kopfzeile
    home.changelog.write_text(bisher.rstrip("\n") + "\n" + zeile + "\n", encoding="utf-8")
    return Acceptance(alt_version, neu, home.role_file, urteil, forced=force and not urteil.accept)


def summary(verdict: Verdict) -> dict[str, Any]:
    return {"result": verdict.label, "reasons": verdict.reasons, "cases": verdict.deltas}
