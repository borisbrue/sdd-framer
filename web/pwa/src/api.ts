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
