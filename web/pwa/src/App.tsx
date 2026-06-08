import { useCallback, useEffect, useMemo, useState } from "react";
import { Project, ProjectRegistry, refreshProjectsFromHub } from "./config";
import { fetchSpecs, fetchStatus, SddSpec, SddStatus } from "./api";
import ProjectSwitcher from "./components/ProjectSwitcher";
import AddProjectScreen from "./components/AddProjectScreen";
import AddSpecScreen from "./components/AddSpecScreen";
import SpecDetailScreen from "./components/SpecDetailScreen";
import HubPanel from "./components/HubPanel";

type Tab = "dashboard" | "hub" | "projects";

export default function App() {
  const [ready, setReady] = useState(false);
  const [projects, setProjects] = useState<Project[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("dashboard");
  const [addVisible, setAddVisible] = useState(false);
  const [newSpecVisible, setNewSpecVisible] = useState(false);
  const [selectedSpecId, setSelectedSpecId] = useState<string | null>(null);

  useEffect(() => {
    ProjectRegistry.init();
    const all = ProjectRegistry.getAll();
    setProjects(all);
    setActiveId(ProjectRegistry.getActiveId());
    setReady(true);
    // Hub-Refresh: aktualisiert baseUrl wenn Projektserver neu gestartet wurde
    refreshProjectsFromHub(all).then(updated => {
      setProjects(updated);
    });
  }, []);

  const reload = useCallback(() => {
    const all = ProjectRegistry.getAll();
    setProjects(all);
    setActiveId(ProjectRegistry.getActiveId());
  }, []);

  function handleActivate(id: string) {
    setActiveId(id);
    setTab("dashboard");
  }

  function handleRemove(id: string) {
    ProjectRegistry.remove(id);
    reload();
  }

  function handleAdded(project: Project) {
    reload();
    setActiveId(project.id);
    setAddVisible(false);
    setTab("dashboard");
  }

  if (!ready) return null;

  const activeProject = projects.find(p => p.id === activeId) ?? null;

  // Kein Projekt → direkt in den "Hinzufügen"-Screen
  if (projects.length === 0 && !addVisible) {
    return (
      <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
        <AddProjectScreen
          onAdded={handleAdded}
          onCancel={() => undefined}
        />
      </div>
    );
  }

  if (addVisible) {
    return (
      <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
        <AddProjectScreen
          onAdded={handleAdded}
          onCancel={() => setAddVisible(false)}
        />
      </div>
    );
  }

  if (newSpecVisible && activeProject) {
    return (
      <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
        <AddSpecScreen
          project={activeProject}
          onCreated={(spec) => { setNewSpecVisible(false); setSelectedSpecId(spec.id); }}
          onCancel={() => setNewSpecVisible(false)}
        />
      </div>
    );
  }

  if (selectedSpecId && activeProject) {
    return (
      <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
        <SpecDetailScreen
          project={activeProject}
          specId={selectedSpecId}
          onBack={() => setSelectedSpecId(null)}
        />
      </div>
    );
  }

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column", paddingTop: "env(safe-area-inset-top)" }}>
      <div style={{ flex: 1, overflow: "hidden", display: "flex", flexDirection: "column" }}>
        {tab === "dashboard" && (
          <DashboardTab
            project={activeProject}
            onProjectReload={reload}
            onSelectSpec={setSelectedSpecId}
          />
        )}
        {tab === "hub" && (
          <HubPanel hubUrl={activeProject?.hubUrl ?? ""} />
        )}
        {tab === "projects" && (
          <ProjectSwitcher
            projects={projects}
            activeId={activeId}
            onActivate={handleActivate}
            onAdd={() => setAddVisible(true)}
            onRemove={handleRemove}
          />
        )}
      </div>

      {tab === "dashboard" && activeProject && (
        <button
          onClick={() => setNewSpecVisible(true)}
          style={{
            position: "fixed",
            right: 20,
            bottom: "calc(70px + env(safe-area-inset-bottom))",
            width: 52,
            height: 52,
            borderRadius: "50%",
            background: "var(--accent)",
            color: "#1d2021",
            border: "none",
            fontSize: 26,
            fontWeight: 300,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            boxShadow: "0 4px 16px rgba(0,0,0,0.5)",
            cursor: "pointer",
            zIndex: 100,
            padding: 0,
            lineHeight: 1,
          }}
          title="Neue Spec anlegen"
        >
          +
        </button>
      )}

      <nav className="tab-bar">
        <button
          className={tab === "dashboard" ? "active" : ""}
          onClick={() => setTab("dashboard")}
        >
          <span className="tab-icon">📋</span>
          Dashboard
        </button>
        <button
          className={tab === "hub" ? "active" : ""}
          onClick={() => setTab("hub")}
        >
          <span className="tab-icon">🔌</span>
          Hub
        </button>
        <button
          className={tab === "projects" ? "active" : ""}
          onClick={() => setTab("projects")}
        >
          <span className="tab-icon">📡</span>
          Projekte
        </button>
        <button onClick={() => setAddVisible(true)}>
          <span className="tab-icon">＋</span>
          Hinzufügen
        </button>
      </nav>
    </div>
  );
}

// ── Dashboard ──────────────────────────────────────────────────────────────────

function DashboardTab({
  project,
  onProjectReload,
  onSelectSpec,
}: {
  project: Project | null;
  onProjectReload: () => void;
  onSelectSpec: (id: string) => void;
}) {
  const [status, setStatus] = useState<SddStatus | null>(null);
  const [specs, setSpecs] = useState<SddSpec[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [statusFilter, setStatusFilter] = useState<string | null>(null);

  useEffect(() => { setStatusFilter(null); }, [project?.id]);

  const availableStatuses = useMemo(
    () => [...new Set(specs.map(s => s.status))].sort(),
    [specs],
  );

  const visibleSpecs = useMemo(() => {
    const sorted = [...specs].sort((a, b) => b.updated.localeCompare(a.updated));
    return statusFilter ? sorted.filter(s => s.status === statusFilter) : sorted;
  }, [specs, statusFilter]);

  useEffect(() => {
    if (!project) return;
    async function load(p: Project) {
      setLoading(true);
      setError("");
      try {
        const [s, sp] = await Promise.all([fetchStatus(p), fetchSpecs(p)]);
        setStatus(s);
        setSpecs(sp);
      } catch (e: unknown) {
        const err = e as { status?: number; message?: string };
        if (err.status === 401) {
          // CON-0087 G-06: 401 → nur dieses Projekt markieren, nicht alle löschen
          ProjectRegistry.update(p.id, { auth_required: true });
          onProjectReload();
          setError("Authentifizierung abgelaufen. Bitte QR-Code erneut scannen.");
        } else if (p.hubUrl) {
          // Netzwerkfehler: Hub befragen ob Port sich geändert hat (z.B. nach Server-Neustart)
          const refreshed = await refreshProjectsFromHub(ProjectRegistry.getAll());
          const updated = refreshed.find(rp => rp.id === p.id);
          if (updated && updated.baseUrl !== p.baseUrl) {
            onProjectReload(); // baseUrl-Dep triggert useEffect-Neustart mit neuem Port
            return;
          }
          setError("Server nicht erreichbar.");
        } else {
          setError("Server nicht erreichbar.");
        }
      } finally {
        setLoading(false);
      }
    }
    load(project);
  }, [project?.id, project?.baseUrl, onProjectReload]);

  if (!project) {
    return (
      <div style={centeredStyle}>
        <p style={{ color: "var(--muted)" }}>Kein aktives Projekt. Wähle eines in der Projektliste.</p>
      </div>
    );
  }

  return (
    <div style={{ flex: 1, overflowY: "auto", padding: 16 }}>
      {/* Projekt-Header */}
      <div style={{
        background: "var(--surface)", borderRadius: 10,
        padding: 16, marginBottom: 16, border: "1px solid var(--border)",
      }}>
        <div style={{ fontWeight: 700, fontSize: 17, color: "var(--accent)", marginBottom: 4 }}>
          {project.name}
        </div>
        <div style={{ fontSize: 12, color: "var(--muted)", wordBreak: "break-all" }}>
          {project.baseUrl}
        </div>
        {project.auth_required && (
          <div style={{
            marginTop: 10, padding: "8px 12px",
            background: "rgba(251,73,52,0.12)", borderRadius: 6,
            color: "var(--red)", fontSize: 13,
          }}>
            Token abgelaufen — scanne den QR-Code erneut, um die Verbindung zu erneuern.
          </div>
        )}
      </div>

      {loading && <p style={{ color: "var(--muted)", textAlign: "center" }}>Laden…</p>}
      {error && <p style={{ color: "var(--red)", fontSize: 13, textAlign: "center" }}>{error}</p>}

      {/* Stats */}
      {status && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 16 }}>
          <StatCard label="Specs" value={status.specs} />
          <StatCard label="Contracts" value={status.contracts} />
          <StatCard label="Tests" value={status.tests} />
          <StatCard
            label="Lücken"
            value={status.gaps}
            accent={status.gaps > 0 ? "var(--yellow)" : "var(--green)"}
          />
        </div>
      )}

      {/* Spec-Liste */}
      {specs.length > 0 && (
        <div>
          {/* Header + Filter-Chips */}
          <div style={{ fontSize: 12, color: "var(--muted)", marginBottom: 8, textTransform: "uppercase", letterSpacing: 1 }}>
            Specs ({statusFilter ? `${visibleSpecs.length} von ${specs.length}` : specs.length})
          </div>
          <div style={{ display: "flex", gap: 6, overflowX: "auto", marginBottom: 12, paddingBottom: 2, scrollbarWidth: "none" }}>
            <FilterChip
              active={statusFilter === null}
              onClick={() => setStatusFilter(null)}
            >
              Alle
            </FilterChip>
            {availableStatuses.map(s => (
              <FilterChip
                key={s}
                active={statusFilter === s}
                status={s}
                onClick={() => setStatusFilter(prev => prev === s ? null : s)}
              >
                {s} <span style={{ opacity: 0.65 }}>({specs.filter(sp => sp.status === s).length})</span>
              </FilterChip>
            ))}
          </div>

          {/* Ergebnis-Liste */}
          {visibleSpecs.length === 0 ? (
            <p style={{ color: "var(--muted)", fontSize: 13, textAlign: "center", padding: "16px 0" }}>
              Keine Specs mit Status „{statusFilter}".
            </p>
          ) : (
            visibleSpecs.map(spec => (
              <div key={spec.id}
                onClick={() => onSelectSpec(spec.id)}
                style={{
                  background: "var(--surface)", borderRadius: 8, padding: "10px 14px",
                  marginBottom: 6, border: "1px solid var(--border)",
                  display: "flex", justifyContent: "space-between", alignItems: "center",
                  cursor: "pointer",
                }}>
                <div style={{ minWidth: 0 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ fontFamily: "monospace", fontSize: 12, color: "var(--accent)", flexShrink: 0 }}>{spec.id}</span>
                    {spec.updated && (
                      <span style={{ fontSize: 11, color: "var(--muted)" }}>{spec.updated}</span>
                    )}
                  </div>
                  <div style={{ fontSize: 13, color: "var(--text)", marginTop: 2, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{spec.title}</div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 6, flexShrink: 0, marginLeft: 8 }}>
                  <StatusBadge status={spec.status} />
                  <span style={{ color: "var(--muted)", fontSize: 16 }}>›</span>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value, accent }: { label: string; value: number; accent?: string }) {
  return (
    <div style={{
      background: "var(--surface)", borderRadius: 10, padding: "14px 16px",
      border: "1px solid var(--border)", textAlign: "center",
    }}>
      <div style={{ fontSize: 26, fontWeight: 700, color: accent ?? "var(--text)" }}>{value}</div>
      <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 4 }}>{label}</div>
    </div>
  );
}

const STATUS_COLOR: Record<string, string> = {
  draft:         "var(--muted)",
  review:        "var(--yellow)",
  approved:      "var(--accent)",
  "in-progress": "var(--accent)",
  implemented:   "var(--green)",
  deprecated:    "var(--red)",
};

function StatusBadge({ status }: { status: string }) {
  const color = STATUS_COLOR[status] ?? "var(--muted)";
  return (
    <span style={{
      fontSize: 11, padding: "2px 8px", borderRadius: 10,
      background: "var(--bg)", color, border: `1px solid ${color}`,
      whiteSpace: "nowrap",
    }}>
      {status}
    </span>
  );
}

function FilterChip({
  active, status, onClick, children,
}: {
  active: boolean;
  status?: string;
  onClick: () => void;
  children: React.ReactNode;
}) {
  const color = status ? (STATUS_COLOR[status] ?? "var(--muted)") : "var(--text)";
  return (
    <button
      onClick={onClick}
      style={{
        flexShrink: 0,
        fontSize: 12,
        padding: "4px 12px",
        borderRadius: 20,
        border: `1px solid ${active ? color : "var(--border)"}`,
        background: active ? `color-mix(in srgb, ${color} 15%, var(--surface))` : "var(--surface)",
        color: active ? color : "var(--muted)",
        fontWeight: active ? 600 : 400,
        cursor: "pointer",
        transition: "all 0.15s",
      }}
    >
      {children}
    </button>
  );
}

const centeredStyle: React.CSSProperties = {
  flex: 1, display: "flex", alignItems: "center", justifyContent: "center",
  padding: 32, textAlign: "center",
};
