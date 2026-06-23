// TST-0218 – PatternsView reine Anzeige-Logik (SPEC-0049 FR-06, CON-0184).
// Runner-agnostisch: valides TS + Inline-Assertions (vitest-Setup wäre ein Follow-up).
import { isEmpty, locationLabel, hasLocations } from "../patternsViewLogic";
import { PatternUsage } from "../api";

function assert(cond: boolean, msg: string): void {
  if (!cond) throw new Error("FAIL: " + msg);
}

// Leer-Zustand (FR-06)
assert(isEmpty([]), "leere Liste → isEmpty true");

const withPattern: PatternUsage = {
  pattern_name: "Strategy",
  specs: [{ spec_id: "SPEC-0015", reason: "x" }],
  refactoring_guru_url: null,
  code_locations: [{ file: "tool/sdd_cli/routing.py", line: 3, annotation: "Strategy Pattern" }],
};

assert(!isEmpty([withPattern]), "nicht-leere Liste → isEmpty false");
assert(hasLocations(withPattern), "Pattern mit Fundstelle → hasLocations true");
assert(
  locationLabel(withPattern.code_locations[0]) === "tool/sdd_cli/routing.py:3",
  "locationLabel → file:line",
);

const noLoc: PatternUsage = { ...withPattern, code_locations: [] };
assert(!hasLocations(noLoc), "Pattern ohne Fundstelle → hasLocations false");

export {};
