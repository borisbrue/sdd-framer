"""Ausführung einer Sonde (SPEC-0054 §3 Template Method, CON-0192 INV-09).

Jede Sonde durchläuft dasselbe Gerüst: Befehl rendern → Holdout-Sperre → mit Zeitlimit
ausführen → Ausgabe parsen → Ergebnis oder `n/a` mit Grund. Unterklassen (etwa für
`sdd quality doctor`) überschreiben nur die Dateimenge.
"""
from __future__ import annotations

import shlex
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from .config import Probe
from .parsers import ParseError, ProbeResult, parse_output

HOLDOUT_MARKER = ".sdd/holdout"
NOT_FOUND_CODES = (126, 127)

REASON_NOT_FOUND = "Befehl nicht gefunden"
REASON_TIMEOUT = "Zeitlimit überschritten"
REASON_NO_OUTPUT = "keine Ausgabe"
REASON_UNPARSABLE = "Ausgabe nicht parsebar"
REASON_HOLDOUT = "Holdout-Pfad verboten"


@dataclass
class ProbeOutcome:
    probe: Probe
    status: str
    command: str
    duration_ms: int = 0
    exit_code: int | None = None
    reason: str | None = None
    detail: str | None = None
    tool_version: str | None = None
    result: ProbeResult | None = None

    @property
    def ok(self) -> bool:
        return self.status == "ok"

    def to_dict(self) -> dict:
        d: dict = {"name": self.probe.name, "command": self.command, "format": self.probe.format,
                   "status": self.status, "exit_code": self.exit_code,
                   "duration_ms": self.duration_ms}
        if self.reason:
            d["reason"] = self.reason
        if self.tool_version:
            d["tool_version"] = self.tool_version
        return d


class ProbeRun:
    def __init__(self, root: Path, paths: list[str]) -> None:
        self.root = root
        self.paths = paths

    def paths_for(self, probe: Probe) -> list[str]:
        return self.paths

    def render(self, probe: Probe, out: Path) -> str:
        dateien = " ".join(shlex.quote(p) for p in self.paths_for(probe))
        return probe.command.replace("{paths}", dateien).replace("{out}", shlex.quote(str(out)))

    def execute(self, probe: Probe, keep_output: Path | None = None) -> ProbeOutcome:
        """keep_output: Zielpfad, unter dem die geparste Ausgabe erhalten bleibt."""
        if HOLDOUT_MARKER in probe.command:
            return ProbeOutcome(probe, "n/a", probe.command, reason=REASON_HOLDOUT)
        with tempfile.TemporaryDirectory(prefix="sdd-probe-") as tmp:
            out = Path(tmp) / f"{probe.name}.out"
            start = time.monotonic()
            try:
                proc = subprocess.run(self.render(probe, out), shell=True, cwd=self.root,
                                      capture_output=True, text=True,
                                      timeout=probe.timeout_seconds)
            except subprocess.TimeoutExpired:
                return ProbeOutcome(probe, "n/a", probe.command, _ms(start),
                                    reason=REASON_TIMEOUT)
            outcome = ProbeOutcome(probe, "ok", probe.command, _ms(start), proc.returncode,
                                   tool_version=self._version(probe))
            if proc.returncode in NOT_FOUND_CODES:
                return self._failed(outcome, REASON_NOT_FOUND, proc.stderr)
            if not out.is_file() or out.stat().st_size == 0:
                return self._failed(outcome, REASON_NO_OUTPUT, proc.stderr)
            try:
                outcome.result = parse_output(probe.format, out, self.root,
                                              fr_marker=probe.fr_marker)
            except ParseError as exc:
                return self._failed(outcome, REASON_UNPARSABLE, str(exc))
            if keep_output is not None:
                keep_output.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(out, keep_output)
        return outcome

    @staticmethod
    def _failed(outcome: ProbeOutcome, reason: str, detail: str) -> ProbeOutcome:
        outcome.status, outcome.reason = "n/a", reason
        outcome.detail = (detail or "").strip()[:500] or None
        return outcome

    def _version(self, probe: Probe) -> str | None:
        if not probe.version_command:
            return None
        try:
            proc = subprocess.run(probe.version_command, shell=True, cwd=self.root,
                                  capture_output=True, text=True, timeout=30)
        except subprocess.TimeoutExpired:
            return None
        zeilen = (proc.stdout or proc.stderr).strip().splitlines()
        return zeilen[0] if zeilen else None


def _ms(start: float) -> int:
    return int((time.monotonic() - start) * 1000)
