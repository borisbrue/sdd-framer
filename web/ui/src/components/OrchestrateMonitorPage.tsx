import { useCallback, useEffect, useRef, useState } from "react";
import { api, DagAgent, DagEventData, DagRun, DagTaskStatus } from "../api";

interface TaskState {
  task_id: string;
  status: DagTaskStatus;
  agent: DagAgent;
  model: string;
  title: string;
  start_ms: number | null;
  end_ms: number | null;
}

interface EscalationState {
  run_id: string;
  task_id: string;
  reason: string;
}

const STATUS_COLOR: Record<DagTaskStatus, string> = {
  pending:  "var(--muted)",
  running:  "var(--accent)",
  done:     "var(--green)",
  failed:   "var(--red)",
  paused:   "#f59e0b",
  skipped:  "#4b5563",
};

const RUN_BADGE: Record<string, string> = {
  running: "#1d3557",
  done:    "#14532d",
  failed:  "#450a0a",
};

function elapsedSec(start: number | null, end: number | null): string {
  if (!start) return "—";
  return Math.round(((end ?? Date.now()) - start) / 1000) + "s";
}

function AgentBadge({ agent, model }: { agent: DagAgent; model: string }) {
  if (agent === "none") return <span style={{ color: "var(--muted)" }}>—</span>;
  const color = agent === "local" ? "#60a5fa" : "#a78bfa";
  return (
    <span style={{ color, fontSize: 11 }}>
      {agent.toUpperCase()}{model ? `: ${model.substring(0, 20)}` : ""}
    </span>
  );
}

function StatusDot({ status }: { status: DagTaskStatus }) {
  const anim = status === "running" ? { animation: "pulse 1s infinite" } : {};
  return (
    <span style={{
      display: "inline-block", width: 8, height: 8, borderRadius: "50%",
      background: STATUS_COLOR[status], marginRight: 6, ...anim,
    }} />
  );
}

function DagGraph({ tasks }: { tasks: TaskState[] }) {
  if (!tasks.length) return null;

  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 8, padding: "8px 0" }}>
      {tasks.map(t => (
        <div key={t.task_id} style={{
          background: STATUS_COLOR[t.status] + "22",
          border: `1px solid ${STATUS_COLOR[t.status]}55`,
          borderRadius: 6, padding: "6px 10px", minWidth: 120, maxWidth: 180,
          fontSize: 11,
        }}>
          <div style={{ fontFamily: "monospace", fontSize: 10, color: "var(--muted)", marginBottom: 2 }}>
            {t.task_id.substring(0, 12)}
          </div>
          <div style={{ fontWeight: 600, marginBottom: 4, wordBreak: "break-word" }}>
            {t.title.substring(0, 30)}
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <StatusDot status={t.status} />
            <span style={{ color: STATUS_COLOR[t.status], fontSize: 10, textTransform: "uppercase" }}>
              {t.status}
            </span>
          </div>
          {t.agent !== "none" && (
            <div style={{ marginTop: 3 }}>
              <AgentBadge agent={t.agent} model={t.model} />
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

export default function OrchestrateMonitorPage({ onNavigate }: { onNavigate?: (id: string) => void }) {
  const [runs, setRuns] = useState<DagRun[]>([]);
  const [selectedRun, setSelectedRun] = useState<DagRun | null>(null);
  const [tasks, setTasks] = useState<Record<string, TaskState>>({});
  const [escalation, setEscalation] = useState<EscalationState | null>(null);
  const [cmdError, setCmdError] = useState("");
  const sseRef = useRef<EventSource | null>(null);
  const isMounted = useRef(true);

  useEffect(() => {
    isMounted.current = true;
    return () => { isMounted.current = false; };
  }, []);

  const loadRuns = useCallback(async () => {
    try {
      const data = await api.getOrchestrateRuns();
      if (isMounted.current) setRuns(data);
    } catch { /* no server */ }
  }, []);

  useEffect(() => {
    loadRuns();
    const id = setInterval(loadRuns, 10_000);
    return () => clearInterval(id);
  }, [loadRuns]);

  function selectRun(run: DagRun) {
    if (sseRef.current) { sseRef.current.close(); sseRef.current = null; }
    setSelectedRun(run);
    setTasks({});
    setEscalation(null);
    setCmdError("");

    sseRef.current = api.streamDagEvents(
      run.run_id,
      (ev: DagEventData) => {
        if (!isMounted.current) return;

        // Escalation event detection
        if (ev.status === "failed" && ev.phase !== undefined) {
          setEscalation({ run_id: ev.run_id, task_id: ev.task_id, reason: ev.reason || ev.details || "Unbekannter Fehler" });
        }

        setTasks(prev => {
          const existing = prev[ev.task_id];
          const start_ms = ev.status === "running" && !existing?.start_ms ? Date.now() : (existing?.start_ms ?? null);
          const end_ms = (ev.status === "done" || ev.status === "failed") ? Date.now() : (existing?.end_ms ?? null);
          return {
            ...prev,
            [ev.task_id]: {
              task_id:  ev.task_id,
              status:   ev.status,
              agent:    ev.agent,
              model:    ev.model,
              title:    ev.details || existing?.title || ev.task_id,
              start_ms,
              end_ms,
            },
          };
        });
      },
      () => {
        if (isMounted.current) loadRuns();
      },
    );
  }

  useEffect(() => () => { sseRef.current?.close(); }, []);

  async function sendCmd(taskId: string, commandType: string) {
    if (!selectedRun) return;
    setCmdError("");
    try {
      await api.sendOrchestrateCommand(selectedRun.run_id, commandType, taskId);
    } catch (e: unknown) {
      setCmdError(e instanceof Error ? e.message : String(e));
    }
  }

  async function handleEscalation(action: "retry" | "skip" | "abort") {
    if (!escalation) return;
    const cmdType = action === "retry" ? "restart_task" : action === "skip" ? "skip_task" : "skip_task";
    await sendCmd(escalation.task_id, cmdType);
    setEscalation(null);
  }

  const taskList = Object.values(tasks);

  return (
    <div style={{ display: "flex", height: "100%", gap: 0 }}>
      {/* Sidebar: Run List */}
      <aside style={{ width: 260, minWidth: 200, borderRight: "1px solid var(--border)", overflowY: "auto", padding: 12 }}>
        <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--muted)", marginBottom: 8 }}>
          Runs
        </div>
        {!runs.length && (
          <p style={{ color: "var(--muted)", fontSize: 12 }}>Keine laufenden Runs.</p>
        )}
        {runs.map(run => (
          <div
            key={run.run_id}
            onClick={() => selectRun(run)}
            style={{
              padding: "10px 12px", borderRadius: 6, cursor: "pointer", marginBottom: 4,
              border: `1px solid ${selectedRun?.run_id === run.run_id ? "var(--accent)" : "var(--border)"}`,
              background: selectedRun?.run_id === run.run_id ? "#1e2130" : "transparent",
            }}
          >
            <div style={{ fontWeight: 500, fontSize: 13 }}>{run.spec_id}</div>
            <div style={{ fontSize: 11, color: "var(--muted)", marginTop: 2, display: "flex", gap: 8 }}>
              <span style={{
                padding: "1px 6px", borderRadius: 10, fontSize: 10, fontWeight: 600, textTransform: "uppercase",
                background: (RUN_BADGE[run.status] ?? "#1a1d26") + "bb",
                color: run.status === "running" ? "var(--accent)" : run.status === "done" ? "var(--green)" : "var(--red)",
              }}>
                {run.status}
              </span>
              <span>{new Date(run.started_at * 1000).toLocaleTimeString("de")}</span>
            </div>
          </div>
        ))}
      </aside>

      {/* Main: DAG + Task Table */}
      <main style={{ flex: 1, overflowY: "auto", padding: 20, display: "flex", flexDirection: "column", gap: 16 }}>

        {/* Escalation Banner (FR-10) */}
        {escalation && (
          <div style={{
            background: "#450a0a", border: "1px solid #7f1d1d", borderRadius: 8, padding: 16,
          }}>
            <div style={{ color: "var(--red)", fontWeight: 600, marginBottom: 6 }}>
              ⚠ Autopilot eskaliert
            </div>
            <div style={{ color: "#fca5a5", fontSize: 12, marginBottom: 12 }}>
              {escalation.reason}
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <button onClick={() => handleEscalation("retry")} style={{ padding: "6px 14px", background: "var(--accent)", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer", fontWeight: 600 }}>
                Retry
              </button>
              <button onClick={() => handleEscalation("skip")} style={{ padding: "6px 14px", background: "#374151", color: "var(--text)", border: "none", borderRadius: 6, cursor: "pointer" }}>
                Skip Task
              </button>
              <button onClick={() => handleEscalation("abort")} style={{ padding: "6px 14px", background: "#7f1d1d", color: "var(--red)", border: "none", borderRadius: 6, cursor: "pointer" }}>
                Abort
              </button>
            </div>
          </div>
        )}

        {!selectedRun && (
          <div style={{ color: "var(--muted)", fontSize: 13, textAlign: "center", padding: 40 }}>
            Run in der Sidebar auswählen.
          </div>
        )}

        {selectedRun && (
          <>
            {/* DAG Graph (FR-02, FR-03, FR-05) */}
            <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8, padding: 16 }}>
              <div style={{ display: "flex", alignItems: "center", marginBottom: 12 }}>
                <span style={{ fontWeight: 600, fontSize: 13 }}>DAG · {selectedRun.spec_id}</span>
                {onNavigate && (
                  <button
                    onClick={() => onNavigate(selectedRun.spec_id)}
                    style={{ marginLeft: "auto", fontSize: 11, color: "var(--accent)", background: "none", border: "none", cursor: "pointer", padding: 0 }}
                  >
                    → Kanban-Board
                  </button>
                )}
              </div>
              {!taskList.length
                ? <p style={{ color: "var(--muted)", fontSize: 12 }}>Warte auf Events…</p>
                : <DagGraph tasks={taskList} />
              }
            </div>

            {/* Task Table */}
            <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8, padding: 16 }}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 12 }}>Tasks</div>
              {cmdError && (
                <div style={{ color: "var(--red)", fontSize: 12, marginBottom: 8 }}>{cmdError}</div>
              )}
              {!taskList.length
                ? <p style={{ color: "var(--muted)", fontSize: 12 }}>Keine Tasks empfangen.</p>
                : (
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                    <thead>
                      <tr style={{ borderBottom: "1px solid var(--border)" }}>
                        {["Task", "Status", "Agent", "Dauer", "Aktionen"].map(h => (
                          <th key={h} style={{ textAlign: "left", padding: "6px 10px", fontSize: 11, color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.06em" }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {taskList.map(t => (
                        <tr key={t.task_id} style={{ borderBottom: "1px solid #1e2130" }}>
                          <td style={{ padding: "8px 10px", fontFamily: "monospace" }} title={t.task_id}>
                            {t.title.substring(0, 40)}
                          </td>
                          <td style={{ padding: "8px 10px" }}>
                            <StatusDot status={t.status} />
                            {t.status}
                          </td>
                          <td style={{ padding: "8px 10px" }}>
                            <AgentBadge agent={t.agent} model={t.model} />
                          </td>
                          <td style={{ padding: "8px 10px", fontFamily: "monospace" }}>
                            {elapsedSec(t.start_ms, t.end_ms)}
                          </td>
                          <td style={{ padding: "8px 10px" }}>
                            <TaskActions task={t} onCommand={(cmd) => sendCmd(t.task_id, cmd)} />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )
              }
            </div>
          </>
        )}
      </main>

      <style>{`
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.4} }
      `}</style>
    </div>
  );
}

function TaskActions({ task, onCommand }: { task: TaskState; onCommand: (cmd: string) => void }) {
  function btn(label: string, cmd: string, color?: string) {
    return (
      <button
        key={cmd}
        onClick={() => onCommand(cmd)}
        style={{
          padding: "2px 8px", borderRadius: 4, fontSize: 10, fontWeight: 600, cursor: "pointer",
          border: `1px solid ${color ?? "var(--border)"}`, background: "#1e2130",
          color: color ?? "var(--text)", marginRight: 2,
        }}
      >
        {label}
      </button>
    );
  }

  const btns = [];
  if (task.status === "running") btns.push(btn("Pause", "pause_task"));
  if (task.status === "paused")  btns.push(btn("Resume", "resume_task", "var(--green)"));
  if (task.status === "failed")  btns.push(btn("Restart", "restart_task", "var(--green)"));
  if (task.status === "pending" || task.status === "paused") {
    btns.push(btn("↓ Local", "force_local"));
    btns.push(btn("↑ Cloud", "force_cloud"));
    btns.push(btn("Skip", "skip_task", "var(--red)"));
  }

  return <>{btns.length ? btns : <span style={{ color: "var(--muted)" }}>—</span>}</>;
}
