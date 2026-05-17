export type PipelineStatus = "running" | "labeled" | "merged" | "failed" | "aborted" | "dry_run";

export const TERMINAL_STATUSES: PipelineStatus[] = ["labeled", "merged", "failed", "aborted", "dry_run"];

export interface PipelineReport {
  pass_rate: number;
  pr_url: string | null;
  issue_url: string | null;
  failed_scenarios: string[];
  reason: string | null;
  explanation: string | null;
}

export interface PipelineRunState {
  run_id: string;
  status: PipelineStatus;
  current_step: string;
  attempts: unknown[];
  max_attempts: number;
  report: PipelineReport | null;
  error: string | null;
}

interface OrchestrateResponse {
  run_id: string;
}

export interface OrchestrateOptions {
  dryRun?: boolean;
  noPr?: boolean;
  projectId?: string;
}

export class PipelineClient {
  constructor(private readonly _getBaseUrl: () => string) {}

  async orchestrate(specId: string, opts: OrchestrateOptions = {}): Promise<string> {
    const resp = await fetch(`${this._getBaseUrl()}/api/orchestrate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        spec_id: specId,
        dry_run: opts.dryRun ?? false,
        no_pr: opts.noPr ?? false,
        project_id: opts.projectId ?? null,
      }),
    });
    if (!resp.ok) {
      const err = (await resp.json().catch(() => ({}))) as Record<string, unknown>;
      const detail = String(err.detail ?? `HTTP ${resp.status}`);
      throw Object.assign(new Error(detail), { status: resp.status });
    }
    return ((await resp.json()) as OrchestrateResponse).run_id;
  }

  async getRun(runId: string): Promise<PipelineRunState> {
    const resp = await fetch(`${this._getBaseUrl()}/api/pipeline/${encodeURIComponent(runId)}`);
    if (!resp.ok) {
      throw Object.assign(new Error(`HTTP ${resp.status}`), { status: resp.status });
    }
    return resp.json() as Promise<PipelineRunState>;
  }

  async getActive(specId: string): Promise<{ run_id: string; status: string } | null> {
    const resp = await fetch(
      `${this._getBaseUrl()}/api/pipeline/active?spec_id=${encodeURIComponent(specId)}`
    );
    if (resp.status === 404) {
      return null;
    }
    if (!resp.ok) {
      throw new Error(`HTTP ${resp.status}`);
    }
    return resp.json() as Promise<{ run_id: string; status: string }>;
  }

  async abort(runId: string): Promise<void> {
    const resp = await fetch(
      `${this._getBaseUrl()}/api/pipeline/${encodeURIComponent(runId)}/abort`,
      { method: "POST" }
    );
    if (!resp.ok) {
      throw new Error(`HTTP ${resp.status}`);
    }
  }
}
