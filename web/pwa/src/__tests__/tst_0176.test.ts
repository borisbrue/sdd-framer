// TST-0176 – Hub API Client: fetchHubHealth, fetchHubProjects, postHubAction
// Contracts: CON-0147, CON-0149 | Spec: SPEC-0040

import { fetchHubHealth, fetchHubProjects, postHubAction } from "../api.ts";

const HUB = "http://hub.test:4711";

function assertOk(v: unknown, msg: string): void {
  if (!v) throw new Error(msg);
}
function assertEq(a: unknown, b: unknown, msg?: string): void {
  if (a !== b) throw new Error(msg ?? `Expected ${JSON.stringify(a)} === ${JSON.stringify(b)}`);
}

function makeResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

// ── fetchHubHealth (CON-0149) ─────────────────────────────────────────────────

Deno.test("fetchHubHealth: 200 ok → true", async () => {
  globalThis.fetch = async () => makeResponse({ status: "ok", timestamp: "2026-06-09T00:00:00Z" });
  assertEq(await fetchHubHealth(HUB), true);
});

Deno.test("fetchHubHealth: 200 degraded → true (Hub teilweise erreichbar gilt als online)", async () => {
  globalThis.fetch = async () => makeResponse({ status: "degraded", timestamp: "2026-06-09T00:00:00Z" });
  assertEq(await fetchHubHealth(HUB), true);
});

Deno.test("fetchHubHealth: 503 → false", async () => {
  globalThis.fetch = async () => makeResponse({}, 503);
  assertEq(await fetchHubHealth(HUB), false);
});

Deno.test("fetchHubHealth: Netzwerkfehler → false (kein throw)", async () => {
  globalThis.fetch = async () => { throw new TypeError("Failed to fetch"); };
  assertEq(await fetchHubHealth(HUB), false);
});

Deno.test("fetchHubHealth: Timeout → false (kein throw)", async () => {
  globalThis.fetch = async () => { throw new DOMException("signal timed out", "TimeoutError"); };
  assertEq(await fetchHubHealth(HUB), false);
});

Deno.test("fetchHubHealth: 200 aber kein status-Feld → false", async () => {
  globalThis.fetch = async () => makeResponse({ version: "1.0" });
  assertEq(await fetchHubHealth(HUB), false);
});

Deno.test("fetchHubHealth: 200 unbekannter status → false", async () => {
  globalThis.fetch = async () => makeResponse({ status: "unknown", timestamp: "2026-06-09T00:00:00Z" });
  assertEq(await fetchHubHealth(HUB), false);
});

Deno.test("fetchHubHealth: ruft GET /health auf", async () => {
  let capturedUrl = "";
  globalThis.fetch = async (url: string | URL | Request) => {
    capturedUrl = typeof url === "string" ? url : url instanceof URL ? url.href : (url as Request).url;
    return makeResponse({ status: "ok", timestamp: "2026-06-09T00:00:00Z" });
  };
  await fetchHubHealth(HUB);
  assertEq(capturedUrl, `${HUB}/health`);
});

// ── fetchHubProjects (CON-0147, CON-0148) ────────────────────────────────────

Deno.test("fetchHubProjects: liefert Projektliste und retrievedAt", async () => {
  const list = {
    projects: [{ id: "p1", name: "Web", status: "running", updatedAt: "2026-06-09T00:00:00Z" }],
    retrievedAt: "2026-06-09T10:00:00Z",
  };
  globalThis.fetch = async () => makeResponse(list);
  const result = await fetchHubProjects(HUB);
  assertEq(result.projects.length, 1);
  assertEq(result.projects[0].id, "p1");
  assertEq(result.projects[0].status, "running");
  assertEq(result.retrievedAt, "2026-06-09T10:00:00Z");
});

Deno.test("fetchHubProjects: leere Liste → projects ist leer, retrievedAt vorhanden", async () => {
  globalThis.fetch = async () => makeResponse({ projects: [], retrievedAt: "2026-06-09T10:00:00Z" });
  const result = await fetchHubProjects(HUB);
  assertEq(result.projects.length, 0);
  assertOk(typeof result.retrievedAt === "string", "retrievedAt fehlt");
});

Deno.test("fetchHubProjects: ruft GET /projects auf", async () => {
  let capturedUrl = "";
  globalThis.fetch = async (url: string | URL | Request) => {
    capturedUrl = typeof url === "string" ? url : url instanceof URL ? url.href : (url as Request).url;
    return makeResponse({ projects: [], retrievedAt: "2026-06-09T10:00:00Z" });
  };
  await fetchHubProjects(HUB);
  assertEq(capturedUrl, `${HUB}/projects`);
});

Deno.test("fetchHubProjects: non-200 wirft Fehler", async () => {
  globalThis.fetch = async () => makeResponse({}, 503);
  let thrown = false;
  try { await fetchHubProjects(HUB); } catch { thrown = true; }
  assertOk(thrown, "fetchHubProjects hätte bei 503 werfen sollen");
});

// ── postHubAction (CON-0147) ─────────────────────────────────────────────────

Deno.test("postHubAction start: sendet POST an /projects/{id}/start", async () => {
  let capturedUrl = "";
  let capturedMethod = "";
  globalThis.fetch = async (url: string | URL | Request, init?: RequestInit) => {
    capturedUrl = typeof url === "string" ? url : url instanceof URL ? url.href : (url as Request).url;
    capturedMethod = (init?.method ?? "GET").toUpperCase();
    return makeResponse({}, 202);
  };
  await postHubAction(HUB, "proj-01", "start");
  assertEq(capturedUrl, `${HUB}/projects/proj-01/start`);
  assertEq(capturedMethod, "POST");
});

Deno.test("postHubAction stop: sendet POST an /projects/{id}/stop", async () => {
  let capturedUrl = "";
  globalThis.fetch = async (url: string | URL | Request) => {
    capturedUrl = typeof url === "string" ? url : url instanceof URL ? url.href : (url as Request).url;
    return makeResponse({}, 202);
  };
  await postHubAction(HUB, "proj-02", "stop");
  assertEq(capturedUrl, `${HUB}/projects/proj-02/stop`);
});

Deno.test("postHubAction: wirft bei 404", async () => {
  globalThis.fetch = async () => makeResponse({}, 404);
  let thrown = false;
  try { await postHubAction(HUB, "proj-01", "start"); } catch { thrown = true; }
  assertOk(thrown, "postHubAction hätte bei 404 werfen sollen");
});

Deno.test("postHubAction: wirft bei 409 (falscher Ausgangsstatus, EC-05)", async () => {
  globalThis.fetch = async () => makeResponse({}, 409);
  let thrown = false;
  try { await postHubAction(HUB, "proj-01", "start"); } catch { thrown = true; }
  assertOk(thrown, "postHubAction hätte bei 409 werfen sollen");
});

Deno.test("postHubAction: wirft bei Netzwerkfehler", async () => {
  globalThis.fetch = async () => { throw new TypeError("Failed to fetch"); };
  let thrown = false;
  try { await postHubAction(HUB, "proj-01", "start"); } catch { thrown = true; }
  assertOk(thrown, "postHubAction hätte bei Netzwerkfehler werfen sollen");
});
