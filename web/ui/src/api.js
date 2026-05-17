const BASE = "/api";
async function req(method, path, body) {
    const res = await fetch(`${BASE}${path}`, {
        method,
        headers: body ? { "Content-Type": "application/json" } : {},
        body: body ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail ?? res.statusText);
    }
    return res.json();
}
export const api = {
    getProjects: () => req("GET", "/projects"),
    createProject: (b) => req("POST", "/projects", b),
    getStatus: () => req("GET", "/status"),
    getSpecs: () => req("GET", "/specs"),
    getSpec: (id) => req("GET", `/specs/${id}`),
    createSpec: (b) => req("POST", "/specs", b),
    getContracts: () => req("GET", "/contracts"),
    getContract: (id) => req("GET", `/contracts/${id}`),
    createContract: (b) => req("POST", "/contracts", b),
    getTests: () => req("GET", "/tests"),
    getTest: (id) => req("GET", `/tests/${id}`),
    createTest: (b) => req("POST", "/tests", b),
    validate: () => req("POST", "/validate"),
    trace: () => req("POST", "/trace"),
    maintenance: () => req("GET", "/maintenance"),
    setLevel: (project_id, level) => req("PATCH", `/projects/${project_id}/level`, { level }),
    getFormats: () => req("GET", "/formats"),
    openInEditor: (abs_file, line) => req("POST", "/open", { abs_file, line: line ?? 1 }),
    aiGenerateSpec: (b) => req("POST", "/ai/generate-spec", b),
    aiImproveSpec: (b) => req("POST", "/ai/improve-spec", b),
    aiSuggestContracts: (b) => req("POST", "/ai/suggest-contracts", b),
    aiUsage: () => req("GET", "/ai/usage"),
    copilotGenerateSpec: (b) => req("POST", "/copilot/generate-spec", b),
    copilotImproveSpec: (b) => req("POST", "/copilot/improve-spec", b),
    copilotSuggestContracts: (b) => req("POST", "/copilot/suggest-contracts", b),
    analyzeDoc: (docId, b) => req("PUT", `/docs/${docId}/analyze`, b),
    getTestResults: (specId) => req("GET", `/specs/${specId}/test-results`),
    triggerTestRun: (specId) => req("POST", `/specs/${specId}/test-run`),
    orchestrate: (b) => req("POST", "/orchestrate", b),
    getPipelineRun: (runId) => req("GET", `/pipeline/${runId}`),
    getActivePipeline: (specId) => req("GET", `/pipeline/active?spec_id=${specId}`),
    abortPipeline: (runId) => req("POST", `/pipeline/${runId}/abort`),
    getConfig: () => req("GET", "/config"),
    saveConfigRaw: (yaml) => req("PUT", "/config", { yaml }),
    patchConfig: (fields) => req("PATCH", "/config", fields),
    streamPipelineLog: (runId, onLine, onDone) => {
        const es = new EventSource(`${BASE}/pipeline/${runId}/log`);
        es.onmessage = (e) => onLine(e.data);
        es.addEventListener("done", () => { es.close(); onDone(); });
        es.onerror = () => { es.close(); onDone(); };
        return es;
    },
};
