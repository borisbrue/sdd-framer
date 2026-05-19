import { useCallback, useEffect, useState } from "react";

// ── Types ──────────────────────────────────────────────────────────────────────

interface Substep {
  id: string;
  label: string;
  status: "done" | "active" | "pending" | "failed";
  detail?: string | null;
}

interface Action {
  id: string;
  label: string;
  endpoint?: string;
  method?: string;
  info?: boolean;
}

interface Stage {
  id: string;
  label: string;
  status: "done" | "active" | "pending" | "failed" | "skipped";
  detail?: string | null;
  substeps?: Substep[];
  actions?: Action[];
  count?: number;
  pass_rate?: number | null;
}

interface PipelineState {
  spec_id: string;
  status: string;
  stages: Stage[];
  next_action: Action | null;
  container_running: boolean;
  holdout_count: number;
  pr_path: string | null;
}

// ── Icons ──────────────────────────────────────────────────────────────────────

function StatusIcon({ status }: { status: Stage["status"] }) {
  const size = 22;
  if (status === "done") return (
    <svg width={size} height={size} viewBox="0 0 22 22">
      <circle cx="11" cy="11" r="10" fill="var(--green)" opacity="0.2" stroke="var(--green)" strokeWidth="1.5" />
      <polyline points="6,11 9.5,14.5 16,8" stroke="var(--green)" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
  if (status === "active") return (
    <svg width={size} height={size} viewBox="0 0 22 22">
      <circle cx="11" cy="11" r="10" fill="var(--accent)" opacity="0.15" stroke="var(--accent)" strokeWidth="1.5" />
      <circle cx="11" cy="11" r="3.5" fill="var(--accent)" />
    </svg>
  );
  if (status === "failed") return (
    <svg width={size} height={size} viewBox="0 0 22 22">
      <circle cx="11" cy="11" r="10" fill="var(--red)" opacity="0.15" stroke="var(--red)" strokeWidth="1.5" />
      <line x1="7" y1="7" x2="15" y2="15" stroke="var(--red)" strokeWidth="2" strokeLinecap="round" />
      <line x1="15" y1="7" x2="7" y2="15" stroke="var(--red)" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
  return (
    <svg width={size} height={size} viewBox="0 0 22 22">
      <circle cx="11" cy="11" r="10" fill="transparent" stroke="var(--border)" strokeWidth="1.5" />
    </svg>
  );
}

function SubStatusDot({ status }: { status: Substep["status"] }) {
  const color = status === "done" ? "var(--green)"
    : status === "active" ? "var(--accent)"
    : status === "failed" ? "var(--red)"
    : "var(--border)";
  return (
    <span style={{
      display: "inline-block", width: 8, height: 8, borderRadius: "50%",
      background: color, flexShrink: 0,
    }} />
  );
}

// ── Action button ──────────────────────────────────────────────────────────────

function ActionButton({ action, onDone }: { action: Action; onDone: () => void }) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  if (action.info) {
    return (
      <span style={{
        fontSize: 11, color: "var(--muted)", fontFamily: "monospace",
        background: "var(--bg)", padding: "2px 8px", borderRadius: 4,
        border: "1px solid var(--border)",
      }}>
        {action.label}
      </span>
    );
  }

  const trigger = async () => {
    if (!action.endpoint) return;
    setLoading(true);
    setResult(null);
    try {
      const res = await fetch(action.endpoint, { method: action.method ?? "POST" });
      const data = await res.json();
      setResult(data.ok ? "✓" : "✗ " + (data.output?.split("\n").slice(-2).join(" ") ?? "Fehler"));
      if (data.ok) setTimeout(onDone, 1500);
    } catch {
      setResult("✗ Verbindungsfehler");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <button
        onClick={trigger}
        disabled={loading}
        style={{
          background: "var(--accent)", color: "var(--bg)",
          border: "none", borderRadius: 5, padding: "4px 12px",
          fontSize: 12, fontWeight: 600, cursor: loading ? "wait" : "pointer",
          opacity: loading ? 0.7 : 1,
        }}
      >
        {loading ? "…" : action.label}
      </button>
      {result && (
        <span style={{
          fontSize: 11,
          color: result.startsWith("✓") ? "var(--green)" : "var(--red)",
        }}>
          {result}
        </span>
      )}
    </div>
  );
}

// ── Single stage node ──────────────────────────────────────────────────────────

function StageNode({ stage, onRefresh }: { stage: Stage; onRefresh: () => void }) {
  const isActive = stage.status === "active";
  const isFailed = stage.status === "failed";

  return (
    <div style={{
      display: "flex", flexDirection: "row", gap: 14, alignItems: "flex-start",
    }}>
      {/* Icon column */}
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", flexShrink: 0 }}>
        <StatusIcon status={stage.status} />
      </div>

      {/* Content */}
      <div style={{
        flex: 1, paddingBottom: 4,
        opacity: stage.status === "pending" ? 0.5 : 1,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 2 }}>
          <span style={{
            fontWeight: isActive || isFailed ? 700 : 500,
            fontSize: 13,
            color: isFailed ? "var(--red)" : isActive ? "var(--text)" : "var(--text)",
          }}>
            {stage.label}
          </span>
          {stage.count !== undefined && stage.count > 0 && (
            <span style={{
              fontSize: 10, background: "var(--border)", color: "var(--muted)",
              borderRadius: 10, padding: "1px 6px",
            }}>
              {stage.count}
            </span>
          )}
        </div>

        {stage.detail && (
          <div style={{ fontSize: 11, color: "var(--muted)", marginBottom: 4 }}>
            {stage.detail}
          </div>
        )}

        {/* Substeps */}
        {stage.substeps && stage.substeps.length > 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 3, marginBottom: 6 }}>
            {stage.substeps.map(sub => (
              <div key={sub.id} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11 }}>
                <SubStatusDot status={sub.status} />
                <span style={{ color: sub.status === "pending" ? "var(--muted)" : "var(--text)" }}>
                  {sub.label}
                </span>
                {sub.detail && (
                  <span style={{ color: "var(--muted)", marginLeft: 4 }}>{sub.detail}</span>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Actions */}
        {stage.actions && stage.actions.length > 0 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 4 }}>
            {stage.actions.map(a => (
              <ActionButton key={a.id} action={a} onDone={onRefresh} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Connector line ─────────────────────────────────────────────────────────────

function Connector({ fromStatus }: { fromStatus: Stage["status"] }) {
  return (
    <div style={{
      width: 2, height: 20, marginLeft: 10,
      background: fromStatus === "done" ? "var(--green)"
        : fromStatus === "active" ? "var(--accent)"
        : "var(--border)",
      opacity: fromStatus === "pending" ? 0.3 : 0.6,
      borderRadius: 1,
    }} />
  );
}

// ── Main component ─────────────────────────────────────────────────────────────

interface Props {
  specId: string;
}

export default function SpecPipelineView({ specId }: Props) {
  const [state, setState] = useState<PipelineState | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    fetch(`/api/specs/${specId}/pipeline`)
      .then(r => r.ok ? r.json() : r.json().then((e: {detail: string}) => { throw new Error(e.detail); }))
      .then(setState)
      .catch(e => setError(e.message));
  }, [specId]);

  useEffect(() => {
    load();
    // Poll every 15s when a stage is active
    const interval = setInterval(() => {
      if (state?.stages.some(s => s.status === "active")) load();
    }, 15000);
    return () => clearInterval(interval);
  }, [load, state]);

  if (error) return (
    <div style={{ padding: 12, color: "var(--muted)", fontSize: 12 }}>
      Pipeline nicht verfügbar: {error}
    </div>
  );
  if (!state) return (
    <div style={{ padding: 12, color: "var(--muted)", fontSize: 12 }}>Lade Pipeline…</div>
  );

  return (
    <div className="card" style={{ padding: "16px 20px" }}>
      <div style={{
        display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16,
      }}>
        <span style={{ fontWeight: 700, fontSize: 13, color: "var(--text)" }}>Pipeline</span>
        <button
          onClick={load}
          style={{
            background: "none", border: "none", cursor: "pointer",
            color: "var(--muted)", fontSize: 11, padding: "2px 6px",
          }}
          title="Aktualisieren"
        >
          ↻
        </button>
      </div>

      {/* Stage list */}
      <div style={{ display: "flex", flexDirection: "column" }}>
        {state.stages.map((stage, i) => (
          <div key={stage.id}>
            <StageNode stage={stage} onRefresh={load} />
            {i < state.stages.length - 1 && (
              <div style={{ marginLeft: 10 }}>
                <Connector fromStatus={stage.status} />
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Next action banner */}
      {state.next_action && (
        <div style={{
          marginTop: 16, padding: "10px 14px",
          background: "var(--bg)", border: "1px solid var(--border)",
          borderRadius: 6, display: "flex", alignItems: "center", gap: 10,
        }}>
          <span style={{ fontSize: 11, color: "var(--muted)", flexShrink: 0 }}>Nächster Schritt</span>
          <ActionButton action={state.next_action} onDone={load} />
        </div>
      )}

      {/* Status chips */}
      <div style={{ marginTop: 12, display: "flex", gap: 8, flexWrap: "wrap" }}>
        {state.container_running && (
          <span style={{
            fontSize: 10, padding: "2px 8px", borderRadius: 10,
            background: "rgba(180,210,100,0.15)", color: "var(--green)",
            border: "1px solid var(--green)", opacity: 0.8,
          }}>
            Container läuft
          </span>
        )}
        {state.holdout_count > 0 && (
          <span style={{
            fontSize: 10, padding: "2px 8px", borderRadius: 10,
            background: "var(--surface)", color: "var(--muted)",
            border: "1px solid var(--border)",
          }}>
            {state.holdout_count} Holdout{state.holdout_count !== 1 ? "s" : ""}
          </span>
        )}
        {state.pr_path && (
          <span style={{
            fontSize: 10, padding: "2px 8px", borderRadius: 10,
            background: "rgba(100,150,255,0.1)", color: "var(--accent)",
            border: "1px solid var(--accent)", opacity: 0.8,
          }}>
            PR erstellt
          </span>
        )}
      </div>
    </div>
  );
}
