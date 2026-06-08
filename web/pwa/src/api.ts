/**
 * PWA API-Client — spricht mit dem aktiven SDD-Backend.
 * Verwendet den Token aus ProjectRegistry für alle authentifizierten Calls.
 */
import { Project } from "./config";

export interface SddStatus {
  project: string;
  specs: number;
  contracts: number;
  tests: number;
  gaps: number;
}

export interface SddSpec {
  id: string;
  title: string;
  status: string;
  priority: string;
  owner: string;
  tags: string[];
  updated: string;
}

export interface SddSpecDetail extends SddSpec {
  body: string;
  contracts: string[];
  tests: string[];
}

export type TestStatus = "passed" | "failed" | "error" | "missing" | "skipped";

export interface TestResult {
  test_id: string;
  artifact: string;
  status: TestStatus;
  duration_s: number;
  message: string;
}

export interface TestReport {
  spec_id: string;
  runner: string;
  started_at: string;
  duration_s: number;
  exit_code: number;
  tests: TestResult[];
  contract_coverage: Record<string, boolean>;
  passed: number;
  failed: number;
  skipped: number;
}

function buildHeaders(token: string): HeadersInit {
  return { Authorization: `Bearer ${token}` };
}

export async function fetchStatus(project: Project): Promise<SddStatus> {
  const res = await fetch(`${project.baseUrl}/api/status`, {
    headers: buildHeaders(project.token),
  });
  if (!res.ok) throw Object.assign(new Error("status_error"), { status: res.status });
  return res.json();
}

export async function fetchSpecs(project: Project): Promise<SddSpec[]> {
  const res = await fetch(`${project.baseUrl}/api/specs`, {
    headers: buildHeaders(project.token),
  });
  if (!res.ok) throw Object.assign(new Error("specs_error"), { status: res.status });
  return res.json();
}

export async function fetchSpec(project: Project, id: string): Promise<SddSpecDetail> {
  const res = await fetch(`${project.baseUrl}/api/specs/${id}`, {
    headers: buildHeaders(project.token),
  });
  if (!res.ok) throw Object.assign(new Error("spec_error"), { status: res.status });
  return res.json();
}

export async function updateSpec(project: Project, id: string, body: string): Promise<SddSpecDetail> {
  const res = await fetch(`${project.baseUrl}/api/specs/${id}`, {
    method: "PUT",
    headers: { ...buildHeaders(project.token), "Content-Type": "application/json" },
    body: JSON.stringify({ body }),
  });
  if (!res.ok) throw Object.assign(new Error("update_error"), { status: res.status });
  return res.json();
}

export async function getTestResults(project: Project, specId: string): Promise<TestReport> {
  const res = await fetch(`${project.baseUrl}/api/specs/${specId}/test-results`, {
    headers: buildHeaders(project.token),
  });
  if (!res.ok) throw Object.assign(new Error("test_results_error"), { status: res.status });
  return res.json();
}

export interface AiResponse {
  result: string;
  usage: Record<string, unknown>;
}

export async function generateSpec(
  project: Project,
  data: { title: string; description?: string; context?: string },
): Promise<AiResponse> {
  const res = await fetch(`${project.baseUrl}/api/ai/generate-spec`, {
    method: "POST",
    headers: { ...buildHeaders(project.token), "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw Object.assign(new Error("ai_error"), { status: res.status });
  return res.json();
}

export async function improveSpec(
  project: Project,
  specId: string,
  currentContent: string,
  instructions: string,
): Promise<AiResponse> {
  const res = await fetch(`${project.baseUrl}/api/ai/improve-spec`, {
    method: "POST",
    headers: { ...buildHeaders(project.token), "Content-Type": "application/json" },
    body: JSON.stringify({ spec_id: specId, current_content: currentContent, instructions }),
  });
  if (!res.ok) throw Object.assign(new Error("ai_error"), { status: res.status });
  return res.json();
}

export async function createSpec(
  project: Project,
  data: { title: string; owner?: string; priority?: string },
): Promise<SddSpec> {
  const res = await fetch(`${project.baseUrl}/api/specs`, {
    method: "POST",
    headers: { ...buildHeaders(project.token), "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw Object.assign(new Error(err.detail ?? res.statusText), { status: res.status });
  }
  return res.json();
}

// ── Hub API (CON-0147, CON-0149) ──────────────────────────────────────────────

export type { ServerStatus } from "./hubLogic";

export interface HubProject {
  id: string;
  name: string;
  status: string;
  updatedAt?: string;
}

export interface HubProjectList {
  projects: HubProject[];
  retrievedAt: string;
}

export async function fetchHubHealth(hubUrl: string): Promise<boolean> {
  try {
    const res = await fetch(`${hubUrl}/health`, { signal: AbortSignal.timeout(3000) });
    if (!res.ok) return false;
    const body = await res.json().catch(() => null);
    return body && (body.status === "ok" || body.status === "degraded");
  } catch {
    return false;
  }
}

export async function fetchHubProjects(hubUrl: string): Promise<HubProjectList> {
  const res = await fetch(`${hubUrl}/projects`, { signal: AbortSignal.timeout(5000) });
  if (!res.ok) throw new Error(`hub_projects_error:${res.status}`);
  return res.json();
}

export async function postHubAction(
  hubUrl: string,
  projectId: string,
  action: "start" | "stop",
): Promise<void> {
  const res = await fetch(`${hubUrl}/projects/${projectId}/${action}`, {
    method: "POST",
    signal: AbortSignal.timeout(10000),
  });
  if (!res.ok) throw new Error(`hub_action_error:${res.status}`);
}

export async function triggerTestRun(project: Project, specId: string): Promise<TestReport> {
  const res = await fetch(`${project.baseUrl}/api/specs/${specId}/test-run`, {
    method: "POST",
    headers: buildHeaders(project.token),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw Object.assign(new Error(err.detail ?? res.statusText), { status: res.status });
  }
  return res.json();
}
