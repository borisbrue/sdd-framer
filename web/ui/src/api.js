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
    getStatus: () => req("GET", "/status"),
    getSpecs: () => req("GET", "/specs"),
    getSpec: (id) => req("GET", `/specs/${id}`),
    createSpec: (b) => req("POST", "/specs", b),
    updateSpec: (specId, body) => req("PUT", `/specs/${specId}`, { body }),
    patchSpecStatus: (specId, status) => req("PATCH", `/specs/${specId}/status`, { status }),
    approveSpec: (specId) => req("POST", `/specs/${specId}/approve`),
    getContracts: () => req("GET", "/contracts"),
    getContract: (id) => req("GET", `/contracts/${id}`),
    createContract: (b) => req("POST", "/contracts", b),
    patchContractStatus: (contractId, status) => req("PATCH", `/contracts/${contractId}/status`, { status }),
    getTests: () => req("GET", "/tests"),
    getTest: (id) => req("GET", `/tests/${id}`),
    createTest: (b) => req("POST", "/tests", b),
    validate: () => req("POST", "/validate"),
    trace: () => req("POST", "/trace"),
    maintenance: () => req("GET", "/maintenance"),
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
    analyzeStart: (docId, b) => req("POST", `/docs/${docId}/analyze/start`, b),
    analyzeStatus: (docId, jobId) => req("GET", `/docs/${docId}/analyze/status/${jobId}`),
    listAnalyses: (docId) => req("GET", `/docs/${docId}/analyses`),
    getAnalysis: (docId, resultId) => req("GET", `/docs/${docId}/analyses/${resultId}`),
    dismissItem: (docId, resultId, itemId, dismissed) => req("PATCH", `/docs/${docId}/analyses/${resultId}/dismiss`, { item_id: itemId, dismissed }),
    patchContractBody: (contractId, body) => req("PATCH", `/contracts/${contractId}/body`, { body }),
    fetchFixHint: (docId, questionText, section, content) => req("POST", `/docs/${docId}/analyze/fix-hint`, {
        content, question_text: questionText, section,
    }),
    getHoldouts: (specId) => req("GET", `/specs/${specId}/holdouts`),
    getHoldout: (holId) => req("GET", `/holdouts/${holId}`),
    saveHoldout: (specId, holId, body) => req("PUT", `/specs/${specId}/holdouts/${holId}`, { body }),
    patchHoldoutStatus: (specId, holId, status) => req("PATCH", `/specs/${specId}/holdouts/${holId}/status`, { status }),
    getTestResults: (specId) => req("GET", `/specs/${specId}/test-results`),
    triggerTestRun: (specId) => req("POST", `/specs/${specId}/test-run`),
    orchestrate: (b) => req("POST", "/orchestrate", b),
    getPipelineRun: (runId) => req("GET", `/pipeline/${runId}`),
    getActivePipeline: (specId) => req("GET", `/pipeline/active?spec_id=${specId}`),
    abortPipeline: (runId) => req("POST", `/pipeline/${runId}/abort`),
    // SPEC-0025: Server-Info und QR-Payload
    serverInfo: () => req("GET", "/server-info"),
    qrPayload: () => req("GET", "/auth/qr-payload"),
    generateToken: () => req("POST", "/auth/generate-token"),
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
