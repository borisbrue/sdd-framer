"""Parser für die Austauschformate der Sonden (SPEC-0054 FR-02, CON-0193).

Adapter Pattern: je Format ein `ProbeResultParser` hinter derselben Schnittstelle. Der Kern
kennt nur Formate, keine Werkzeuge; werkzeugspezifische Ausgaben werden im Projekt in eines
dieser Formate konvertiert.
"""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Protocol
from urllib.parse import unquote, urlparse

from .schemas import validator

FR_RE = re.compile(r"FR-\d+[a-z]?")


class ParseError(Exception):
    """Die Ausgabe einer Sonde genügt ihrem Format nicht."""


@dataclass(frozen=True)
class TestCase:
    __test__ = False

    name: str
    classname: str
    status: str
    frs: tuple[str, ...] = ()
    file: str | None = None


@dataclass(frozen=True)
class Finding:
    rule: str
    message: str
    file: str
    line: int
    severity: str
    column: int | None = None


@dataclass(frozen=True)
class Metric:
    name: str
    value: float
    scope: str = "project"
    unit: str | None = None


@dataclass(frozen=True)
class Edge:
    source: str
    target: str | None
    kind: str
    symbol: str
    file: str
    line: int
    args: tuple[str, ...] = ()
    unresolved: bool = False


@dataclass
class TestSuiteResult:
    __test__ = False

    cases: list[TestCase]


@dataclass
class FindingsResult:
    findings: list[Finding]
    discarded: int = 0


@dataclass
class MetricsResult:
    metrics: list[Metric]


@dataclass
class DepsGraph:
    kinds: frozenset[str]
    edges: list[Edge] = field(default_factory=list)


ProbeResult = TestSuiteResult | FindingsResult | MetricsResult | DepsGraph


class ProbeResultParser(Protocol):
    def parse(self, path: Path, root: Path, **options: object) -> ProbeResult: ...


# ── JUnit ─────────────────────────────────────────────────────────────────────

class JUnitParser:
    def parse(self, path: Path, root: Path, **options: object) -> TestSuiteResult:
        try:
            wurzel = ET.parse(path).getroot()
        except (ET.ParseError, OSError) as exc:
            raise ParseError(f"kein gültiges JUnit-XML: {exc}") from exc
        if wurzel.tag not in ("testsuites", "testsuite"):
            raise ParseError(f"unerwartetes Wurzelelement <{wurzel.tag}>")
        marker = options.get("fr_marker")
        faelle = []
        for tc in wurzel.iter("testcase"):
            name = tc.get("name")
            if not name:
                raise ParseError("<testcase> ohne name")
            faelle.append(TestCase(
                name=name,
                classname=tc.get("classname", ""),
                status=self._status(tc),
                frs=self._frs(tc, name, marker),
                file=tc.get("file"),
            ))
        return TestSuiteResult(faelle)

    @staticmethod
    def _status(tc: ET.Element) -> str:
        for tag, status in (("failure", "failed"), ("error", "error"), ("skipped", "skipped")):
            if tc.find(tag) is not None:
                return status
        return "passed"

    @staticmethod
    def _frs(tc: ET.Element, name: str, marker: object) -> tuple[str, ...]:
        if marker == "name":
            return tuple(dict.fromkeys(FR_RE.findall(name)))
        if marker == "property":
            werte = [p.get("value", "") for p in tc.iter("property") if p.get("name") == "fr"]
            return tuple(dict.fromkeys(fr for w in werte for fr in FR_RE.findall(w)))
        return ()


# ── SARIF ─────────────────────────────────────────────────────────────────────

_SARIF_LEVEL = {"error": "error", "warning": "warning", "note": "note", "none": "note"}


class SarifParser:
    def parse(self, path: Path, root: Path, **options: object) -> FindingsResult:
        daten = _load_json(path)
        runs = daten.get("runs") if isinstance(daten, dict) else None
        if not isinstance(runs, list):
            raise ParseError("SARIF ohne Liste 'runs'")
        ergebnis = FindingsResult([])
        for run in runs:
            basen = run.get("originalUriBaseIds") or {}
            for res in run.get("results") or []:
                datei = self._datei(res, basen, root)
                if datei is None:
                    ergebnis.discarded += 1
                    continue
                region = self._location(res).get("region") or {}
                ergebnis.findings.append(Finding(
                    rule=res.get("ruleId") or (res.get("rule") or {}).get("id") or "unknown",
                    message=(res.get("message") or {}).get("text", ""),
                    file=datei,
                    line=int(region.get("startLine") or 1),
                    column=region.get("startColumn"),
                    severity=_SARIF_LEVEL.get(res.get("level", "warning"), "warning"),
                ))
        return ergebnis

    @staticmethod
    def _location(res: dict) -> dict:
        locs = res.get("locations") or [{}]
        return locs[0].get("physicalLocation") or {}

    def _datei(self, res: dict, basen: dict, root: Path) -> str | None:
        art = self._location(res).get("artifactLocation") or {}
        uri = art.get("uri")
        if not uri:
            return None
        basis = (basen.get(art.get("uriBaseId")) or {}).get("uri", "") if art.get("uriBaseId") else ""
        return relative_path(_uri_to_path(basis) + _uri_to_path(uri) if basis else
                             _uri_to_path(uri), root)


def _uri_to_path(uri: str) -> str:
    teile = urlparse(uri)
    if teile.scheme == "file":
        return unquote(teile.path)
    return unquote(uri)


def relative_path(pfad: str, root: Path) -> str | None:
    """Pfad relativ zur Projektwurzel mit '/', oder None, wenn er außerhalb liegt."""
    p = Path(pfad)
    if p.is_absolute():
        try:
            p = p.resolve().relative_to(root.resolve())
        except ValueError:
            return None
    teile = PurePosixPath(p.as_posix())
    if ".." in teile.parts:
        return None
    return str(teile)


# ── Coverage ──────────────────────────────────────────────────────────────────

class CoberturaParser:
    def parse(self, path: Path, root: Path, **options: object) -> MetricsResult:
        try:
            wurzel = ET.parse(path).getroot()
        except (ET.ParseError, OSError) as exc:
            raise ParseError(f"kein gültiges Cobertura-XML: {exc}") from exc
        gueltig, abgedeckt = wurzel.get("lines-valid"), wurzel.get("lines-covered")
        if gueltig and abgedeckt and float(gueltig) > 0:
            quote = float(abgedeckt) / float(gueltig)
        elif wurzel.get("line-rate") is not None:
            quote = float(wurzel.get("line-rate"))
        else:
            raise ParseError("Cobertura ohne lines-valid/lines-covered oder line-rate")
        return MetricsResult([Metric("coverage", quote)])


class LcovParser:
    def parse(self, path: Path, root: Path, **options: object) -> MetricsResult:
        gefunden = getroffen = 0
        for zeile in path.read_text(encoding="utf-8").splitlines():
            if zeile.startswith("LF:"):
                gefunden += int(zeile[3:])
            elif zeile.startswith("LH:"):
                getroffen += int(zeile[3:])
        if gefunden == 0:
            raise ParseError("LCOV ohne LF-Einträge")
        return MetricsResult([Metric("coverage", getroffen / gefunden)])


# ── sdd-Formate ───────────────────────────────────────────────────────────────

class _SddFormatParser:
    fmt = ""

    def parse(self, path: Path, root: Path, **options: object) -> ProbeResult:
        daten = _load_json(path)
        if not isinstance(daten, dict) or daten.get("format") != self.fmt:
            raise ParseError(f"Datei ist nicht im Format {self.fmt}")
        fehler = next(iter(validator("exchange-formats").iter_errors(daten)), None)
        if fehler is not None:
            raise ParseError(f"{self.fmt} verletzt das Schema: {fehler.message}")
        return self._build(daten)

    def _build(self, daten: dict) -> ProbeResult:
        raise NotImplementedError


class SddDepsParser(_SddFormatParser):
    fmt = "sdd-deps"

    def _build(self, daten: dict) -> DepsGraph:
        return DepsGraph(
            kinds=frozenset(daten["kinds_provided"]),
            edges=[Edge(source=e["from"], target=e["to"], kind=e["kind"], symbol=e["symbol"],
                        file=e["file"], line=e["line"], args=tuple(e.get("args") or ()),
                        unresolved=bool(e.get("unresolved"))) for e in daten["edges"]],
        )


class SddMetricsParser(_SddFormatParser):
    fmt = "sdd-metrics"

    def _build(self, daten: dict) -> MetricsResult:
        return MetricsResult([Metric(m["name"], float(m["value"]), m.get("scope", "project"),
                                     m.get("unit")) for m in daten["metrics"]])


class SddFindingsParser(_SddFormatParser):
    fmt = "sdd-findings"

    def _build(self, daten: dict) -> FindingsResult:
        return FindingsResult([Finding(f["rule"], f["message"], f["file"], f["line"],
                                       f["severity"], f.get("column"))
                               for f in daten["findings"]])


def _load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError) as exc:
        raise ParseError(f"kein gültiges JSON: {exc}") from exc


PARSERS: dict[str, ProbeResultParser] = {
    "junit": JUnitParser(),
    "sarif": SarifParser(),
    "cobertura": CoberturaParser(),
    "lcov": LcovParser(),
    "sdd-deps": SddDepsParser(),
    "sdd-metrics": SddMetricsParser(),
    "sdd-findings": SddFindingsParser(),
}


def parse_output(fmt: str, path: Path, root: Path, **options: object) -> ProbeResult:
    try:
        parser = PARSERS[fmt]
    except KeyError as exc:
        raise ParseError(f"unbekanntes Format {fmt!r}") from exc
    try:
        return parser.parse(path, root, **options)
    except ParseError:
        raise
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        raise ParseError(f"Ausgabe im Format {fmt} nicht lesbar: {exc}") from exc
