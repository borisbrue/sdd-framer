import { useCallback, useEffect, useRef, useState } from "react";
import { HubProject, ServerStatus, fetchHubHealth, fetchHubProjects, postHubAction } from "../api";

const POLL_INTERVAL_MS = 8000;
const HEALTH_INTERVAL_MS = 8000;
const OFFLINE_THRESHOLD = 2; // consecutive failures before offline

type ConnectionState = "online" | "offline" | "unknown";

interface Props {
  hubUrl: string;
}

export default function HubPanel({ hubUrl }: Props) {
  const [connection, setConnection] = useState<ConnectionState>("unknown");
  const [projects, setProjects] = useState<HubProject[]>([]);
  const [lastFetchedAt, setLastFetchedAt] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [pendingActions, setPendingActions] = useState<Set<string>>(new Set());

  const failureCountRef = useRef(0);
  const isMounted = useRef(true);

  // ── Health monitor ──────────────────────────────────────────────────────────

  const checkHealth = useCallback(async () => {
    const ok = await fetchHubHealth(hubUrl);
    if (!isMounted.current) return;
    if (ok) {
      failureCountRef.current = 0;
      setConnection("online");
    } else {
      failureCountRef.current += 1;
      if (failureCountRef.current >= OFFLINE_THRESHOLD) {
        setConnection("offline");
      }
    }
  }, [hubUrl]);

  // ── Project polling ─────────────────────────────────────────────────────────

  const loadProjects = useCallback(async () => {
    try {
      const list = await fetchHubProjects(hubUrl);
      if (!isMounted.current) return;
      setProjects(list.projects);
      setLastFetchedAt(list.retrievedAt);
    } catch {
      // connection lost — health monitor will detect it
    } finally {
      if (isMounted.current) setLoading(false);
    }
  }, [hubUrl]);

  // ── Bootstrap ───────────────────────────────────────────────────────────────

  useEffect(() => {
    isMounted.current = true;
    let healthTimer: ReturnType<typeof setInterval>;
    let pollTimer: ReturnType<typeof setInterval>;

    async function init() {
      await checkHealth();
      await loadProjects();
      healthTimer = setInterval(checkHealth, HEALTH_INTERVAL_MS);
      pollTimer = setInterval(() => {
        if (connection !== "offline") loadProjects();
      }, POLL_INTERVAL_MS);
    }

    init();
    return () => {
      isMounted.current = false;
      clearInterval(healthTimer);
      clearInterval(pollTimer);
    };
  }, [hubUrl]); // re-init when hubUrl changes

  // Re-fetch on reconnect
  const prevConnection = useRef(connection);
  useEffect(() => {
    if (prevConnection.current === "offline" && connection === "online") {
      loadProjects();
    }
    prevConnection.current = connection;
  }, [connection, loadProjects]);

  // ── Actions ─────────────────────────────────────────────────────────────────

  async function handleAction(project: HubProject, action: "start" | "stop") {
    if (connection !== "online" || pendingActions.has(project.id)) return;

    setPendingActions(prev => new Set(prev).add(project.id));

    // Optimistic update
    const optimisticStatus: ServerStatus = action === "start" ? "starting" : "stopping";
    setProjects(prev =>
      prev.map(p => p.id === project.id ? { ...p, status: optimisticStatus } : p),
    );

    try {
      await postHubAction(hubUrl, project.id, action);
    } catch {
      // Revert optimistic update on failure
      setProjects(prev =>
        prev.map(p => p.id === project.id ? { ...p, status: project.status } : p),
      );
    } finally {
      // Poll for real status, then clear pending
      await loadProjects();
      if (isMounted.current) {
        setPendingActions(prev => {
          const next = new Set(prev);
          next.delete(project.id);
          return next;
        });
      }
    }
  }

  // ── Render ──────────────────────────────────────────────────────────────────

  const isOffline = connection === "offline";
  const isUnknown = connection === "unknown";

  return (
    <div style={{ flex: 1, overflowY: "auto", padding: 16 }}>
      {/* Header */}
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        marginBottom: 16,
      }}>
        <div style={{ fontWeight: 700, fontSize: 17, color: "var(--accent)" }}>
          Hub
        </div>
        <ConnectionBadge state={connection} />
      </div>

      {/* Offline banner */}
      {isOffline && lastFetchedAt && (
        <div
          role="alert"
          aria-live="polite"
          style={{
            background: "rgba(251,73,52,0.12)", border: "1px solid var(--red)",
            borderRadius: 8, padding: "10px 14px", marginBottom: 16,
            color: "var(--red)", fontSize: 13,
          }}
        >
          Hub nicht erreichbar · Letzter Abruf: {formatTime(lastFetchedAt)}
        </div>
      )}

      {/* No hubUrl configured */}
      {!hubUrl && (
        <div style={centeredStyle}>
          <p style={{ color: "var(--muted)" }}>
            Kein Hub konfiguriert. Scanne einen Hub-QR-Code um fortzufahren.
          </p>
        </div>
      )}

      {loading && (
        <p style={{ color: "var(--muted)", textAlign: "center" }}>Verbinde mit Hub…</p>
      )}

      {!loading && !isUnknown && projects.length === 0 && (
        <div style={centeredStyle}>
          <p style={{ color: "var(--muted)" }}>
            {isOffline
              ? "Keine Projektdaten verfügbar."
              : "Keine Projekte im Hub hinterlegt."}
          </p>
        </div>
      )}

      {projects.map(project => (
        <ProjectRow
          key={project.id}
          project={project}
          online={!isOffline && !isUnknown}
          pending={pendingActions.has(project.id)}
          onAction={handleAction}
        />
      ))}
    </div>
  );
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function ProjectRow({
  project, online, pending, onAction,
}: {
  project: HubProject;
  online: boolean;
  pending: boolean;
  onAction: (p: HubProject, a: "start" | "stop") => void;
}) {
  const isTransition = project.status === "starting" || project.status === "stopping";
  const buttonsDisabled = !online || pending || isTransition;

  return (
    <div
      style={{
        background: "var(--surface)", borderRadius: 8, padding: "12px 14px",
        marginBottom: 8, border: "1px solid var(--border)",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
        <div style={{ minWidth: 0 }}>
          <div style={{ fontWeight: 600, fontSize: 14, color: "var(--text)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {project.name}
          </div>
          <div style={{ marginTop: 4 }}>
            <StatusBadge status={project.status} />
          </div>
        </div>

        <div
          role="group"
          aria-label={`Aktionen für ${project.name}`}
          style={{ display: "flex", gap: 6, flexShrink: 0 }}
        >
          {(project.status === "stopped" || isTransition) && (
            <ActionButton
              label="Starten"
              disabled={buttonsDisabled || project.status !== "stopped"}
              onClick={() => onAction(project, "start")}
              color="var(--green)"
            />
          )}
          {(project.status === "running" || isTransition) && (
            <ActionButton
              label="Stoppen"
              disabled={buttonsDisabled || project.status !== "running"}
              onClick={() => onAction(project, "stop")}
              color="var(--red)"
            />
          )}
          {project.status === "error" && (
            <span style={{ fontSize: 12, color: "var(--red)", padding: "4px 0" }}>
              Fehler
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

function ActionButton({
  label, disabled, onClick, color,
}: {
  label: string;
  disabled: boolean;
  onClick: () => void;
  color: string;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      aria-disabled={disabled}
      title={disabled ? "Nicht verfügbar" : label}
      style={{
        fontSize: 12, padding: "5px 12px", borderRadius: 6,
        border: `1px solid ${disabled ? "var(--border)" : color}`,
        background: disabled ? "var(--bg)" : `color-mix(in srgb, ${color} 15%, var(--surface))`,
        color: disabled ? "var(--muted)" : color,
        cursor: disabled ? "not-allowed" : "pointer",
        fontWeight: 500, transition: "all 0.15s",
      }}
    >
      {label}
    </button>
  );
}

const STATUS_COLOR: Record<ServerStatus | "error", string> = {
  running:  "var(--green)",
  stopped:  "var(--muted)",
  starting: "var(--yellow)",
  stopping: "var(--yellow)",
  error:    "var(--red)",
};

const STATUS_LABEL: Record<ServerStatus | "error", string> = {
  running:  "läuft",
  stopped:  "gestoppt",
  starting: "startet…",
  stopping: "stoppt…",
  error:    "Fehler",
};

function StatusBadge({ status }: { status: string }) {
  const color = STATUS_COLOR[status as ServerStatus] ?? "var(--muted)";
  const label = STATUS_LABEL[status as ServerStatus] ?? status;
  return (
    <span
      aria-label={`Status: ${label}`}
      style={{
        fontSize: 11, padding: "2px 8px", borderRadius: 10,
        background: "var(--bg)", color, border: `1px solid ${color}`,
      }}
    >
      {label}
    </span>
  );
}

function ConnectionBadge({ state }: { state: ConnectionState }) {
  const map: Record<ConnectionState, { color: string; label: string }> = {
    online:  { color: "var(--green)", label: "Online" },
    offline: { color: "var(--red)",   label: "Offline" },
    unknown: { color: "var(--muted)", label: "Verbinde…" },
  };
  const { color, label } = map[state];
  return (
    <span
      aria-live="polite"
      style={{
        fontSize: 11, padding: "3px 10px", borderRadius: 10,
        background: `color-mix(in srgb, ${color} 15%, var(--surface))`,
        color, border: `1px solid ${color}`,
      }}
    >
      {label}
    </span>
  );
}

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" });
  } catch {
    return iso;
  }
}

const centeredStyle: React.CSSProperties = {
  flex: 1, display: "flex", alignItems: "center", justifyContent: "center",
  padding: 32, textAlign: "center",
};
