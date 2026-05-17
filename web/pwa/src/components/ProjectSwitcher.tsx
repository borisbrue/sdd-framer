import { Project, ProjectRegistry } from "../config";

interface Props {
  projects: Project[];
  activeId: string | null;
  onActivate: (id: string) => void;
  onAdd: () => void;
  onRemove: (id: string) => void;
}

export default function ProjectSwitcher({ projects, activeId, onActivate, onAdd, onRemove }: Props) {
  if (projects.length === 0) {
    return (
      <div style={styles.empty}>
        <div style={{ fontSize: 40, marginBottom: 12 }}>📡</div>
        <p style={{ color: "var(--muted)", marginBottom: 16 }}>Noch keine SDD-Projekte verbunden.</p>
        <button className="primary" onClick={onAdd} style={{ width: "100%", maxWidth: 280 }}>
          + Projekt hinzufügen
        </button>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <span style={styles.label}>Projekte ({projects.length})</span>
        <button onClick={onAdd} style={styles.addBtn}>+ Hinzufügen</button>
      </div>

      <div style={styles.list}>
        {projects.map(project => (
          <ProjectRow
            key={project.id}
            project={project}
            isActive={project.id === activeId}
            onActivate={() => {
              ProjectRegistry.setActive(project.id);
              onActivate(project.id);
            }}
            onRemove={() => onRemove(project.id)}
          />
        ))}
      </div>
    </div>
  );
}

function ProjectRow({
  project, isActive, onActivate, onRemove,
}: {
  project: Project;
  isActive: boolean;
  onActivate: () => void;
  onRemove: () => void;
}) {
  return (
    <div
      onClick={onActivate}
      style={{
        ...styles.row,
        background: isActive ? "var(--accent-dim, rgba(131,148,150,0.12))" : "transparent",
        borderLeft: isActive ? "3px solid var(--accent)" : "3px solid transparent",
      }}
    >
      <div style={styles.rowInfo}>
        <div style={styles.rowName}>
          {project.name}
          {project.auth_required && (
            <span style={styles.authBadge} title="Token abgelaufen – neu verbinden">🔒</span>
          )}
        </div>
        <div style={styles.rowUrl}>{project.baseUrl}</div>
      </div>

      <button
        onClick={(e) => { e.stopPropagation(); if (confirm(`"${project.name}" entfernen?`)) onRemove(); }}
        style={styles.removeBtn}
        title="Projekt entfernen"
      >
        ×
      </button>
    </div>
  );
}

const styles = {
  container: { display: "flex", flexDirection: "column" as const, height: "100%" },
  header: {
    display: "flex", justifyContent: "space-between", alignItems: "center",
    padding: "12px 16px",
    borderBottom: "1px solid var(--border)",
  },
  label: { fontSize: 12, color: "var(--muted)", textTransform: "uppercase" as const, letterSpacing: 1 },
  addBtn: { padding: "4px 10px", fontSize: 12 },
  list: { flex: 1, overflowY: "auto" as const, padding: 8 },
  row: {
    display: "flex", alignItems: "center",
    padding: "12px 10px",
    borderRadius: 6,
    cursor: "pointer",
    gap: 8,
    transition: "background 0.1s",
  },
  rowInfo: { flex: 1, minWidth: 0 },
  rowName: { fontWeight: 600, fontSize: 14, color: "var(--text)", display: "flex", alignItems: "center", gap: 6 },
  rowUrl: { fontSize: 12, color: "var(--muted)", marginTop: 2, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" as const },
  authBadge: { fontSize: 12 },
  removeBtn: {
    background: "transparent", border: "none", color: "var(--muted)",
    cursor: "pointer", padding: "2px 6px", fontSize: 18, lineHeight: 1,
    flexShrink: 0,
  },
  empty: {
    display: "flex", flexDirection: "column" as const,
    alignItems: "center", justifyContent: "center",
    height: "100%", padding: 32, textAlign: "center" as const,
  },
};
