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
