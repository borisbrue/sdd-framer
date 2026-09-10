"""AutopilotStateMachine für SPEC-0037 — vollautonomer Implementierungs-Autopilot.

State Pattern (CON-0133): idle → decomposing → implementing → testing → reviewing
  → finalizing → done, plus fix_loop und escalated als Fehlerzustände.
"""
from __future__ import annotations

import asyncio
import logging
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

logger = logging.getLogger(__name__)

AutopilotPhase = Literal[
    "idle", "decomposing", "implementing", "testing",
    "reviewing", "finalizing", "done", "fix_loop", "escalated",
]


@dataclass
class AutopilotConfig:
    max_fix_iterations: int = 3
    review_model: str = "claude-sonnet-4-6"
    test_timeout_seconds: int = 300
    progress_check: bool = True
    notify_on_escalation: bool = True
    automated_gate_approval: bool = False

    @classmethod
    def from_dict(cls, d: dict) -> AutopilotConfig:
        return cls(
            max_fix_iterations=int(d.get("max_fix_iterations", 3)),
            review_model=str(d.get("review_model", "claude-sonnet-4-6")),
            test_timeout_seconds=int(d.get("test_timeout_seconds", 300)),
            progress_check=bool(d.get("progress_check", True)),
            notify_on_escalation=bool(d.get("notify_on_escalation", True)),
            automated_gate_approval=bool(d.get("automated_gate_approval", False)),
        )

    @classmethod
    def from_sdd_config(cls, config) -> AutopilotConfig:
        return cls.from_dict(config.raw.get("autopilot", {}))


@dataclass
class GateResult:
    passed: bool
    findings: list[str] = field(default_factory=list)
    phase: str = ""


@dataclass
class AutopilotReport:
    spec_id: str
    final_phase: AutopilotPhase = "idle"
    iterations: int = 0
    escalation_reason: str = ""
    transitions: list[dict] = field(default_factory=list)

    def record(self, phase: AutopilotPhase, gate_result: str = "ok", details: str = "") -> None:
        self.transitions.append({
            "phase": phase,
            "gate_result": gate_result,
            "iteration": self.iterations,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": details,
        })
        self.final_phase = phase


class AutopilotStateMachine:
    """Deterministischer Autopilot-Zyklus (CON-0133, FR-06–FR-12).

    Alle CLI-Aufrufe erfolgen via _run_sdd(). Für Tests injizierbar.
    """

    def __init__(
        self,
        spec_id: str,
        config: AutopilotConfig,
        *,
        on_phase: Callable[[AutopilotPhase, str], None] | None = None,
        on_escalation: Callable[[str, int, str], None] | None = None,
        _sdd_runner: Callable[..., tuple[int, str]] | None = None,
    ) -> None:
        self.spec_id = spec_id
        self.config = config
        self._on_phase = on_phase or (lambda phase, detail: None)
        self._on_escalation = on_escalation or (lambda reason, iteration, phase: None)
        self._run_sdd = _sdd_runner or self._default_sdd_runner
        self._report = AutopilotReport(spec_id=spec_id)
        self._phase: AutopilotPhase = "idle"
        # Tracks failed test IDs between iterations for progress check
        self._prev_failed_tests: set[str] = set()
        self._prev_review_findings: set[str] = set()

    # ─── Public API ──────────────────────────────────────────────────────────

    def run(self) -> AutopilotReport:
        """Synchroner Einstiegspunkt. Blockiert bis done oder escalated."""
        self._transition("decomposing")
        self._phase_decompose()
        return self._report

    async def run_async(self) -> AutopilotReport:
        """Async-Wrapper für FastAPI-Background-Tasks."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.run)

    def receive_escalation_response(self, action: Literal["retry", "skip", "abort"]) -> None:
        """Nutzer-Entscheidung aus WebUI oder Terminal (FR-10)."""
        if action == "retry":
            self._report.record("fix_loop", "user_retry")
            self._phase = "fix_loop"
            self._phase_fix_loop(reset_counter=True)
        elif action == "skip":
            self._report.record("implementing", "user_skip")
            self._phase = "implementing"
            self._phase_implement()
        else:
            self._report.record("idle", "user_abort")
            self._phase = "idle"

    # ─── Phase implementations ───────────────────────────────────────────────

    def _phase_decompose(self) -> None:
        rc, out = self._run_sdd("decompose", self.spec_id, "--yes")
        if rc != 0:
            self._escalate(f"sdd decompose failed: {out}", "decomposing")
            return
        self._transition("implementing", out[:200])
        self._phase_implement()

    def _phase_implement(self) -> None:
        rc, out = self._run_sdd("implement", self.spec_id)
        if rc != 0:
            self._transition("fix_loop", out[:200])
            self._phase_fix_loop()
            return
        self._transition("testing")
        self._phase_test()

    def _phase_test(self) -> GateResult:
        rc, out = self._run_sdd(
            "test", self.spec_id,
            timeout=self.config.test_timeout_seconds,
        )
        failed = self._parse_failed_tests(out)
        gate = GateResult(passed=(rc == 0), findings=list(failed), phase="testing")
        if gate.passed:
            self._transition("reviewing")
            self._phase_review()
        else:
            self._transition("fix_loop", f"tests failed: {len(failed)}")
            self._phase_fix_loop(failed_tests=failed)
        return gate

    def _phase_review(self) -> GateResult:
        rc, out = self._run_sdd("review", self.spec_id, "--auto")
        approved = rc == 0 and "approved" in out.lower()
        findings = self._parse_review_findings(out)
        gate = GateResult(passed=approved, findings=findings, phase="reviewing")
        if gate.passed:
            if self.config.automated_gate_approval:
                self._run_sdd("spec", "approve", self.spec_id)
            self._transition("finalizing")
            self._phase_finalize()
        else:
            self._transition("fix_loop", f"review rejected: {len(findings)} findings")
            self._phase_fix_loop(review_findings=set(findings))
        return gate

    def _phase_finalize(self) -> None:
        rc, out = self._run_sdd("finalize", self.spec_id)
        if rc != 0:
            self._escalate(f"sdd finalize failed: {out}", "finalizing")
            return
        self._transition("done")
        self._report.record("done", "ok")
        self._log_token_history("done", "ok")

    def _phase_fix_loop(
        self,
        failed_tests: set[str] | None = None,
        review_findings: set[str] | None = None,
        reset_counter: bool = False,
    ) -> None:
        if reset_counter:
            self._report.iterations = 0

        self._report.iterations += 1
        iter_count = self._report.iterations

        # Fortschritts-Check (FR-09): kein Fortschritt → eskalierten auch vor max
        if self.config.progress_check and iter_count > 1:
            no_progress = self._no_progress(failed_tests, review_findings)
            if no_progress:
                self._escalate("No progress detected across iterations", "fix_loop")
                return

        if iter_count > self.config.max_fix_iterations:
            self._escalate(
                f"max_fix_iterations ({self.config.max_fix_iterations}) reached",
                "fix_loop",
            )
            return

        # Update tracking state
        if failed_tests is not None:
            self._prev_failed_tests = failed_tests
        if review_findings is not None:
            self._prev_review_findings = review_findings

        self._log_token_history("fix_loop", f"iteration_{iter_count}")
        self._transition("implementing", f"fix iteration {iter_count}")
        self._phase_implement()

    # ─── Helpers ─────────────────────────────────────────────────────────────

    def _transition(self, phase: AutopilotPhase, details: str = "") -> None:
        self._phase = phase
        self._report.record(phase, "ok", details)
        self._on_phase(phase, details)
        logger.info("[Autopilot] %s → %s %s", self.spec_id, phase, details)

    def _escalate(self, reason: str, phase: AutopilotPhase) -> None:
        self._phase = "escalated"
        self._report.escalation_reason = reason
        self._report.record("escalated", "escalated", reason)
        self._log_token_history("escalated", reason[:100])
        self._on_escalation(reason, self._report.iterations, phase)
        logger.warning("[Autopilot] %s ESCALATED: %s", self.spec_id, reason)
        if not self.config.notify_on_escalation:
            return
        # Terminal-Fallback wenn kein async-Kontext (FR-10)
        self._terminal_prompt()

    def _terminal_prompt(self) -> None:
        try:
            print(
                f"\n⚠ Autopilot eskaliert ({self.spec_id}): {self._report.escalation_reason}\n"
                f"Aktion wählen: [r]etry / [s]kip / [a]bort ",
                end="", flush=True,
            )
            choice = input().strip().lower()[:1]
            action_map: dict[str, Literal["retry", "skip", "abort"]] = {"r": "retry", "s": "skip", "a": "abort"}
            self.receive_escalation_response(action_map.get(choice, "abort"))
        except (EOFError, OSError):
            pass  # Kein Terminal verfügbar — WebUI übernimmt

    def _no_progress(
        self,
        current_tests: set[str] | None,
        current_findings: set[str] | None,
    ) -> bool:
        if (current_tests is not None and self._prev_failed_tests
                and current_tests < self._prev_failed_tests):
            return False  # mindestens ein Test jetzt grün
        # False, wenn mindestens ein Finding behoben ist
        return not (current_findings is not None and self._prev_review_findings
                    and len(current_findings) < len(self._prev_review_findings))

    def _log_token_history(self, phase: str, gate_result: str) -> None:
        try:
            from .token_history import append_autopilot_event  # optional
            append_autopilot_event(
                spec_id=self.spec_id,
                phase=phase,
                gate_result=gate_result,
                iteration=self._report.iterations,
            )
        except Exception:
            pass  # token-history ist optional

    @staticmethod
    def _parse_failed_tests(output: str) -> set[str]:
        """Extrahiert FAILED test_ids aus pytest-Output."""
        failed: set[str] = set()
        for line in output.splitlines():
            if line.startswith("FAILED "):
                failed.add(line.split()[1])
        return failed

    @staticmethod
    def _parse_review_findings(output: str) -> list[str]:
        findings: list[str] = []
        for line in output.splitlines():
            if line.strip().startswith("- ") or "finding" in line.lower():
                findings.append(line.strip())
        return findings

    @staticmethod
    def _default_sdd_runner(*args: str, timeout: int = 120) -> tuple[int, str]:
        cmd = ["sdd", *args]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result.returncode, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return 1, f"Timeout after {timeout}s"
        except FileNotFoundError:
            return 1, "sdd CLI not found"
