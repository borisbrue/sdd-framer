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
