import { useEffect, useState } from "react";
import { Project, ProjectRegistry } from "./config";
import { fetchSpecs, fetchStatus, SddSpec, SddStatus } from "./api";
import ProjectSwitcher from "./components/ProjectSwitcher";
import AddProjectScreen from "./components/AddProjectScreen";

type Tab = "dashboard" | "projects" | "add";

export default function App() {
  const [ready, setReady] = useState(false);
  const [projects, setProjects] = useState<Project[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("dashboard");
  const [addVisible, setAddVisible] = useState(false);

  useEffect(() => {
    ProjectRegistry.init();
    reload();
    setReady(true);
  }, []);

  function reload() {
    const all = ProjectRegistry.getAll();
    setProjects(all);
    setActiveId(ProjectRegistry.getActiveId());
  }

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
          onCancel={() => undefined} // kein Abbrechen ohne Projekte
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

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      <div style={{ flex: 1, overflow: "hidden", display: "flex", flexDirection: "column" }}>
        {tab === "dashboard" && (
          <DashboardTab
            project={activeProject}
            onProjectReload={reload}
          />
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

      <nav className="tab-bar">
        <button
          className={tab === "dashboard" ? "active" : ""}
          onClick={() => setTab("dashboard")}
        >
          <span className="tab-icon">📋</span>
          Dashboard
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
}: {
  project: Project | null;
  onProjectReload: () => void;
}) {
  const [status, setStatus] = useState<SddStatus | null>(null);
  const [specs, setSpecs] = useState<SddSpec[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!project) return;
    load(project);
  }, [project?.id]); // eslint-disable-line react-hooks/exhaustive-deps

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
      } else {
        setError("Server nicht erreichbar.");
      }
    } finally {
      setLoading(false);
    }
  }

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
          <div style={{ fontSize: 12, color: "var(--muted)", marginBottom: 8, textTransform: "uppercase", letterSpacing: 1 }}>
            Specs ({specs.length})
          </div>
          {specs.map(spec => (
            <div key={spec.id} style={{
              background: "var(--surface)", borderRadius: 8, padding: "10px 14px",
              marginBottom: 6, border: "1px solid var(--border)",
              display: "flex", justifyContent: "space-between", alignItems: "center",
            }}>
              <div>
                <span style={{ fontFamily: "monospace", fontSize: 12, color: "var(--accent)" }}>{spec.id}</span>
                <div style={{ fontSize: 13, color: "var(--text)", marginTop: 2 }}>{spec.title}</div>
              </div>
              <span style={{
                fontSize: 11, padding: "2px 8px", borderRadius: 10,
                background: "var(--bg)", color: "var(--muted)", border: "1px solid var(--border)",
              }}>
                {spec.status}
              </span>
            </div>
          ))}
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

const centeredStyle: React.CSSProperties = {
  flex: 1, display: "flex", alignItems: "center", justifyContent: "center",
  padding: 32, textAlign: "center",
};
