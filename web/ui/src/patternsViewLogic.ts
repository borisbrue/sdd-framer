// Reine Anzeige-Logik der Patterns-View (SPEC-0049, FR-06) – ohne DOM, testbar.
import { PatternUsage, PatternCodeLocation } from "./api";

export function isEmpty(patterns: PatternUsage[]): boolean {
  return patterns.length === 0;
}

export function locationLabel(loc: PatternCodeLocation): string {
  return `${loc.file}:${loc.line}`;
}

export function hasLocations(p: PatternUsage): boolean {
  return p.code_locations.length > 0;
}
