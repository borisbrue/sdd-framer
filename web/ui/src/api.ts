const BASE = "/api";

async function req<T>(method: string, path: string, body?: unknown): Promise<T> {
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
  getStatus:       () => req<Status>("GET", "/status"),
  getSpecs:        () => req<Spec[]>("GET", "/specs"),
  getSpec:         (id: string) => req<SpecDetail>("GET", `/specs/${id}`),
  createSpec:      (b: CreateSpec) => req<{id: string; file: string}>("POST", "/specs", b),
  updateSpec:      (specId: string, body: string) => req<SpecDetail>("PUT", `/specs/${specId}`, { body }),
  patchSpecStatus: (specId: string, status: string) =>
                     req<{ok: boolean; status: string}>("PATCH", `/specs/${specId}/status`, { status }),
  approveSpec:     (specId: string) =>
                     req<{approved: boolean; status: string; checks: GateCheck[]}>("POST", `/specs/${specId}/approve`),
  getContracts:    () => req<Contract[]>("GET", "/contracts"),
  getContract:     (id: string) => req<ContractDetail>("GET", `/contracts/${id}`),
  createContract:  (b: CreateContract) => req<{id: string; file: string}>("POST", "/contracts", b),
  patchContractStatus: (contractId: string, status: string) =>
                         req<{ok: boolean; status: string}>("PATCH", `/contracts/${contractId}/status`, { status }),
  getTests:        () => req<Test[]>("GET", "/tests"),
  getTest:         (id: string) => req<TestDetail>("GET", `/tests/${id}`),
  createTest:      (b: CreateTest) => req<{id: string; file: string}>("POST", "/tests", b),
  validate:        () => req<ValidationResult>("POST", "/validate"),
  trace:           () => req<{ok: boolean; file: string}>("POST", "/trace"),
  maintenance:     () => req<MaintenanceReport>("GET", "/maintenance"),
  getFormats:      () => req<string[]>("GET", "/formats"),
  openInEditor:    (abs_file: string, line?: number) =>
                     req<{ok: boolean}>("POST", "/open", { abs_file, line: line ?? 1 }),
  aiGenerateSpec:     (b: AiGenerateSpec)      => req<AiResponse>("POST", "/ai/generate-spec", b),
  aiImproveSpec:      (b: AiImproveSpec)       => req<AiResponse>("POST", "/ai/improve-spec", b),
  aiSuggestContracts: (b: AiSuggestContracts)  => req<AiResponse>("POST", "/ai/suggest-contracts", b),
  aiUsage:            ()                        => req<AiUsage>("GET", "/ai/usage"),
  copilotGenerateSpec:     (b: AiGenerateSpec)     => req<AiResponse>("POST", "/copilot/generate-spec", b),
  copilotImproveSpec:      (b: AiImproveSpec)      => req<AiResponse>("POST", "/copilot/improve-spec", b),
  copilotSuggestContracts: (b: AiSuggestContracts) => req<AiResponse>("POST", "/copilot/suggest-contracts", b),
  analyzeDoc: (docId: string, b: AnalyzeRequest) => req<AnalyzeResponse>("PUT", `/docs/${docId}/analyze`, b),
  analyzeStart: (docId: string, b: AsyncAnalyzeRequest) =>
    req<{ job_id: string; status: string }>("POST", `/docs/${docId}/analyze/start`, b),
  analyzeStatus: (docId: string, jobId: string) =>
    req<AsyncAnalyzeStatus>("GET", `/docs/${docId}/analyze/status/${jobId}`),
  listAnalyses: (docId: string) =>
    req<AnalysisSummary[]>("GET", `/docs/${docId}/analyses`),
  getAnalysis: (docId: string, resultId: string) =>
    req<PersistedAnalysis>("GET", `/docs/${docId}/analyses/${resultId}`),
  dismissItem: (docId: string, resultId: string, itemId: string, dismissed: boolean) =>
    req<{ dismissed_ids: string[] }>("PATCH", `/docs/${docId}/analyses/${resultId}/dismiss`, { item_id: itemId, dismissed }),
  patchContractBody: (contractId: string, body: string) =>
    req<{ ok: boolean }>("PATCH", `/contracts/${contractId}/body`, { body }),
  fetchFixHint: (docId: string, questionText: string, section: string, content: string) =>
    req<{ suggested_fix: string }>("POST", `/docs/${docId}/analyze/fix-hint`, {
      content, question_text: questionText, section,
    }),
  getHoldouts:         (specId: string) => req<{holdouts: Holdout[]}>( "GET", `/specs/${specId}/holdouts`),
  getHoldout:          (holId: string) => req<Holdout & {spec: string}>( "GET", `/holdouts/${holId}`),
  saveHoldout:         (specId: string, holId: string, body: string) =>
                         req<{ok: boolean}>("PUT", `/specs/${specId}/holdouts/${holId}`, { body }),
  patchHoldoutStatus:  (specId: string, holId: string, status: string) =>
                         req<{ok: boolean; status: string}>("PATCH", `/specs/${specId}/holdouts/${holId}/status`, { status }),
  getTestResults:      (specId: string) => req<RunReport>("GET", `/specs/${specId}/test-results`),
  triggerTestRun:      (specId: string) => req<RunReport>("POST", `/specs/${specId}/test-run`),
  orchestrate:         (b: OrchestrateRequest) => req<{run_id: string}>("POST", "/orchestrate", b),
  getPipelineRun:      (runId: string) => req<PipelineRunState>("GET", `/pipeline/${runId}`),
  getActivePipeline:   (specId: string) => req<PipelineRunState>("GET", `/pipeline/active?spec_id=${specId}`),
  abortPipeline: (runId: string) => req<{aborted: boolean; run_id: string}>("POST", `/pipeline/${runId}/abort`),
  // SPEC-0025: Server-Info und QR-Payload
  serverInfo:       () => req<ServerInfo>("GET", "/server-info"),
  qrPayload:        () => req<QrPayload>("GET", "/auth/qr-payload"),
  generateToken:    () => req<{ok: boolean}>("POST", "/auth/generate-token"),

  getConfig:        () => req<ConfigData>("GET", "/config"),
  saveConfigRaw:    (yaml: string) => req<{ok: boolean}>("PUT", "/config", { yaml }),
  patchConfig:      (fields: ConfigPatch) => req<{ok: boolean}>("PATCH", "/config", fields),
  streamPipelineLog: (
    runId: string,
    onLine: (line: string) => void,
    onDone: () => void,
  ): EventSource => {
    const es = new EventSource(`${BASE}/pipeline/${runId}/log`);
    es.onmessage = (e) => onLine(e.data as string);
    es.addEventListener("done", () => { es.close(); onDone(); });
    es.onerror = () => { es.close(); onDone(); };
    return es;
  },
};

export interface AnalyzeRequest {
  content: string;
  doc_type: "spec" | "contract";
  session_id?: string | null;
  answered_questions?: { id: string; answer: string }[];
}

export interface AsyncAnalyzeRequest {
  content: string;
  doc_type: "spec" | "contract";
  dismissed_ids?: string[];
  session_id?: string | null;
}

export interface AsyncAnalyzeStatus {
  status: "queued" | "running" | "complete" | "failed";
  result_id: string | null;
  error?: string | null;
}

export interface AnalysisSummary {
  result_id: string;
  timestamp: string;
  question_count: number;
  issue_count: number;
  dismissed_count: number;
}

export interface PersistedAnalysis {
  result_id: string;
  doc_id: string;
  timestamp: string;
  session_id: string;
  dismissed_ids: string[];
  questions: AnalysisQuestion[];
  issues: AnalysisIssue[];
  suggestions: { text: string; suggested_fix?: string | null }[];
  usage: Record<string, unknown>;
}

export interface AnalysisQuestion {
  id: string;
  section: string;
  text: string;
  severity: "error" | "warning" | "suggestion";
}

export interface AnalysisIssue {
  section: string;
  text: string;
  severity: "error" | "warning";
  suggested_fix?: string | null;
}

export interface AnalyzeResponse {
  session_id: string;
  questions: AnalysisQuestion[];
  issues: AnalysisIssue[];
  suggestions: { text: string }[];
  usage: AiUsageEntry;
}

export interface Status {
  title: string;
  specs: number;
  contracts: number;
  tests: number;
  gaps: number;
  has_claude_cli?: boolean;
  evaluator_base_url?: string;
  project_root?: string;
}

export interface Spec {
  id: string;
  title: string;
  status: string;
  priority: string;
  owner: string;
  contracts: string[];
  tests: string[];
  adrs: string[];
  depends_on: string[];
  tags: string[];
  version: string;
  created: string;
  updated: string;
  file: string;
  abs_file: string;
}

export interface SpecDetail extends Spec {
  body: string;
}

export interface Contract {
  id: string;
  title: string;
  type: string;
  format: string;
  spec: string;
  status: string;
  version: string;
  artifact: string;
  abs_artifact: string;
  tests: string[];
  file: string;
  abs_file: string;
}

export interface ContractDetail extends Contract {
  body: string;
  artifact_content?: string;
}

export interface Test {
  id: string;
  title: string;
  level: string;
  spec: string;
  contract: string;
  status: string;
  version: string;
  framework: string;
  file: string;
  abs_file: string;
}

export interface TestDetail extends Test {
  body: string;
}

export interface Holdout {
  id: string;
  title: string;
  status: string;
  body: string;
  abs_file: string;
  spec?: string;
}

export interface ValidationIssue {
  file: string;
  message: string;
  instruction: string;
}

export interface ValidationResult {
  ok: boolean;
  errors: ValidationIssue[];
  warnings: ValidationIssue[];
}

export interface MaintenanceIssue {
  severity: string;
  spec_id: string;
  file: string;
  message: string;
  action: string;
}

export interface MaintenanceReport {
  stale_after_weeks: number;
  total_issues: number;
  stale_specs: number;
  drift_issues: number;
  issues: MaintenanceIssue[];
}

export interface CreateSpec     { title: string; owner?: string; priority?: string; }
export interface CreateContract { spec_id: string; format: string; title?: string; }
export interface CreateTest     { spec_id: string; contract_id: string; level: string; title?: string; }

export interface AiGenerateSpec    { title: string; description?: string; context?: string; }
export interface AiImproveSpec     { spec_id: string; current_content: string; instructions: string; }
export interface AiSuggestContracts { spec_id: string; spec_content: string; }

export interface AiUsageEntry {
  ts: string; provider: string; operation: string; model: string;
  input_tokens: number; output_tokens: number;
  cache_creation_tokens: number; cache_read_tokens: number;
  cost_usd: number;
}
export interface AiResponse { result: string; usage: AiUsageEntry; }
export interface AiUsage {
  summary: {
    total_calls: number; total_cost_usd: number;
    total_input_tokens: number; total_output_tokens: number;
    total_cache_read_tokens: number; total_cache_creation_tokens: number;
    by_operation: Record<string, { count: number; cost_usd: number }>;
    by_provider: Record<string, { count: number; input_tokens: number; output_tokens: number; cost_usd: number }>;
  };
  records: AiUsageEntry[];
}

export interface OrchestrateRequest {
  spec_id:    string;
  project_id?: string;
  dry_run?:   boolean;
  no_pr?:     boolean;
  base_url?:  string;
}

export type PipelineStatus = "running" | "labeled" | "merged" | "failed" | "dry_run" | "aborted";

export interface PipelineAttempt {
  attempt:        number;
  branch:         string;
  build_passed:   boolean | null;
  eval_pass_rate: number | null;
  pr_url:         string | null;
  error:          string | null;
  explanation:    string;
}

export interface PipelineReport {
  pass_rate:        number;
  pr_url:           string | null;
  issue_url:        string | null;
  failed_scenarios: string[];
  reason:           string | null;
  explanation:      string | null;
}

export interface PipelineRunState {
  run_id:        string;
  spec_id:       string;
  status:        PipelineStatus;
  current_step?: string;
  attempts:      PipelineAttempt[];
  max_attempts?: number;
  issue_url?:    string | null;
  log?:          string[];
  report?:       PipelineReport | null;
}

// SPEC-0025
export interface ServerInfo {
  name: string;
  externalUrl: string;
  tokenHash: string;
}

export interface QrPayload {
  sdd: number;
  name: string;
  url: string;
  token: string;
}

export interface ConfigData {
  yaml:               string;
  title:              string;
  evaluator_base_url: string;
  max_retries:        number;
  spec_lifecycle:     string[];
}

export interface ConfigPatch {
  title?:              string;
  evaluator_base_url?: string;
  max_retries?:        number;
  spec_lifecycle?:     string[];
}

export interface GateCheck {
  name: string;
  passed: boolean;
  message: string;
}

export type TestRunStatus = "passed" | "failed" | "error" | "missing" | "skipped";

export interface TestRunResult {
  test_id: string;
  artifact: string;
  status: TestRunStatus;
  duration_s: number;
  message: string;
}

export interface RunReport {
  spec_id: string;
  runner: string;
  started_at: string;
  duration_s: number;
  exit_code: number;
  tests: TestRunResult[];
  contract_coverage: Record<string, boolean>;
  passed: number;
  failed: number;
  skipped: number;
}
