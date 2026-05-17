import { useEffect, useRef, useState } from "react";
import { api, PipelineAttempt, PipelineRunState, PipelineStatus, Spec } from "../api";

interface Props {
  spec: Spec;
  onStatusChange: () => void;
}

const POLL_INTERVAL = 5000;
const SESSION_KEY = (specId: string) => `sdd-pipeline-${specId}`;
const TERMINAL: PipelineStatus[] = ["labeled", "merged", "failed", "dry_run", "aborted"];

export default function ExecutePanel({ spec, onStatusChange }: Props) {
  const [run, setRun] = useState<PipelineRunState | null>(null);
  const [logLines, setLogLines] = useState<string[]>([]);
  const [showModal, setShowModal] = useState(false);
  const [baseUrl, setBaseUrl] = useState("");
  const [projectId, setProjectId] = useState(spec.project ?? "");
  const [dryRun, setDryRun] = useState(false);
  const [noPr, setNoPr] = useState(false);
  const [hasClaudeCli, setHasClaudeCli] = useState(true);
  const [projectRoot, setProjectRoot] = useState("");
  const [starting, setStarting] = useState(false);
  const [staleResult, setStaleResult] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const esRef = useRef<EventSource | null>(null);
  const logRef = useRef<HTMLDivElement | null>(null);

  // Load status + prefill base_url on mount
  useEffect(() => {
    api.getStatus().then(s => {
      setHasClaudeCli(s.has_claude_cli ?? true);
      setBaseUrl(s.evaluator_base_url ?? "");
      setProjectRoot(s.project_root ?? "");
    }).catch(() => {});
  }, []);

  // Auto-scroll log to bottom on new lines
  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [logLines]);

  // Restore run from sessionStorage or active-run endpoint on mount
  useEffect(() => {
    if (spec.status !== "approved") return;
    const storedId = sessionStorage.getItem(SESSION_KEY(spec.id));
    if (storedId) {
      api.getPipelineRun(storedId)
        .then(r => {
          setRun(r);
          if (!TERMINAL.includes(r.status)) {
            startPolling(storedId);
            startStreaming(storedId);
          } else {
            setLogLines(r.log ?? []);
          }
        })
        .catch(() => {
          // run_id in sessionStorage but API returns 404 (TTL expired or server restart)
          // → show stale banner per spec §4.2 rule 3 and §6
          sessionStorage.removeItem(SESSION_KEY(spec.id));
          setStaleResult(true);
        });
    } else {
      tryActiveRun();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [spec.id]);

  function tryActiveRun() {
    api.getActivePipeline(spec.id)
      .then(r => { setRun(r); startPolling(r.run_id); startStreaming(r.run_id); })
      .catch(() => {});
  }

  function startStreaming(runId: string) {
    if (esRef.current) { esRef.current.close(); esRef.current = null; }
    const es = api.streamPipelineLog(
      runId,
      (line) => setLogLines(prev => [...prev, line]),
      () => { esRef.current = null; },
    );
    esRef.current = es;
  }

  function startPolling(runId: string) {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const r = await api.getPipelineRun(runId);
        setRun(r);
        if (TERMINAL.includes(r.status)) {
          clearInterval(pollRef.current!);
          pollRef.current = null;
          sessionStorage.removeItem(SESSION_KEY(spec.id));
          if (r.log?.length) setLogLines(r.log);
          if (r.status === "labeled" || r.status === "merged") onStatusChange();
        }
      } catch {
        // 404 means run_id expired (TTL) or server restarted → stale banner per spec §4.2 rule 3
        clearInterval(pollRef.current!);
        pollRef.current = null;
        sessionStorage.removeItem(SESSION_KEY(spec.id));
        setRun(null);
        setLogLines([]);
        setStaleResult(true);
      }
    }, POLL_INTERVAL);
  }

  useEffect(() => () => {
    if (pollRef.current) clearInterval(pollRef.current);
    if (esRef.current) { esRef.current.close(); esRef.current = null; }
  }, []);

  async function handleExecute() {
    // Clear any previous state per spec §4.2 rule 2
    sessionStorage.removeItem(SESSION_KEY(spec.id));
    setStaleResult(false);
    setStarting(true);
    try {
      const { run_id } = await api.orchestrate({
        spec_id:    spec.id,
        project_id: projectId || undefined,
        dry_run:    dryRun,
        no_pr:      noPr,
        base_url:   baseUrl || undefined,
      });
      sessionStorage.setItem(SESSION_KEY(spec.id), run_id);
      const initial = await api.getPipelineRun(run_id);
      setRun(initial);
      setLogLines([]);
      setShowModal(false);
      startStreaming(run_id);
      startPolling(run_id);
    } catch (e: unknown) {
      alert(`Execute fehlgeschlagen: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setStarting(false);
    }
  }

  async function handleAbort() {
    if (!run) return;
    try {
      await api.abortPipeline(run.run_id);
    } catch {
      // Ignore — run may have finished between click and request
    }
  }

  if (spec.status !== "approved") return null;

  const isRunning = run?.status === "running";
  const isDone = run && TERMINAL.includes(run.status);

  return (
    <>
      {/* Status-Panel */}
      {run && (
        <div className="card" style={{ borderColor: panelBorder(run.status), marginBottom: 0 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontWeight: 600, marginBottom: 6, display: "flex", alignItems: "center", gap: 10 }}>
                <span>{statusIcon(run.status)} {statusTitle(run, spec.id)}</span>
                {run.status === "running" && (
                  <button
                    style={{ fontSize: 11, padding: "2px 8px", color: "var(--red)", borderColor: "var(--red)" }}
                    onClick={handleAbort}
                  >
                    ⊘ Abbrechen
                  </button>
                )}
              </div>

              {/* Live terminal log */}
              {logLines.length > 0 && (
                <div
                  ref={logRef}
                  style={{
                    background: "#1d2021",
                    color: "#ebdbb2",
                    fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
                    fontSize: 11,
                    lineHeight: 1.55,
                    padding: "8px 12px",
                    borderRadius: 4,
                    height: 220,
                    overflowY: "auto",
                    marginBottom: isDone ? 8 : 0,
                    border: "1px solid #504945",
                  }}
                >
                  {logLines.map((line, i) => (
                    <div key={i} style={{ color: lineColor(line), whiteSpace: "pre-wrap" }}>{line}</div>
                  ))}
                  {!isDone && (
                    <span style={{ color: "var(--accent)", opacity: 0.7 }}>▌</span>
                  )}
                </div>
              )}

              {isDone && <AttemptSummary attempts={run.attempts} status={run.status} issueUrl={run.issue_url} />}
            </div>
            {isDone && (
              <button style={{ fontSize: 12, marginLeft: 8 }} onClick={() => { setRun(null); setLogLines([]); }}>✕</button>
            )}
          </div>
        </div>
      )}

      {/* Stale-Result-Banner (TTL abgelaufen oder Server-Neustart) */}
      {staleResult && (
        <div style={{
          display: "flex", justifyContent: "space-between", alignItems: "center",
          background: "color-mix(in srgb, var(--yellow) 12%, transparent)",
          border: "1px solid var(--yellow)", borderRadius: "var(--radius)",
          padding: "8px 12px", fontSize: 12, color: "var(--yellow)",
        }}>
          <span>Ergebnis nicht mehr verfügbar (Server-Neustart oder Timeout).</span>
          <button style={{ fontSize: 11, padding: "2px 6px" }} onClick={() => setStaleResult(false)}>✕</button>
        </div>
      )}

      {/* Execute-Button */}
      {!isDone && (
        <div style={{ display: "flex", justifyContent: "flex-end" }}>
          <button
            className="primary"
            disabled={isRunning}
            onClick={() => setShowModal(true)}
            style={{ minWidth: 110 }}
          >
            {isRunning ? "⚙ läuft…" : "▶ Execute"}
          </button>
        </div>
      )}

      {/* Modal */}
      {showModal && (
        <div style={modalOverlay} onClick={() => setShowModal(false)}>
          <div style={modalBox} onClick={e => e.stopPropagation()}>
            <h3 style={{ marginBottom: 12 }}>Pipeline starten</h3>
            <div style={{ fontSize: 13, color: "var(--muted)", marginBottom: 16 }}>
              <code style={{ color: "var(--accent)" }}>{spec.id}</code> — {spec.title}
            </div>

            {!hasClaudeCli && (
              <div style={{ background: "color-mix(in srgb, var(--red) 15%, transparent)", border: "1px solid var(--red)", borderRadius: "var(--radius)", padding: "8px 12px", marginBottom: 14, fontSize: 12, color: "var(--red)" }}>
                ⚠ Claude Code CLI nicht gefunden. Stelle sicher, dass <code>claude</code> im PATH installiert und eingeloggt ist.
              </div>
            )}
            {projectRoot && (
              <div style={{ fontSize: 11, color: "var(--muted)", marginBottom: 14 }}>
                Code wird geschrieben nach: <code style={{ color: "var(--text)" }}>{projectRoot}</code>
              </div>
            )}

            <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 16 }}>
              <div>
                <label>Base-URL für Evaluator (leer = kein Evaluator)</label>
                <input value={baseUrl} onChange={e => setBaseUrl(e.target.value)} placeholder="http://localhost:8000" />
              </div>
              <div>
                <label>Project ID (optional)</label>
                <input value={projectId} onChange={e => setProjectId(e.target.value)} placeholder={spec.project ?? ""} />
              </div>
              <label style={{ display: "flex", gap: 8, alignItems: "center", cursor: "pointer", fontSize: 13, color: "var(--text)" }}>
                <input type="checkbox" checked={dryRun} onChange={e => setDryRun(e.target.checked)} />
                Dry-run (kein Git-Commit, kein PR)
              </label>
              <label style={{ display: "flex", gap: 8, alignItems: "center", cursor: "pointer", fontSize: 13, color: "var(--text)" }}>
                <input type="checkbox" checked={noPr} onChange={e => setNoPr(e.target.checked)} />
                Ohne PR erstellen (--no-pr)
              </label>
            </div>

            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
              <button onClick={() => setShowModal(false)}>Abbrechen</button>
              <button className="primary" disabled={starting} onClick={handleExecute}>
                {starting ? "Startet…" : "Execute"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function AttemptSummary({ attempts, status, issueUrl }: {
  attempts: PipelineAttempt[];
  status: PipelineStatus;
  issueUrl?: string | null;
}) {
  const lastPr = [...attempts].reverse().find(a => a.pr_url)?.pr_url;
  const failed = attempts.filter(a => a.error);

  return (
    <div style={{ marginTop: 8, fontSize: 12, display: "flex", flexDirection: "column", gap: 4 }}>
      {lastPr && (
        <span>PR: <a href={lastPr} target="_blank" rel="noreferrer" style={{ color: "var(--accent)" }}>{lastPr}</a></span>
      )}
      {status === "labeled" || status === "merged" ? (
        <span style={{ color: "var(--green)" }}>
          Pass-Rate: {formatRate(attempts)} · {attempts.length} Attempt(s) · Status: implemented
        </span>
      ) : status === "dry_run" ? (
        <span style={{ color: "var(--yellow)" }}>
          Dry-run — {attempts[0]?.explanation ?? "keine Erklärung"}
        </span>
      ) : status === "aborted" ? (
        <span style={{ color: "var(--yellow)" }}>Manuell abgebrochen</span>
      ) : (
        <>
          {failed.map(a => (
            <span key={a.attempt} style={{ color: "var(--red)" }}>
              Attempt {a.attempt}: {a.error?.slice(0, 120)}
            </span>
          ))}
          {issueUrl && (
            <span>Issue: <a href={issueUrl} target="_blank" rel="noreferrer" style={{ color: "var(--red)" }}>{issueUrl}</a></span>
          )}
        </>
      )}
    </div>
  );
}

function lineColor(line: string): string {
  if (line.includes("✓")) return "#b8bb26";
  if (line.includes("✗") || /fehler|error|fail/i.test(line)) return "#fb4934";
  if (/läuft|generiert|attempt|erstellt|committed|PR/i.test(line)) return "#fabd2f";
  return "#ebdbb2";
}

function formatRate(attempts: PipelineAttempt[]) {
  const rates = attempts.map(a => a.eval_pass_rate).filter((r): r is number => r !== null);
  if (!rates.length) return "—";
  return `${Math.round(rates[rates.length - 1] * 100)} %`;
}

function panelBorder(status: PipelineStatus) {
  if (status === "running") return "var(--accent)";
  if (status === "labeled" || status === "merged") return "var(--green)";
  if (status === "dry_run" || status === "aborted") return "var(--yellow)";
  return "var(--red)";
}

function statusIcon(status: PipelineStatus) {
  if (status === "running") return "⚙";
  if (status === "labeled" || status === "merged") return "✓";
  if (status === "dry_run") return "🔍";
  if (status === "aborted") return "⊘";
  return "✗";
}

function statusTitle(run: PipelineRunState, specId: string) {
  if (run.status === "running") {
    const current = run.attempts.length + 1;
    const max = run.max_attempts ?? 3;
    return `Pipeline läuft — ${specId} · Attempt ${current}/${max}`;
  }
  if (run.status === "labeled") return "Implementiert — PR erstellt";
  if (run.status === "merged")  return "Implementiert — PR gemergt";
  if (run.status === "dry_run") return "Dry-run abgeschlossen";
  if (run.status === "aborted") return "Pipeline abgebrochen";
  return `Pipeline fehlgeschlagen — ${run.attempts.length} Attempt(s)`;
}

const modalOverlay: React.CSSProperties = {
  position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)",
  display: "flex", alignItems: "center", justifyContent: "center", zIndex: 100,
};

const modalBox: React.CSSProperties = {
  background: "var(--surface)", border: "1px solid var(--border)",
  borderRadius: "var(--radius)", padding: 24, width: 440, maxWidth: "90vw",
};
