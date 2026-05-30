import { useState } from "react";
import { Project } from "../config";
import { createSpec, SddSpec } from "../api";

interface Props {
  project: Project;
  onCreated: (spec: SddSpec) => void;
  onCancel: () => void;
}

export default function AddSpecScreen({ project, onCreated, onCancel }: Props) {
  const [title, setTitle] = useState("");
  const [owner, setOwner] = useState("");
  const [priority, setPriority] = useState<"low" | "medium" | "high">("medium");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    setLoading(true);
    setError("");
    try {
      const spec = await createSpec(project, { title: title.trim(), owner: owner.trim(), priority });
      onCreated(spec);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Fehler beim Anlegen.");
      setLoading(false);
    }
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <button onClick={onCancel} style={styles.backBtn}>←</button>
        <span style={styles.title}>Neue Spec</span>
      </div>
      <div style={styles.body}>
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <label style={styles.fieldLabel}>
            Titel *
            <input
              value={title}
              onChange={e => setTitle(e.target.value)}
              placeholder="z.B. User-Login via OAuth"
              required
              // eslint-disable-next-line jsx-a11y/no-autofocus
              autoFocus
              style={styles.input}
            />
          </label>
          <label style={styles.fieldLabel}>
            Owner
            <input
              value={owner}
              onChange={e => setOwner(e.target.value)}
              placeholder="Boris"
              style={styles.input}
            />
          </label>
          <div style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 13, color: "var(--muted)" }}>
            Priorität
            <div style={{ display: "flex", gap: 8 }}>
              {(["low", "medium", "high"] as const).map(p => (
                <button
                  key={p}
                  type="button"
                  onClick={() => setPriority(p)}
                  style={{
                    flex: 1,
                    padding: "8px 0",
                    background: priority === p ? "var(--accent)" : "var(--surface)",
                    color: priority === p ? "#1d2021" : "var(--muted)",
                    border: `1px solid ${priority === p ? "var(--accent)" : "var(--border)"}`,
                    borderRadius: 6,
                    fontWeight: priority === p ? 600 : 400,
                  }}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
          {error && <p style={{ color: "var(--red)", fontSize: 13, margin: 0 }}>{error}</p>}
          <button type="submit" className="primary" disabled={!title.trim() || loading}>
            {loading ? "Anlegen…" : "Spec anlegen"}
          </button>
          <button type="button" onClick={onCancel}>Abbrechen</button>
        </form>
      </div>
    </div>
  );
}

const styles = {
  container: { display: "flex", flexDirection: "column" as const, height: "100%", background: "var(--bg)" },
  header: {
    display: "flex", alignItems: "center", gap: 12,
    padding: "14px 16px",
    paddingTop: "calc(14px + env(safe-area-inset-top))",
    borderBottom: "1px solid var(--border)",
    background: "var(--surface)",
  },
  backBtn: { background: "transparent", border: "none", color: "var(--accent)", fontSize: 20, cursor: "pointer", padding: 0 },
  title: { fontWeight: 700, fontSize: 16, color: "var(--text)" },
  body: { flex: 1, padding: 20, display: "flex", flexDirection: "column" as const, overflowY: "auto" as const },
  fieldLabel: { display: "flex", flexDirection: "column" as const, gap: 6, fontSize: 13, color: "var(--muted)" },
  input: {
    padding: "10px 12px",
    background: "var(--surface)",
    border: "1px solid var(--border)",
    borderRadius: 6,
    color: "var(--text)",
    fontSize: 16,
    width: "100%",
    boxSizing: "border-box" as const,
  },
};
