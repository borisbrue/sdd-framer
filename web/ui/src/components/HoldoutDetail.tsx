import { useEffect, useState } from "react";
import { api, Holdout } from "../api";
import IdChip from "./IdChip";
import MarkdownBody from "./MarkdownBody";
import OpenButton from "./OpenButton";

interface Props {
  holdoutId: string;
  onNavigate: (id: string) => void;
}

export default function HoldoutDetail({ holdoutId, onNavigate }: Props) {
  const [holdout, setHoldout] = useState<(Holdout & { spec: string }) | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [editBody, setEditBody] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");

  useEffect(() => {
    setHoldout(null);
    setLoadError(null);
    setEditBody(null);
    setMsg("");
    api.getHoldout(holdoutId)
      .then(setHoldout)
      .catch(e => setLoadError(e instanceof Error ? e.message : String(e)));
  }, [holdoutId]);

  if (loadError) return (
    <div style={{ padding: 20, color: "var(--red)", fontSize: 13 }}>
      Fehler beim Laden: {loadError}
    </div>
  );
  if (!holdout) return <div style={{ padding: 20, color: "var(--muted)" }}>Lade…</div>;

  const body = editBody ?? holdout.body;
  const dirty = editBody !== null && editBody !== holdout.body;

  const save = async () => {
    if (!dirty) return;
    setSaving(true);
    try {
      const res = await api.saveHoldout(holdout.spec, holdout.id, body);
      if (res.ok) {
        setHoldout(h => h ? { ...h, body } : h);
        setEditBody(null);
        setMsg("✓ Gespeichert");
      }
    } catch {
      setMsg("✗ Fehler");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>
          <div style={{ flex: 1 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
              <IdChip id={holdout.id} onClick={() => {}} />
              <select
                value={holdout.status}
                onChange={async e => {
                  const s = e.target.value;
                  await api.patchHoldoutStatus(holdout.spec, holdout.id, s);
                  setHoldout(h => h ? { ...h, status: s } : h);
                }}
                style={{
                  fontSize: 11, background: "var(--surface)", color: "var(--muted)",
                  border: "1px solid var(--border)", borderRadius: 4, padding: "2px 6px", cursor: "pointer",
                }}
              >
                <option value="draft">draft</option>
                <option value="ready">ready</option>
                <option value="archived">archived</option>
              </select>
            </div>
            <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>{holdout.title}</h2>
            {holdout.spec && (
              <div style={{ fontSize: 12, color: "var(--muted)" }}>
                Spec: <IdChip id={holdout.spec} onClick={onNavigate} />
              </div>
            )}
          </div>
          <div style={{ display: "flex", gap: 8, flexShrink: 0 }}>
            <OpenButton absFile={holdout.abs_file} />
          </div>
        </div>
      </div>

      <section className="card">
        <h3 style={sectionHead}>Inhalt</h3>
        <textarea
          value={body}
          onChange={e => { setEditBody(e.target.value); setMsg(""); }}
          style={{
            width: "100%", minHeight: 300,
            background: "var(--bg)", color: "var(--text)",
            border: "1px solid var(--border)", borderRadius: 4,
            fontFamily: "monospace", fontSize: 12, lineHeight: 1.6,
            padding: 8, resize: "vertical", boxSizing: "border-box",
            marginTop: 8,
          }}
        />
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 8 }}>
          <button
            onClick={save}
            disabled={!dirty || saving}
            style={{
              background: dirty ? "var(--accent)" : "var(--border)",
              color: dirty ? "var(--bg)" : "var(--muted)",
              border: "none", borderRadius: 4, padding: "3px 14px",
              fontSize: 12, fontWeight: 600,
              cursor: dirty && !saving ? "pointer" : "default",
            }}
          >
            {saving ? "…" : "Speichern"}
          </button>
          {dirty && (
            <button
              onClick={() => { setEditBody(null); setMsg(""); }}
              style={{ background: "none", border: "none", color: "var(--muted)", fontSize: 11, cursor: "pointer" }}
            >
              Verwerfen
            </button>
          )}
          {msg && (
            <span style={{ fontSize: 11, color: msg.startsWith("✓") ? "var(--green)" : "var(--red)" }}>
              {msg}
            </span>
          )}
        </div>
      </section>

      {body.trim() && !dirty && (
        <section className="card">
          <h3 style={{ ...sectionHead, marginBottom: 12 }}>Vorschau</h3>
          <MarkdownBody markdown={body} onIdClick={onNavigate} />
        </section>
      )}
    </div>
  );
}

const sectionHead: React.CSSProperties = {
  fontSize: 12,
  color: "var(--muted)",
  textTransform: "uppercase",
  letterSpacing: 1,
};
