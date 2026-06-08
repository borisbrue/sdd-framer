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
  secondary?: boolean;
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
  const size = 18;
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
      display: "inline-block", width: 7, height: 7, borderRadius: "50%",
      background: color, flexShrink: 0,
    }} />
  );
}

// ── Action button ──────────────────────────────────────────────────────────────

function ActionButton({ action, onDone, onTriggered }: { action: Action; onDone: () => void; onTriggered?: (id: string) => void }) {
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
      if (!res.ok) {
        setResult("✗ " + (data.detail ?? `HTTP ${res.status}`));
        return;
      }
      if (data.ok) {
        setResult("✓ " + (data.output?.split("\n")[0] ?? "OK"));
        onTriggered?.(action.id);
        setTimeout(onDone, 1500);
      } else {
        const lines = (data.output ?? data.detail ?? "Fehler unbekannt")
          .split("\n").filter(Boolean).slice(0, 4).join(" · ");
        setResult("✗ " + lines);
      }
    } catch (e) {
      setResult("✗ Verbindungsfehler: " + (e instanceof Error ? e.message : String(e)));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <button
        onClick={trigger}
        disabled={loading}
        style={action.secondary ? {
          background: "none", color: "var(--muted)",
          border: "1px solid var(--border)", borderRadius: 5, padding: "3px 10px",
          fontSize: 11, fontWeight: 400, cursor: loading ? "wait" : "pointer",
          opacity: loading ? 0.5 : 1,
        } : {
          background: "var(--accent)", color: "var(--bg)",
          border: "none", borderRadius: 5, padding: "4px 12px",
          fontSize: 12, fontWeight: 600, cursor: loading ? "wait" : "pointer",
          opacity: loading ? 0.7 : 1,
        }}
      >
        {loading ? "…" : action.label}
      </button>
      {result && (
        <span style={{ fontSize: 11, color: result.startsWith("✓") ? "var(--green)" : "var(--red)" }}>
          {result}
        </span>
      )}
    </div>
  );
}

// ── Horizontal connector ───────────────────────────────────────────────────────

function HorizontalConnector({ fromStatus }: { fromStatus: Stage["status"] }) {
  return (
    <div style={{
      width: 20, height: 2, flexShrink: 0,
      alignSelf: "flex-start", marginTop: 14,
      background: fromStatus === "done" ? "var(--green)"
        : fromStatus === "active" ? "var(--accent)"
        : "var(--border)",
      opacity: fromStatus === "pending" || fromStatus === "skipped" ? 0.25 : 0.6,
      borderRadius: 1,
    }} />
  );
}

// ── Stage chip ─────────────────────────────────────────────────────────────────

function StageChip({ stage, expanded, onClick }: { stage: Stage; expanded: boolean; onClick: () => void }) {
  const isActive = stage.status === "active";
  const isFailed = stage.status === "failed";
  return (
    <button
      onClick={onClick}
      title={stage.label + (stage.detail ? " – " + stage.detail : "")}
      style={{
        display: "flex", flexDirection: "column", alignItems: "center", gap: 3,
        padding: "6px 8px", borderRadius: 6, border: "none",
        cursor: "pointer", flexShrink: 0,
        background: expanded ? "var(--surface)" : "transparent",
        outline: isActive ? "2px solid var(--accent)"
          : isFailed ? "2px solid var(--red)"
          : expanded ? "1px solid var(--border)"
          : "none",
        opacity: stage.status === "pending" || stage.status === "skipped" ? 0.45 : 1,
      }}
    >
      <StatusIcon status={stage.status} />
      <span style={{
        fontSize: 10, fontWeight: isActive || isFailed ? 700 : 400,
        color: isFailed ? "var(--red)" : isActive ? "var(--text)" : "var(--muted)",
        maxWidth: 72, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
      }}>
        {stage.label}
      </span>
      {stage.count !== undefined && stage.count > 0 && (
        <span style={{
          fontSize: 9, background: "var(--border)", color: "var(--muted)",
          borderRadius: 8, padding: "0 4px", lineHeight: "14px",
        }}>
          {stage.count}
        </span>
      )}
    </button>
  );
}

// ── Expanded stage detail panel ────────────────────────────────────────────────

function StageDetailPanel({ stage, onRefresh, onTriggered }: { stage: Stage; onRefresh: () => void; onTriggered?: (id: string) => void }) {
  const borderColor = stage.status === "failed" ? "var(--red)"
    : stage.status === "active" ? "var(--accent)"
    : "var(--border)";
  return (
    <div style={{
      marginTop: 8, padding: "10px 14px", borderRadius: 6,
      background: "var(--surface)", border: `1px solid ${borderColor}`,
    }}>
      <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 4, color: "var(--text)" }}>
        {stage.label}
      </div>
      {stage.detail && (
        <div style={{ fontSize: 11, color: "var(--muted)", marginBottom: 8 }}>
          {stage.detail}
        </div>
      )}
      {stage.substeps && stage.substeps.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 3, marginBottom: 8 }}>
          {stage.substeps.map(sub => (
            <div key={sub.id} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11 }}>
              <SubStatusDot status={sub.status} />
              <span style={{ color: sub.status === "pending" ? "var(--muted)" : "var(--text)" }}>
                {sub.label}
              </span>
              {sub.detail && <span style={{ color: "var(--muted)", marginLeft: 4 }}>{sub.detail}</span>}
            </div>
          ))}
        </div>
      )}
      {stage.actions && stage.actions.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
          {stage.actions.map(a => (
            <ActionButton key={a.id} action={a} onDone={onRefresh} onTriggered={onTriggered} />
          ))}
        </div>
      )}
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────

const LOG_ACTION_IDS = new Set(["start", "run-tests", "review", "propose-contracts", "generate-holdouts", "finalize", "evaluate"]);

interface Props {
  specId: string;
  onActionTriggered?: (actionId: string) => void;
}

export default function SpecPipelineView({ specId, onActionTriggered }: Props) {
  const [state, setState] = useState<PipelineState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const load = useCallback(() => {
    fetch(`/api/specs/${specId}/pipeline`)
      .then(r => r.ok ? r.json() : r.json().then((e: { detail: string }) => { throw new Error(e.detail); }))
      .then((data: PipelineState) => {
        setState(data);
        setExpandedId(prev => {
          if (prev && data.stages.some(s => s.id === prev)) return prev;
          const auto = data.stages.find(s => s.status === "active" || s.status === "failed");
          return auto?.id ?? null;
        });
      })
      .catch(e => setError(e.message));
  }, [specId]);

  useEffect(() => {
    setExpandedId(null);
    load();
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

  const expandedStage = state.stages.find(s => s.id === expandedId);

  const stageRow: React.ReactNode[] = [];
  state.stages.forEach((stage, i) => {
    stageRow.push(
      <StageChip
        key={stage.id}
        stage={stage}
        expanded={expandedId === stage.id}
        onClick={() => setExpandedId(prev => prev === stage.id ? null : stage.id)}
      />
    );
    if (i < state.stages.length - 1) {
      stageRow.push(<HorizontalConnector key={`c${i}`} fromStatus={stage.status} />);
    }
  });

  return (
    <div className="card" style={{ padding: "14px 20px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
        <span style={{ fontWeight: 700, fontSize: 13, color: "var(--text)" }}>Pipeline</span>
        <button
          onClick={load}
          style={{ background: "none", border: "none", cursor: "pointer", color: "var(--muted)", fontSize: 11, padding: "2px 6px" }}
          title="Aktualisieren"
        >
          ↻
        </button>
      </div>

      {/* Horizontal stage row */}
      <div style={{ display: "flex", alignItems: "flex-start", overflowX: "auto", paddingBottom: 2 }}>
        {stageRow}
      </div>

      {/* Expanded stage detail */}
      {expandedStage && (
        <StageDetailPanel
          stage={expandedStage}
          onRefresh={load}
          onTriggered={id => LOG_ACTION_IDS.has(id) && onActionTriggered?.(id)}
        />
      )}

      {/* Next action banner */}
      {state.next_action && (
        <div style={{
          marginTop: 12, padding: "8px 12px",
          background: "var(--bg)", border: "1px solid var(--border)",
          borderRadius: 6, display: "flex", alignItems: "center", gap: 10,
        }}>
          <span style={{ fontSize: 11, color: "var(--muted)", flexShrink: 0 }}>Nächster Schritt</span>
          <ActionButton
            action={state.next_action}
            onDone={load}
            onTriggered={id => LOG_ACTION_IDS.has(id) && onActionTriggered?.(id)}
          />
        </div>
      )}

      {/* Status chips */}
      <div style={{ marginTop: 10, display: "flex", gap: 8, flexWrap: "wrap" }}>
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
