import { useEffect, useState } from "react";
import { Project } from "../config";
import { fetchSpec, updateSpec, SddSpecDetail } from "../api";
import TestRunPanel from "./TestRunPanel";
import MarkdownBody from "./MarkdownBody";
import GuidedSpecEditor from "./GuidedSpecEditor";

interface Props {
  project: Project;
  specId: string;
  onBack: () => void;
}

const STATUS_COLOR: Record<string, string> = {
  draft: "var(--muted)",
  review: "var(--yellow)",
  approved: "var(--blue, #58a6ff)",
  implemented: "var(--green)",
  deprecated: "var(--red)",
};

export default function SpecDetailScreen({ project, specId, onBack }: Props) {
  const [spec, setSpec] = useState<SddSpecDetail | null>(null);
  const [editing, setEditing] = useState(false);
  const [guided, setGuided] = useState(false);
  const [draft, setDraft] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setSpec(null);
    setEditing(false);
    setGuided(false);
    setError("");
    fetchSpec(project, specId)
      .then(s => { setSpec(s); setDraft(s.body); })
      .catch(() => setError("Spec konnte nicht geladen werden."));
  }, [specId]);

  async function handleSave() {
    if (!spec) return;
    setSaving(true);
    setError("");
    try {
      const updated = await updateSpec(project, spec.id, draft);
      setSpec(updated);
      setDraft(updated.body);
      setEditing(false);
    } catch {
      setError("Speichern fehlgeschlagen.");
    } finally {
      setSaving(false);
    }
  }

  if (guided && spec) {
    return (
      <GuidedSpecEditor
        project={project}
        spec={spec}
        onSaved={(updated) => { setSpec(updated); setDraft(updated.body); setGuided(false); }}
        onCancel={() => setGuided(false)}
      />
    );
  }

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      {/* Header */}
      <div style={{
        display: "flex", alignItems: "center", gap: 10,
        padding: "12px 16px", borderBottom: "1px solid var(--border)",
        background: "var(--surface)",
        paddingTop: "calc(12px + env(safe-area-inset-top))",
      }}>
        <button onClick={onBack} style={{ padding: "4px 10px", fontSize: 15 }}>←</button>
        <span style={{ flex: 1, fontWeight: 600, fontSize: 14, color: "var(--accent)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {spec?.id ?? specId}
        </span>
        {spec && !editing && (
          <>
            <button onClick={() => setGuided(true)} style={{ padding: "4px 10px", fontSize: 13, color: "var(--accent)", borderColor: "var(--accent)" }}>
              ✦ Geführt
            </button>
            <button onClick={() => setEditing(true)} style={{ padding: "4px 10px", fontSize: 13 }}>
              Bearbeiten
            </button>
          </>
        )}
        {editing && (
          <>
            <button onClick={() => { setEditing(false); setDraft(spec?.body ?? ""); }} style={{ padding: "4px 10px", fontSize: 13 }}>
              Abbrechen
            </button>
            <button onClick={handleSave} disabled={saving} className="primary" style={{ padding: "4px 14px", fontSize: 13 }}>
              {saving ? "…" : "Speichern"}
            </button>
          </>
        )}
      </div>

      {!spec && !error && (
        <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <p style={{ color: "var(--muted)" }}>Laden…</p>
        </div>
      )}

      {error && (
        <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <p style={{ color: "var(--red)", fontSize: 13 }}>{error}</p>
        </div>
      )}

      {spec && !editing && (
        <div style={{ flex: 1, overflowY: "auto", padding: 16 }}>
          {/* Meta */}
          <div style={{
            background: "var(--surface)", borderRadius: 10, padding: 14,
            border: "1px solid var(--border)", marginBottom: 16,
            display: "flex", flexDirection: "column", gap: 6,
          }}>
            <div style={{ fontWeight: 700, fontSize: 16, color: "var(--text)" }}>{spec.title}</div>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 4 }}>
              <Badge color={STATUS_COLOR[spec.status] ?? "var(--muted)"}>{spec.status}</Badge>
              <Badge color="var(--muted)">{spec.priority}</Badge>
              {spec.owner && <Badge color="var(--muted)">{spec.owner}</Badge>}
            </div>
            {(spec.contracts.length > 0 || spec.tests.length > 0) && (
              <div style={{ marginTop: 4, display: "flex", gap: 12, fontSize: 12, color: "var(--muted)" }}>
                {spec.contracts.length > 0 && <span>{spec.contracts.length} Contracts</span>}
                {spec.tests.length > 0 && <span>{spec.tests.length} Tests</span>}
              </div>
            )}
          </div>

          {/* Body */}
          <div style={{
            background: "var(--surface)", borderRadius: 10,
            padding: 14, border: "1px solid var(--border)",
          }}>
            {spec.body
              ? <MarkdownBody content={spec.body} />
              : <span style={{ color: "var(--muted)", fontSize: 13 }}>Kein Inhalt.</span>
            }
          </div>

          {/* Test-Run */}
          <div style={{ marginTop: 16 }}>
            <TestRunPanel project={project} specId={spec.id} />
          </div>
        </div>
      )}

      {spec && editing && (
        <textarea
          value={draft}
          onChange={e => setDraft(e.target.value)}
          spellCheck={false}
          style={{
            flex: 1, padding: 16, margin: 0, border: "none", outline: "none", resize: "none",
            fontFamily: "monospace", fontSize: 13, lineHeight: 1.6,
            background: "var(--bg)", color: "var(--text)",
          }}
        />
      )}
    </div>
  );
}

function Badge({ children, color }: { children: React.ReactNode; color: string }) {
  return (
    <span style={{
      fontSize: 11, padding: "2px 8px", borderRadius: 10,
      background: "var(--bg)", color, border: `1px solid ${color}`,
    }}>
      {children}
    </span>
  );
}
