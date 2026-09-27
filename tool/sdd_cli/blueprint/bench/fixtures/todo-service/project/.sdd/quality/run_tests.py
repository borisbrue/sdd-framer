"""Testsonde des Fixtures: unittest-Discovery mit JUnit-XML, nur Standardbibliothek.

Aufruf im Projektverzeichnis:

    python .sdd/quality/run_tests.py --start <verzeichnis> --junit <ausgabe.xml>

- Findet Tests wie `python -m unittest discover` (Muster `test*.py`); Verzeichnisse mit Tests
  brauchen eine `__init__.py`, das Projektverzeichnis ist die Importwurzel.
- Schreibt je Testfall ein `<testcase>`; Import- und Ladefehler erscheinen als `<error>`.
- FR-Marker: `spec0001_fr02` oder `fr02` im Testnamen bzw. `FR-02` in der ersten Docstring-Zeile
  werden als `<property name="fr" value="FR-02"/>` ausgegeben, bei Spec-Bezug zusätzlich
  `<property name="spec" value="SPEC-0001"/>`.
- Exit 0, wenn alle Tests grün sind (übersprungene zählen nicht als rot), sonst 1.
"""
from __future__ import annotations

import argparse
import io
import os
import re
import sys
import time
import traceback
import unittest
import xml.etree.ElementTree as ET

NAME_MARKER = re.compile(r"(?:spec(\d{4})_)?fr_?(\d{1,3})(?![0-9])", re.IGNORECASE)
DOC_MARKER = re.compile(r"(?:(SPEC-\d{4})\s+)?(FR-\d+)")


def _markers(test: unittest.TestCase) -> list[tuple[str | None, str]]:
    """(Spec-ID oder None, FR-ID) aus Testname und erster Docstring-Zeile."""
    name = getattr(test, "_testMethodName", "") or ""
    gefunden: list[tuple[str | None, str]] = []
    for spec, fr in NAME_MARKER.findall(name):
        gefunden.append((f"SPEC-{spec}" if spec else None, f"FR-{int(fr):02d}"))
    doc = test.shortDescription() or ""
    for spec, fr in DOC_MARKER.findall(doc):
        gefunden.append((spec or None, fr))
    return list(dict.fromkeys(gefunden))


class _Result(unittest.TestResult):
    """Sammelt je Test Status, Dauer und Meldung."""

    def __init__(self) -> None:
        super().__init__()
        self.cases: list[dict] = []
        self._start: dict[str, float] = {}

    def startTest(self, test: unittest.TestCase) -> None:
        super().startTest(test)
        self._start[test.id()] = time.monotonic()

    def _add(self, test: unittest.TestCase, status: str, text: str = "") -> None:
        dauer = time.monotonic() - self._start.get(test.id(), time.monotonic())
        self.cases.append({"test": test, "status": status, "text": text, "time": dauer})

    def addSuccess(self, test):
        super().addSuccess(test)
        self._add(test, "passed")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._add(test, "failure", self._exc_info_to_string(err, test))

    def addError(self, test, err):
        super().addError(test, err)
        self._add(test, "error", self._exc_info_to_string(err, test))

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self._add(test, "skipped", reason)

    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test, err)
        self._add(test, "passed")

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        self._add(test, "failure", "unerwarteter Erfolg")

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err is not None:
            status = "failure" if issubclass(err[0], test.failureException) else "error"
            self._add(test, status, self._exc_info_to_string(err, test))


def _junit(cases: list[dict], dauer: float) -> ET.Element:
    fehler = sum(1 for c in cases if c["status"] == "error")
    rot = sum(1 for c in cases if c["status"] == "failure")
    skip = sum(1 for c in cases if c["status"] == "skipped")
    wurzel = ET.Element("testsuites")
    suite = ET.SubElement(wurzel, "testsuite", name="unittest", tests=str(len(cases)),
                          failures=str(rot), errors=str(fehler), skipped=str(skip),
                          time=f"{dauer:.3f}")
    for c in cases:
        test = c["test"]
        teile = test.id().rsplit(".", 1)
        classname = teile[0] if len(teile) == 2 else ""
        name = getattr(test, "_testMethodName", None) or teile[-1]
        tc = ET.SubElement(suite, "testcase", classname=classname, name=name,
                           time=f"{c['time']:.3f}")
        modul = sys.modules.get(type(test).__module__)
        datei = getattr(modul, "__file__", None)
        if datei:
            tc.set("file", os.path.relpath(datei))
        marker = _markers(test)
        if marker:
            props = ET.SubElement(tc, "properties")
            for spec, fr in marker:
                ET.SubElement(props, "property", name="fr", value=fr)
                if spec:
                    ET.SubElement(props, "property", name="spec", value=spec)
        if c["status"] in ("failure", "error"):
            kurz = (c["text"].strip().splitlines() or [c["status"]])[-1][:200]
            el = ET.SubElement(tc, c["status"], message=kurz)
            el.text = c["text"]
        elif c["status"] == "skipped":
            ET.SubElement(tc, "skipped", message=c["text"][:200])
    return wurzel


STATUS_RANG = {"error": 3, "failure": 2, "passed": 1, "skipped": 0}


def _merge(cases: list[dict]) -> list[dict]:
    """Ein Eintrag je Testmethode: rote Subtests bestimmen den Status, Meldungen werden verbunden."""
    je_test: dict[str, dict] = {}
    for c in cases:
        bisher = je_test.get(c["test"].id())
        if bisher is None:
            je_test[c["test"].id()] = dict(c)
            continue
        if STATUS_RANG[c["status"]] > STATUS_RANG[bisher["status"]]:
            bisher["status"] = c["status"]
        if c["status"] in ("failure", "error"):
            bisher["text"] = (bisher["text"] + "\n" + c["text"]).strip()
        bisher["time"] = max(bisher["time"], c["time"])
    return list(je_test.values())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--start", default="tests", help="Startverzeichnis der Discovery")
    parser.add_argument("--junit", required=True, help="Pfad der JUnit-XML-Ausgabe")
    parser.add_argument("--pattern", default="test*.py")
    args = parser.parse_args(argv)

    wurzel = os.getcwd()
    if wurzel not in sys.path:
        sys.path.insert(0, wurzel)
    start = time.monotonic()
    ergebnis = _Result()
    if os.path.isdir(args.start):
        try:
            suite = unittest.defaultTestLoader.discover(args.start, pattern=args.pattern,
                                                        top_level_dir=wurzel)
        except ImportError as exc:
            suite = unittest.TestSuite([_load_error(args.start, exc)])
        stdout, stderr = sys.stdout, sys.stderr
        sys.stdout = sys.stderr = io.StringIO()  # Testausgaben nicht mit dem Bericht mischen
        try:
            suite.run(ergebnis)
        finally:
            gefangen = sys.stdout.getvalue()
            sys.stdout, sys.stderr = stdout, stderr
        if gefangen:
            sys.stderr.write(gefangen[-4000:])
    cases = _merge(ergebnis.cases)
    xml = _junit(cases, time.monotonic() - start)
    ziel = os.path.dirname(os.path.abspath(args.junit))
    os.makedirs(ziel, exist_ok=True)
    ET.ElementTree(xml).write(args.junit, encoding="utf-8", xml_declaration=True)

    rot = [c for c in cases if c["status"] in ("failure", "error")]
    gruen = sum(1 for c in cases if c["status"] == "passed")
    print(f"{len(cases)} Tests: {gruen} grün, {len(rot)} rot, "
          f"{len(cases) - gruen - len(rot)} übersprungen")
    for c in rot:
        print(f"  {c['status'].upper()}: {c['test'].id()}")
    return 0 if cases and not rot else 1


def _load_error(start: str, exc: Exception) -> unittest.TestCase:
    text = "".join(traceback.format_exception(exc))

    class LoadError(unittest.TestCase):
        def test_discovery(self) -> None:
            raise ImportError(f"Discovery in {start} gescheitert:\n{text}")

    return LoadError("test_discovery")


if __name__ == "__main__":
    sys.exit(main())
