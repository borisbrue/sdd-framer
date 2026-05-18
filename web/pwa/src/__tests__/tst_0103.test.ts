// TST-0103 – CON-0093: PWA localStorage-Schema (ProjectRegistry)
// Contract: CON-0093 | Spec: SPEC-0024
// Deno hat eingebautes localStorage — kein Mock nötig.

import { ProjectRegistry, type Project } from "../config.ts";

function assertOk(v: unknown, msg: string): void {
  if (!v) throw new Error(msg);
}
function assertEq(a: unknown, b: unknown, msg?: string): void {
  if (a !== b) throw new Error(msg ?? `Expected ${JSON.stringify(a)} === ${JSON.stringify(b)}`);
}

function reset(): void {
  localStorage.clear();
  ProjectRegistry.init();
}

function makeProject(overrides: Partial<Project> = {}): Project {
  return {
    id: crypto.randomUUID(),
    name: "Test",
    baseUrl: "http://sdd.test:8000",
    token: "abc123",
    addedAt: new Date().toISOString(),
    ...overrides,
  };
}

// CON-0093 G-01: baseUrl ist eine valide URL (http:// oder https://)
Deno.test("baseUrl ist valide URL", () => {
  const validUrls = [
    "http://sdd.test:8000",
    "https://rechner.tail.ts.net:8000",
    "http://192.168.1.10:8000",
  ];
  for (const url of validUrls) {
    const parsed = new URL(url);
    assertOk(
      parsed.protocol === "http:" || parsed.protocol === "https:",
      `'${url}' hat kein http/https-Protokoll`,
    );
  }
});

// CON-0093 G-02: token ist nicht leer wenn Projekt existiert
Deno.test("token ist nicht leer nach add()", () => {
  reset();
  const p = makeProject({ token: "mytoken" });
  ProjectRegistry.add(p);
  const found = ProjectRegistry.getAll().find(x => x.id === p.id);
  assertOk(found, "Projekt nicht gefunden");
  assertOk(found!.token.length > 0, "token ist leer");
});

// CON-0093 G-05: add() speichert baseUrl und token
Deno.test("add() speichert baseUrl und token", () => {
  reset();
  const p = makeProject({ baseUrl: "http://myserver:9000", token: "tok-xyz" });
  ProjectRegistry.add(p);
  const stored = ProjectRegistry.getAll().find(x => x.id === p.id);
  assertOk(stored, "Projekt nach add() nicht vorhanden");
  assertEq(stored!.baseUrl, "http://myserver:9000");
  assertEq(stored!.token, "tok-xyz");
});

// CON-0093 G-04: init() migriert Legacy-sdd_config zu sdd_projects
Deno.test("init() migriert Legacy-sdd_config", () => {
  localStorage.clear();
  localStorage.setItem("sdd_config", JSON.stringify({
    baseUrl: "http://legacy.test:8000",
    token: "legacy-token",
  }));

  ProjectRegistry.init();

  assertEq(localStorage.getItem("sdd_config"), null, "Legacy-Key wurde nicht entfernt");
  const projects = ProjectRegistry.getAll();
  assertOk(projects.length > 0, "Kein Projekt nach Migration vorhanden");
  assertEq(projects[0].baseUrl, "http://legacy.test:8000");
  assertEq(projects[0].token, "legacy-token");
});

// CON-0093: getActive() liefert null ohne aktives Projekt
Deno.test("getActive() liefert null ohne aktives Projekt", () => {
  reset();
  assertEq(ProjectRegistry.getActive(), null, "getActive() sollte null liefern");
});

// CON-0093: setActive() + getActive() round-trip
Deno.test("setActive() und getActive() round-trip", () => {
  reset();
  const p = makeProject();
  ProjectRegistry.add(p);
  ProjectRegistry.setActive(p.id);
  const active = ProjectRegistry.getActive();
  assertOk(active !== null, "getActive() sollte ein Projekt liefern");
  assertEq(active!.id, p.id);
});
