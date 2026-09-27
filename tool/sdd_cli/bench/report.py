"""Kennzahlen, Pareto-Front, Signifikanz, Report und Vergleich (SPEC-0056 FR-07, FR-08, CON-0224).

Alle Auswertungen laufen je `q_kind`; Eval- und Qualitätsscores werden nie gemeinsam gerankt.
"""
from __future__ import annotations

import html
import math
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from ..pipeline.schemas import errors as schema_errors

EFFIZIENZ_EINHEIT = 1e5
Q_KINDS = ("quality", "eval")


@dataclass
class Entry:
    key: str
    q_kind: str
    records: list[dict]
    q_mean: float | None = None
    q_std: float = 0.0
    parts: dict[str, tuple[float | None, float]] = field(default_factory=dict)
    t_in: float = 0.0
    t_out: float = 0.0
    t_reason: float = 0.0
    t_claude: float = 0.0
    estimated: bool = False
    tokens_per_fr: float | None = None
    failed_attempts: float = 0.0
    pareto_all: bool = False
    pareto_local: bool = False
    indistinct: bool = False

    def t_total(self, *, exclude_reasoning: bool = False) -> float:
        t = self.t_in + self.t_out
        return t - self.t_reason if exclude_reasoning else t

    @property
    def t_local(self) -> float:
        return self.t_in + self.t_out - self.t_claude

    def efficiency(self, *, exclude_reasoning: bool = False) -> float | None:
        t = self.t_total(exclude_reasoning=exclude_reasoning)
        if self.q_mean is None or t <= 0:
            return None
        return self.q_mean / (t / EFFIZIENZ_EINHEIT)


def _mean_std(werte: list[float]) -> tuple[float | None, float]:
    werte = [w for w in werte if w is not None]
    if not werte:
        return None, 0.0
    return statistics.fmean(werte), statistics.pstdev(werte) if len(werte) > 1 else 0.0


def entry(key: str, q_kind: str, records: list[dict]) -> Entry:
    e = Entry(key, q_kind, records)
    e.q_mean, e.q_std = _mean_std([r.get("Q") for r in records])
    for teil in ("Q_req", "Q_arch", "Q_code"):
        if any(teil in r for r in records):
            e.parts[teil] = _mean_std([r.get(teil) for r in records])
    for feld in ("T_in", "T_out", "T_reason", "T_claude"):
        setattr(e, feld.lower(), statistics.fmean(r[feld] for r in records))
    e.estimated = any(r.get("estimated") for r in records)
    erfuellt = sum(r.get("frs_met", 0) for r in records)
    if any("frs_met" in r for r in records):
        e.tokens_per_fr = (sum(r["T_in"] + r["T_out"] for r in records) / erfuellt
                           if erfuellt else None)
    e.failed_attempts = statistics.fmean(r.get("failed_attempts", 0) for r in records)
    return e


def pareto(entries: list[Entry], t_of) -> set[str]:
    """Nicht dominierte Einträge über (Q ↑, T ↓) (CON-0224 INV-02)."""
    punkte = [(e.key, e.q_mean, t_of(e)) for e in entries if e.q_mean is not None]
    front = set()
    for k, q, t in punkte:
        dominiert = any(q2 >= q and t2 <= t and (q2 > q or t2 < t)
                        for k2, q2, t2 in punkte if k2 != k)
        if not dominiert:
            front.add(k)
    return front


def mark_indistinct(entries: list[Entry]) -> None:
    """Einträge, deren Abstand zum besten kleiner als die gepoolte Streuung ist (INV-03)."""
    gueltig = [e for e in entries if e.q_mean is not None]
    if len(gueltig) < 2:
        return
    bester = max(gueltig, key=lambda e: e.q_mean)
    for e in gueltig:
        if e is bester:
            continue
        gepoolt = math.sqrt((e.q_std ** 2 + bester.q_std ** 2) / 2)
        if bester.q_mean - e.q_mean < gepoolt:
            e.indistinct = bester.indistinct = True


def valid_records(records: list[dict]) -> tuple[list[dict], int]:
    gut = [r for r in records if not schema_errors("bench-record", r)]
    return gut, len(records) - len(gut)


def group(records: list[dict], *, by: str = "assignment") -> dict[str, dict[str, list[Entry]]]:
    """{q_kind: {abschnitt: [Entry]}}; `by=role` bildet je Rolle eine Rangliste der Profile."""
    ergebnis: dict[str, dict[str, list[Entry]]] = {}
    for q_kind in Q_KINDS:
        teil = [r for r in records if r["q_kind"] == q_kind]
        if not teil:
            continue
        abschnitte: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
        for r in teil:
            if by == "role":
                for rolle, b in r["roles"].items():
                    abschnitte[rolle][b["profile"]].append(r)
            else:
                abschnitte["Belegungen"][r["assignment"]].append(r)
        ergebnis[q_kind] = {}
        for name, gruppen in abschnitte.items():
            eintraege = [entry(k, q_kind, rs) for k, rs in gruppen.items()]
            front_all = pareto(eintraege, lambda e: e.t_total())
            front_local = pareto(eintraege, lambda e: e.t_local)
            for e in eintraege:
                e.pareto_all, e.pareto_local = e.key in front_all, e.key in front_local
            mark_indistinct(eintraege)
            eintraege.sort(key=lambda e: -(e.q_mean if e.q_mean is not None else -1))
            ergebnis[q_kind][name] = eintraege
    return ergebnis


def _fmt(wert: float | None, std: float | None = None, nachkomma: int = 3) -> str:
    if wert is None:
        return "–"
    return f"{wert:.{nachkomma}f}" + (f" ± {std:.{nachkomma}f}" if std else "")


def _tok(wert: float, estimated: bool) -> str:
    return f"{wert:,.0f}".replace(",", " ") + ("*" if estimated else "")


def markdown(ordner: Path, records: list[dict], *, by: str = "assignment",
             exclude_reasoning: bool = False, filtered: dict | None = None) -> str:
    zeilen = [f"# Benchmark-Report {ordner.name}", ""]
    gruppen = group(records, by=by)
    for q_kind, abschnitte in gruppen.items():
        titel = "Qualität (Tests und Gates, SPEC-0054)" if q_kind == "quality" else \
            "Rollen-Evals (SPEC-0055)"
        zeilen += [f"## {titel} – q_kind {q_kind}", ""]
        for name, eintraege in abschnitte.items():
            zeilen += [f"### {name}", "",
                       "| Eintrag | Q | Q_req | Q_arch | Q_code | T_in | T_out | T_reason | "
                       "T_claude | Q/100k T | T je erf. FR | Fehlversuche | Pareto | Hinweis |",
                       "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
            for e in eintraege:
                teile = [_fmt(*e.parts[t]) if t in e.parts else "–"
                         for t in ("Q_req", "Q_arch", "Q_code")]
                pareto_text = ", ".join(x for x, ja in (("alle T", e.pareto_all),
                                                        ("lokal", e.pareto_local)) if ja) or "–"
                zeilen.append(
                    f"| {e.key} | {_fmt(e.q_mean, e.q_std)} | {' | '.join(teile)} | "
                    f"{_tok(e.t_in, e.estimated)} | {_tok(e.t_out, e.estimated)} | "
                    f"{_tok(e.t_reason, e.estimated)} | {_tok(e.t_claude, e.estimated)} | "
                    f"{_fmt(e.efficiency(exclude_reasoning=exclude_reasoning), None, 2)} | "
                    f"{_fmt(e.tokens_per_fr, None, 0)} | {e.failed_attempts:.1f} | "
                    f"{pareto_text} | {'nicht unterscheidbar' if e.indistinct else ''} |")
            zeilen.append("")
    if filtered:
        zeilen += ["## Gefiltert (Stufenmodell)", ""]
        zeilen += [f"- {suite}: {', '.join(namen)}" for suite, namen in filtered.items()]
        zeilen.append("")
    zeilen += ["`*` geschätzte Tokens (Provider ohne Usage). „nicht unterscheidbar“: Abstand zum "
               "besten Eintrag kleiner als die gepoolte Standardabweichung.", ""]
    return "\n".join(zeilen)


def html_report(ordner: Path, records: list[dict], md: str, *, by: str = "assignment") -> str:
    """Eigenständige HTML-Seite: Markdown-Tabellen als Text plus Streudiagramm Q gegen T."""
    punkte = [(e, q_kind) for q_kind, abschnitte in group(records, by=by).items()
              for eintraege in abschnitte.values() for e in eintraege if e.q_mean is not None]
    breite, hoehe, rand = 640, 360, 40
    t_max = max((e.t_total() for e, _ in punkte), default=1) or 1
    kreise = []
    for e, q_kind in punkte:
        x = rand + (breite - 2 * rand) * e.t_total() / t_max
        y = hoehe - rand - (hoehe - 2 * rand) * e.q_mean
        farbe = "#d9480f" if e.pareto_all else "#495057"
        kreise.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{farbe}">'
                      f'<title>{html.escape(e.key)} ({q_kind}): Q {e.q_mean:.3f}, '
                      f'T {e.t_total():.0f}</title></circle>')
    svg = (f'<svg width="{breite}" height="{hoehe}" role="img" aria-label="Q gegen Tokens">'
           f'<line x1="{rand}" y1="{hoehe - rand}" x2="{breite - rand}" y2="{hoehe - rand}" '
           f'stroke="#868e96"/><line x1="{rand}" y1="{rand}" x2="{rand}" y2="{hoehe - rand}" '
           f'stroke="#868e96"/><text x="{breite - rand}" y="{hoehe - 10}" text-anchor="end">'
           f'Tokens</text><text x="10" y="{rand - 10}">Q</text>{"".join(kreise)}</svg>')
    return (f"<!doctype html><html lang=\"de\"><meta charset=\"utf-8\"><title>Benchmark "
            f"{html.escape(ordner.name)}</title><body style=\"font-family:sans-serif;"
            f"max-width:1100px;margin:auto;padding:16px\"><h1>Benchmark {html.escape(ordner.name)}"
            f"</h1><p>Rot: Pareto-Front (alle Tokens).</p>{svg}<pre style=\"white-space:pre-wrap\">"
            f"{html.escape(md)}</pre></body></html>")


# ── Vergleich (FR-08) ────────────────────────────────────────────────────────

def compare(a: list[dict], b: list[dict]) -> tuple[list[dict], list[str]]:
    """Deltas je (q_kind, Belegung) und Warnungen zu getauschten Modellen (CON-0224 INV-06)."""
    zeilen = []
    for q_kind in Q_KINDS:
        ga = {k: entry(k, q_kind, rs) for k, rs in _by_key(a, q_kind).items()}
        gb = {k: entry(k, q_kind, rs) for k, rs in _by_key(b, q_kind).items()}
        for k in sorted(set(ga) | set(gb)):
            ea, eb = ga.get(k), gb.get(k)
            zeile = {"q_kind": q_kind, "key": k,
                     "Q_a": ea.q_mean if ea else None, "Q_b": eb.q_mean if eb else None,
                     "T_a": ea.t_total() if ea else None, "T_b": eb.t_total() if eb else None}
            if ea and eb and ea.q_mean is not None and eb.q_mean is not None:
                gepoolt = math.sqrt((ea.q_std ** 2 + eb.q_std ** 2) / 2)
                zeile["delta_Q"] = eb.q_mean - ea.q_mean
                zeile["delta_T"] = eb.t_total() - ea.t_total()
                zeile["distinct"] = abs(zeile["delta_Q"]) >= gepoolt
            zeilen.append(zeile)
    return zeilen, _model_warnings(a, b)


def _by_key(records: list[dict], q_kind: str) -> dict[str, list[dict]]:
    gruppen: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        if r["q_kind"] == q_kind:
            gruppen[r["assignment"]].append(r)
    return gruppen


def _server_models(records: list[dict]) -> dict[str, set[str]]:
    modelle: dict[str, set[str]] = defaultdict(set)
    for r in records:
        for b in r["roles"].values():
            if b.get("server_model"):
                modelle[b["profile"]].add(b["server_model"])
    return modelle


def _model_warnings(a: list[dict], b: list[dict]) -> list[str]:
    ma, mb = _server_models(a), _server_models(b)
    return [f"Profil {p}: Server meldet {', '.join(sorted(mb[p]))} statt "
            f"{', '.join(sorted(ma[p]))}" for p in sorted(set(ma) & set(mb)) if ma[p] != mb[p]]
