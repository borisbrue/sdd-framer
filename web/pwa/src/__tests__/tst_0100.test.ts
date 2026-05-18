// TST-0100 – CON-0090: PWA ApiClient — Auth-Header + 401-Handler
// Contract: CON-0090 | Spec: SPEC-0024

import { fetchSpecs, fetchStatus } from "../api.ts";

const BASE = "http://sdd.test:8000";
const TOKEN = "test-token-abc";
const PROJECT = { id: "p1", name: "Test", baseUrl: BASE, token: TOKEN, addedAt: "" };

function assertEq(a: unknown, b: unknown, msg?: string): void {
  if (a !== b) throw new Error(msg ?? `Expected ${JSON.stringify(a)} === ${JSON.stringify(b)}`);
}

function makeResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

// CON-0090 G-01: Jeder HTTP-Request enthält Authorization: Bearer <token>
Deno.test("fetchSpecs setzt Authorization: Bearer header", async () => {
  let capturedHeaders: Headers | undefined;
  globalThis.fetch = async (_url: string | URL | Request, init?: RequestInit) => {
    capturedHeaders = new Headers(init?.headers);
    return makeResponse([]);
  };

  await fetchSpecs(PROJECT);

  assertEq(
    capturedHeaders?.get("authorization"),
    `Bearer ${TOKEN}`,
    "Authorization-Header fehlt oder falsch",
  );
});

// CON-0090 G-05: getSpecs() ruft GET /api/specs auf
Deno.test("fetchSpecs ruft /api/specs auf", async () => {
  let capturedUrl = "";
  globalThis.fetch = async (url: string | URL | Request) => {
    capturedUrl = typeof url === "string" ? url : url instanceof URL ? url.href : url.url;
    return makeResponse([]);
  };

  await fetchSpecs(PROJECT);

  assertEq(capturedUrl, `${BASE}/api/specs`);
});

// CON-0090: 401-Antwort wirft mit erkennbarem Fehler
Deno.test("fetchSpecs wirft bei HTTP 401", async () => {
  globalThis.fetch = async () => makeResponse({}, 401);

  let thrown: unknown;
  try {
    await fetchSpecs(PROJECT);
  } catch (e) {
    thrown = e;
  }

  if (!thrown) throw new Error("fetchSpecs hätte werfen sollen");
  const err = thrown as Record<string, unknown>;
  if (err["status"] !== 401 && !String(err["message"]).includes("specs_error")) {
    throw new Error(`Unerwarteter Fehler: ${JSON.stringify(err)}`);
  }
});

// CON-0090 G-08: Netzwerkfehler wirft (kein silentes Scheitern)
Deno.test("fetchSpecs wirft bei Netzwerkfehler", async () => {
  globalThis.fetch = async () => { throw new TypeError("Failed to fetch"); };

  let thrown: unknown;
  try {
    await fetchSpecs(PROJECT);
  } catch (e) {
    thrown = e;
  }

  if (!thrown) throw new Error("fetchSpecs hätte bei Netzwerkfehler werfen sollen");
});
