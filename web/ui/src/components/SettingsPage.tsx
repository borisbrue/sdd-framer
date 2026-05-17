import { useEffect, useState } from "react";
import { api, ConfigData } from "../api";
import { Theme, THEMES } from "../hooks/useTheme";

interface Props {
  currentTheme: Theme;
  onThemeChange: (t: Theme) => void;
  onClose: () => void;
}

const ACCENT: Record<Theme, string> = {
  dark:      "#89b4fa",
  light:     "#2563eb",
  cyberpunk: "#00ffff",
};

const THEME_COLORS: Record<Theme, { bg: string; surface: string; border: string; text: string }> = {
  dark:      { bg: "#1e1e2e", surface: "#2a2a3d", border: "#3d3d55", text: "#cdd6f4" },
  light:     { bg: "#f4f4f8", surface: "#ffffff",  border: "#d1d5db", text: "#1f2937" },
  cyberpunk: { bg: "#0a0a0f", surface: "#120820",  border: "#ff00ff", text: "#e0d7ff" },
};

type ConfigTab = "form" | "raw";

function ConfigEditor({ onSaved }: { onSaved: () => void }) {
  const [tab, setTab]               = useState<ConfigTab>("form");
  const [data, setData]             = useState<ConfigData | null>(null);
  const [loading, setLoading]       = useState(true);
  const [saving, setSaving]         = useState(false);
  const [error, setError]           = useState("");
  const [success, setSuccess]       = useState(false);

  // Form state
  const [projectName, setProjectName]         = useState("");
  const [evaluatorUrl, setEvaluatorUrl]       = useState("");
  const [maxRetries, setMaxRetries]           = useState(3);
  const [lifecycle, setLifecycle]             = useState<string[]>([]);
  const [newTag, setNewTag]                   = useState("");

  // Raw state
  const [rawYaml, setRawYaml] = useState("");

  useEffect(() => {
    setLoading(true);
    api.getConfig()
      .then(d => {
        setData(d);
        setProjectName(d.project_name);
        setEvaluatorUrl(d.evaluator_base_url);
        setMaxRetries(d.max_retries);
        setLifecycle(d.spec_lifecycle);
        setRawYaml(d.yaml);
      })
      .catch(() => setError("Config konnte nicht geladen werden."))
      .finally(() => setLoading(false));
  }, []);

  async function saveForm() {
    setSaving(true);
    setError("");
    setSuccess(false);
    try {
      await api.patchConfig({
        project_name:       projectName,
        evaluator_base_url: evaluatorUrl,
        max_retries:        maxRetries,
        spec_lifecycle:     lifecycle,
      });
      setSuccess(true);
      onSaved();
      setTimeout(() => setSuccess(false), 2500);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Speichern fehlgeschlagen.");
    } finally {
      setSaving(false);
    }
  }

  async function saveRaw() {
    setSaving(true);
    setError("");
    setSuccess(false);
    try {
      await api.saveConfigRaw(rawYaml);
      setSuccess(true);
      onSaved();
      setTimeout(() => setSuccess(false), 2500);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Speichern fehlgeschlagen.");
    } finally {
      setSaving(false);
    }
  }

  function addTag() {
    const tag = newTag.trim();
    if (tag && !lifecycle.includes(tag)) {
      setLifecycle(prev => [...prev, tag]);
    }
    setNewTag("");
  }

  function removeTag(tag: string) {
    setLifecycle(prev => prev.filter(t => t !== tag));
  }

  if (loading) return <p style={{ color: "var(--muted)", fontSize: 13 }}>Lade Config…</p>;
  if (!data && error) return <p style={{ color: "var(--red)", fontSize: 13 }}>{error}</p>;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {/* Tabs */}
      <div style={{ display: "flex", gap: 0, borderBottom: "1px solid var(--border)" }}>
        {(["form", "raw"] as ConfigTab[]).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            style={{
              padding: "6px 16px",
              fontSize: 12,
              borderRadius: 0,
              border: "none",
              borderBottom: tab === t ? "2px solid var(--accent)" : "2px solid transparent",
              color: tab === t ? "var(--accent)" : "var(--muted)",
              background: "none",
              cursor: "pointer",
            }}
          >
            {t === "form" ? "Felder" : "YAML (Erweitert)"}
          </button>
        ))}
      </div>

      {/* Form tab */}
      {tab === "form" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div>
            <label style={labelStyle}>Projektname</label>
            <input
              value={projectName}
              onChange={e => setProjectName(e.target.value)}
              placeholder="My Project"
              style={{ width: "100%" }}
            />
          </div>
          <div>
            <label style={labelStyle}>Evaluator-URL</label>
            <input
              value={evaluatorUrl}
              onChange={e => setEvaluatorUrl(e.target.value)}
              placeholder="http://localhost:8000"
              style={{ width: "100%" }}
            />
          </div>
          <div>
            <label style={labelStyle}>Max. Retries (Orchestrator)</label>
            <input
              type="number"
              min={1}
              max={10}
              value={maxRetries}
              onChange={e => setMaxRetries(Number(e.target.value))}
              style={{ width: 80 }}
            />
          </div>
          <div>
            <label style={labelStyle}>Spec-Lifecycle</label>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 4 }}>
              {lifecycle.map(tag => (
                <span
                  key={tag}
                  style={{
                    display: "flex", alignItems: "center", gap: 4,
                    background: "var(--surface)", border: "1px solid var(--border)",
                    borderRadius: 4, padding: "2px 8px", fontSize: 12,
                  }}
                >
                  {tag}
                  <button
                    onClick={() => removeTag(tag)}
                    style={{
                      border: "none", background: "none", padding: 0,
                      cursor: "pointer", color: "var(--muted)", fontSize: 12, lineHeight: 1,
                    }}
                  >
                    ×
                  </button>
                </span>
              ))}
              <div style={{ display: "flex", gap: 4 }}>
                <input
                  value={newTag}
                  onChange={e => setNewTag(e.target.value)}
                  onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); addTag(); } }}
                  placeholder="+ Status"
                  style={{ width: 100, padding: "2px 8px", fontSize: 12 }}
                />
                <button onClick={addTag} style={{ padding: "2px 8px", fontSize: 12 }}>+</button>
              </div>
            </div>
            <p style={{ fontSize: 11, color: "var(--muted)", marginTop: 4 }}>
              Reihenfolge = Lifecycle-Flow. Enter oder + drücken zum Hinzufügen.
            </p>
          </div>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <button className="primary" disabled={saving} onClick={saveForm}>
              {saving ? "Speichert…" : "Speichern"}
            </button>
            {success && <span style={{ fontSize: 12, color: "var(--green)" }}>✓ Gespeichert</span>}
            {error   && <span style={{ fontSize: 12, color: "var(--red)" }}>{error}</span>}
          </div>
        </div>
      )}

      {/* Raw YAML tab */}
      {tab === "raw" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <p style={{ fontSize: 11, color: "var(--muted)" }}>
            Direktes Bearbeiten der <code>.sdd/config.yaml</code>. YAML muss syntaktisch korrekt sein.
          </p>
          <textarea
            value={rawYaml}
            onChange={e => setRawYaml(e.target.value)}
            rows={20}
            spellCheck={false}
            style={{
              fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
              fontSize: 12,
              lineHeight: 1.6,
              padding: "10px 12px",
              resize: "vertical",
              width: "100%",
              background: "#1d2021",
              color: "#ebdbb2",
              border: "1px solid var(--border)",
              borderRadius: "var(--radius)",
            }}
          />
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <button className="primary" disabled={saving} onClick={saveRaw}>
              {saving ? "Speichert…" : "YAML speichern"}
            </button>
            {success && <span style={{ fontSize: 12, color: "var(--green)" }}>✓ Gespeichert</span>}
            {error   && <span style={{ fontSize: 12, color: "var(--red)" }}>{error}</span>}
          </div>
        </div>
      )}
    </div>
  );
}

export default function SettingsPage({ currentTheme, onThemeChange, onClose }: Props) {
  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <h2 style={{ fontSize: 20, fontWeight: 700 }}>Einstellungen</h2>
        <button onClick={onClose} style={{ padding: "4px 12px" }}>× Schließen</button>
      </div>

      <section className="card" style={{ marginBottom: 16 }}>
        <h3 style={sectionHead}>Erscheinungsbild</h3>

        <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
          {THEMES.map(({ id, label }) => {
            const active = id === currentTheme;
            const c = THEME_COLORS[id];
            return (
              <button
                key={id}
                onClick={() => onThemeChange(id)}
                style={{
                  padding: 0,
                  border: `2px solid ${active ? ACCENT[id] : "var(--border)"}`,
                  borderRadius: "var(--radius)",
                  background: "none",
                  cursor: "pointer",
                  width: 160,
                  overflow: "hidden",
                  transition: "border-color 0.2s, transform 0.1s",
                  transform: active ? "scale(1.03)" : "scale(1)",
                }}
              >
                <div style={{ background: c.bg, padding: 12, display: "flex", flexDirection: "column", gap: 6 }}>
                  <div style={{ background: c.surface, border: `1px solid ${c.border}`, borderRadius: 4, padding: "6px 10px" }}>
                    <div style={{ width: "60%", height: 6, background: ACCENT[id], borderRadius: 3, marginBottom: 4 }} />
                    <div style={{ width: "40%", height: 4, background: c.text, borderRadius: 2, opacity: 0.5 }} />
                  </div>
                  <div style={{ display: "flex", gap: 4 }}>
                    <div style={{ flex: 1, height: 4, background: c.border, borderRadius: 2, opacity: 0.6 }} />
                    <div style={{ flex: 2, height: 4, background: c.text, borderRadius: 2, opacity: 0.3 }} />
                  </div>
                </div>
                <div style={{
                  background: c.surface,
                  borderTop: `1px solid ${c.border}`,
                  padding: "8px 12px",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}>
                  <span style={{ color: c.text, fontSize: 13, fontWeight: active ? 700 : 400 }}>{label}</span>
                  {active && (
                    <span style={{ color: ACCENT[id], fontSize: 11 }}>✓ aktiv</span>
                  )}
                </div>
              </button>
            );
          })}
        </div>
      </section>

      <section className="card">
        <h3 style={{ ...sectionHead, marginBottom: 16 }}>Projekt-Config (.sdd/config.yaml)</h3>
        <ConfigEditor onSaved={() => {}} />
      </section>
    </div>
  );
}

const sectionHead: React.CSSProperties = {
  fontSize: 12,
  color: "var(--muted)",
  textTransform: "uppercase",
  letterSpacing: 1,
  marginBottom: 16,
};

const labelStyle: React.CSSProperties = {
  display: "block",
  fontSize: 12,
  color: "var(--muted)",
  marginBottom: 4,
};
