"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.PipelineClient = exports.TERMINAL_STATUSES = void 0;
exports.TERMINAL_STATUSES = ["labeled", "merged", "failed", "aborted", "dry_run"];
class PipelineClient {
    constructor(_getBaseUrl) {
        this._getBaseUrl = _getBaseUrl;
    }
    async orchestrate(specId, opts = {}) {
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
            const err = (await resp.json().catch(() => ({})));
            const detail = String(err.detail ?? `HTTP ${resp.status}`);
            throw Object.assign(new Error(detail), { status: resp.status });
        }
        return (await resp.json()).run_id;
    }
    async getRun(runId) {
        const resp = await fetch(`${this._getBaseUrl()}/api/pipeline/${encodeURIComponent(runId)}`);
        if (!resp.ok) {
            throw Object.assign(new Error(`HTTP ${resp.status}`), { status: resp.status });
        }
        return resp.json();
    }
    async getActive(specId) {
        const resp = await fetch(`${this._getBaseUrl()}/api/pipeline/active?spec_id=${encodeURIComponent(specId)}`);
        if (resp.status === 404) {
            return null;
        }
        if (!resp.ok) {
            throw new Error(`HTTP ${resp.status}`);
        }
        return resp.json();
    }
    async abort(runId) {
        const resp = await fetch(`${this._getBaseUrl()}/api/pipeline/${encodeURIComponent(runId)}/abort`, { method: "POST" });
        if (!resp.ok) {
            throw new Error(`HTTP ${resp.status}`);
        }
    }
}
exports.PipelineClient = PipelineClient;
//# sourceMappingURL=pipeline.js.map