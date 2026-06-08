// TST-0177 – Hub-Verbindungsmonitor und Aktionssperre
// Contracts: CON-0149, CON-0150 | Spec: SPEC-0040

import {
  ConnectionMonitor,
  OFFLINE_THRESHOLD,
  canStart,
  canStop,
  isTransitionState,
  optimisticStatus,
  type ServerStatus,
} from "../hubLogic.ts";

function assertOk(v: unknown, msg: string): void {
  if (!v) throw new Error(msg);
}
function assertEq(a: unknown, b: unknown, msg?: string): void {
  if (a !== b) throw new Error(msg ?? `Expected ${JSON.stringify(a)} === ${JSON.stringify(b)}`);
}

// ── ConnectionMonitor (CON-0149, CON-0150, EC-10) ────────────────────────────

Deno.test("ConnectionMonitor: Initialzustand ist 'unknown'", () => {
  const m = new ConnectionMonitor();
  assertEq(m.state, "unknown");
});

Deno.test("ConnectionMonitor: recordSuccess → online", () => {
  const m = new ConnectionMonitor();
  assertEq(m.recordSuccess(), "online");
  assertEq(m.state, "online");
});

Deno.test("ConnectionMonitor: einzelner Fehler → nicht sofort offline (Entprellung, EC-10)", () => {
  const m = new ConnectionMonitor();
  m.recordFailure();
  assertOk(m.state !== "offline", `1 Fehler darf nicht offline auslösen (threshold=${OFFLINE_THRESHOLD})`);
});

Deno.test(`ConnectionMonitor: ${OFFLINE_THRESHOLD} Fehler → offline`, () => {
  const m = new ConnectionMonitor();
  for (let i = 0; i < OFFLINE_THRESHOLD; i++) m.recordFailure();
  assertEq(m.state, "offline");
});

Deno.test("ConnectionMonitor: threshold-1 Fehler → noch nicht offline", () => {
  const m = new ConnectionMonitor();
  for (let i = 0; i < OFFLINE_THRESHOLD - 1; i++) m.recordFailure();
  assertOk(m.state !== "offline", "Unter threshold darf offline nicht ausgelöst werden");
});

Deno.test("ConnectionMonitor: offline → recordSuccess → online (Wiederverbindung, FR-08)", () => {
  const m = new ConnectionMonitor();
  for (let i = 0; i < OFFLINE_THRESHOLD; i++) m.recordFailure();
  assertEq(m.state, "offline");
  assertEq(m.recordSuccess(), "online");
});

Deno.test("ConnectionMonitor: success setzt Fehlerzähler zurück", () => {
  const m = new ConnectionMonitor();
  m.recordFailure(); // 1 Fehler
  m.recordSuccess(); // reset
  m.recordFailure(); // wieder 1 Fehler
  assertOk(m.state !== "offline", "Fehlerzähler hätte nach success zurückgesetzt werden sollen");
});

Deno.test("ConnectionMonitor: mehrfache online/offline-Zyklen stabil", () => {
  const m = new ConnectionMonitor();
  for (let cycle = 0; cycle < 3; cycle++) {
    m.recordSuccess();
    assertEq(m.state, "online");
    for (let i = 0; i < OFFLINE_THRESHOLD; i++) m.recordFailure();
    assertEq(m.state, "offline");
  }
});

// ── canStart / canStop (CON-0150 – Aktionssperre, FR-05) ─────────────────────

Deno.test("canStart: true wenn online, nicht pending, status stopped", () => {
  assertOk(canStart("stopped", true, false), "canStart sollte true sein");
});

Deno.test("canStart: false wenn offline", () => {
  assertOk(!canStart("stopped", false, false), "canStart offline sollte false sein");
});

Deno.test("canStart: false wenn pending (EC-04 – kein Doppelklick)", () => {
  assertOk(!canStart("stopped", true, true), "canStart pending sollte false sein");
});

Deno.test("canStart: false wenn status nicht stopped", () => {
  const nonStoppedStatuses: ServerStatus[] = ["running", "starting", "stopping", "error"];
  for (const s of nonStoppedStatuses) {
    assertOk(!canStart(s, true, false), `canStart(${s}) sollte false sein`);
  }
});

Deno.test("canStop: true wenn online, nicht pending, status running", () => {
  assertOk(canStop("running", true, false), "canStop sollte true sein");
});

Deno.test("canStop: false wenn offline", () => {
  assertOk(!canStop("running", false, false), "canStop offline sollte false sein");
});

Deno.test("canStop: false wenn pending (EC-04)", () => {
  assertOk(!canStop("running", true, true), "canStop pending sollte false sein");
});

Deno.test("canStop: false wenn status nicht running", () => {
  const nonRunningStatuses: ServerStatus[] = ["stopped", "starting", "stopping", "error"];
  for (const s of nonRunningStatuses) {
    assertOk(!canStop(s, true, false), `canStop(${s}) sollte false sein`);
  }
});

// ── optimisticStatus (FR-07) ─────────────────────────────────────────────────

Deno.test("optimisticStatus: start → starting", () => {
  assertEq(optimisticStatus("start"), "starting");
});

Deno.test("optimisticStatus: stop → stopping", () => {
  assertEq(optimisticStatus("stop"), "stopping");
});

// ── isTransitionState (EC-03) ────────────────────────────────────────────────

Deno.test("isTransitionState: starting → true", () => {
  assertOk(isTransitionState("starting"), "starting ist Übergangsstatus");
});

Deno.test("isTransitionState: stopping → true", () => {
  assertOk(isTransitionState("stopping"), "stopping ist Übergangsstatus");
});

Deno.test("isTransitionState: running/stopped/error → false", () => {
  for (const s of ["running", "stopped", "error"] as ServerStatus[]) {
    assertOk(!isTransitionState(s), `${s} ist kein Übergangsstatus`);
  }
});
