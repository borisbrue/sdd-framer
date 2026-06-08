import { useState } from "react";
import { api, AiUsageEntry } from "../api";
import { useNotify } from "./NotificationContext";

interface Props {
  specId: string;
  initialBody: string;
  onSaved: (newBody: string) => void;
}

type AiPhase = "idle" | "generating" | "preview";

function UsagePill({ entry }: { entry: AiUsageEntry }) {
  return (
    <span style={{ fontSize: 10, color: "var(--muted)", fontFamily: "monospace" }}>
      {entry.input_tokens}↑ {entry.output_tokens}↓
      {entry.cache_read_tokens > 0 && (
        <span style={{ color: "var(--green)" }}> {entry.cache_read_tokens} cached</span>
      )}
      {" "}${entry.cost_usd.toFixed(5)}
    </span>
  );
}

export default function DraftEditor({ specId, initialBody, onSaved }: Props) {
  const notify = useNotify();
  const [body, setBody]           = useState(initialBody);
  const [instructions, setInstructions] = useState("");
  const [aiPhase, setAiPhase]     = useState<AiPhase>("idle");
  const [preview, setPreview]     = useState("");
  const [aiUsage, setAiUsage]     = useState<AiUsageEntry | null>(null);
  const [saving, setSaving]       = useState(false);
  const [error, setError]         = useState("");
  const isDirty = body !== initialBody;

  async function handleGenerate() {
    if (!instructions.trim()) return;
    setAiPhase("generating");
    setError("");
    setPreview("");
    setAiUsage(null);
    try {
      const res = await api.aiImproveSpec({
        spec_id: specId,
        current_content: body,
        instructions,
      });
      setPreview(res.result);
      setAiUsage(res.usage);
      setAiPhase("preview");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Fehler beim Generieren.");
      setAiPhase("idle");
    }
  }

  function handleAccept() {
    setBody(preview);
    setPreview("");
    setAiUsage(null);
    setAiPhase("idle");
    setInstructions("");
  }

  function handleDiscard() {
    setPreview("");
    setAiUsage(null);
    setAiPhase("idle");
  }

  async function handleSave() {
    setSaving(true);
    setError("");
    try {
      await api.updateSpec(specId, body);
      notify("✓ Spec gespeichert", "success");
      onSaved(body);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Fehler beim Speichern.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="card" style={{ borderColor: "var(--accent)" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <h3 style={{ fontSize: 12, color: "var(--accent)", textTransform: "uppercase", letterSpacing: 1 }}>
          ✦ Draft-Editor
        </h3>
        <button
          className="primary"
          onClick={handleSave}
          disabled={saving || !isDirty}
          style={{ fontSize: 11, padding: "3px 12px", opacity: isDirty ? 1 : 0.4 }}
        >
          {saving ? "Speichert…" : "💾 Speichern"}
        </button>
      </div>

      {/* Editable body */}
      <textarea
        value={body}
        onChange={e => setBody(e.target.value)}
        rows={18}
        style={{
          width: "100%", fontFamily: "monospace", fontSize: 12,
          background: "var(--bg)", color: "var(--text)",
          border: "1px solid var(--border)", borderRadius: 4,
          padding: 10, resize: "vertical", boxSizing: "border-box",
          display: "block",
        }}
      />

      {/* AI preview */}
      {aiPhase === "preview" && (
        <div style={{ marginTop: 12 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
            <span style={{ fontSize: 11, color: "var(--accent)", textTransform: "uppercase", letterSpacing: 0.8 }}>
              KI-Vorschlag
            </span>
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              {aiUsage && <UsagePill entry={aiUsage} />}
              <button
                onClick={handleDiscard}
                style={{ fontSize: 11, padding: "2px 8px", color: "var(--muted)" }}
              >
                Verwerfen
              </button>
              <button
                className="primary"
                onClick={handleAccept}
                style={{ fontSize: 11, padding: "2px 10px" }}
              >
                ✓ Übernehmen
              </button>
            </div>
          </div>
          <textarea
            value={preview}
            onChange={e => setPreview(e.target.value)}
            rows={18}
            style={{
              width: "100%", fontFamily: "monospace", fontSize: 12,
              background: "var(--bg)", color: "var(--text)",
              border: "1px solid var(--accent)", borderRadius: 4,
              padding: 10, resize: "vertical", boxSizing: "border-box",
              display: "block",
            }}
          />
        </div>
      )}

      {/* Instruction row */}
      {aiPhase !== "preview" && (
        <div style={{ display: "flex", gap: 8, marginTop: 10, alignItems: "flex-start" }}>
          <textarea
            value={instructions}
            onChange={e => setInstructions(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) handleGenerate(); }}
            placeholder="Anweisung, z.B. 'Füge Akzeptanzkriterien hinzu' -- Ctrl+Enter"
            rows={2}
            style={{
              flex: 1, fontSize: 12, padding: 8,
              background: "var(--bg)", color: "var(--text)",
              border: "1px solid var(--border)", borderRadius: 4,
              resize: "none", boxSizing: "border-box",
            }}
          />
          <button
            onClick={handleGenerate}
            disabled={!instructions.trim() || aiPhase === "generating"}
            style={{
              fontSize: 12, padding: "8px 14px", whiteSpace: "nowrap",
              background: "var(--accent)", color: "#1e1e2e",
              border: "none", borderRadius: 4, cursor: "pointer",
              opacity: (!instructions.trim() || aiPhase === "generating") ? 0.5 : 1,
            }}
          >
            {aiPhase === "generating" ? "✦ …" : "✦ Ausführen"}
          </button>
        </div>
      )}

      {error && <p style={{ color: "var(--red)", fontSize: 12, marginTop: 8 }}>{error}</p>}
    </section>
  );
}
