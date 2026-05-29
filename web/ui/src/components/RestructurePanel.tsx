import { useState } from "react";
import { api } from "../api";
import { useNotify } from "./NotificationContext";

const INSTRUCTIONS: Record<"spec" | "contract", string> = {
  spec:
    "Reorganisiere diesen Spec-Body so, dass alle Informationen an der richtigen Stelle " +
    "gemäß SDD-Struktur sind: (1) Zweck & Überblick, (2) Akzeptanzkriterien als Checkliste " +
    "mit - [ ] Einträgen, (3) Constraints & Non-Goals, (4) Abhängigkeiten, (5) Notizen. " +
    "Verändere den Inhalt NICHT – ordne nur die bestehenden Informationen richtig an. " +
    "Gib nur den Markdown-Body aus (kein Frontmatter, keine Code-Fences).",
  contract:
    "Reorganisiere diesen Contract-Body so, dass alle Informationen an der richtigen Stelle " +
    "gemäß SDD-Struktur sind: (1) Zweck & Überblick, (2) Garantien, (3) Fehlerfälle & " +
    "Error-Responses, (4) Begriffe & Definitionen, (5) Beispiele, (6) Notizen. " +
    "Verändere den Inhalt NICHT – ordne nur die bestehenden Informationen richtig an. " +
    "Gib nur den Markdown-Body aus (kein Frontmatter, keine Code-Fences).",
};

interface Props {
  docId: string;
  docType: "spec" | "contract";
  docContent: string;
  onRestructured: (newBody: string) => void;
}

type Phase = "idle" | "loading" | "preview";

export default function RestructurePanel({ docId, docType, docContent, onRestructured }: Props) {
  const notify = useNotify();
  const [phase, setPhase] = useState<Phase>("idle");
  const [preview, setPreview] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  async function handleRestructure() {
    setPhase("loading");
    setError("");
    try {
      const { result } = await api.aiImproveSpec({
        spec_id: docId,
        current_content: docContent,
        instructions: INSTRUCTIONS[docType],
      });
      setPreview(result);
      setPhase("preview");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Fehler beim Restrukturieren.");
      setPhase("idle");
    }
  }

  async function handleApply() {
    setSaving(true);
    setError("");
    try {
      if (docType === "spec") {
        await api.updateSpec(docId, preview);
      } else {
        await api.patchContractBody(docId, preview);
      }
      notify("✓ Restrukturiert — Review startet…", "success");
      onRestructured(preview);
      setPhase("idle");
      setPreview("");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Fehler beim Speichern.");
    } finally {
      setSaving(false);
    }
  }

  if (phase === "idle") {
    return (
      <button
        onClick={handleRestructure}
        style={{ fontSize: 11, padding: "2px 10px", color: "var(--accent)", borderColor: "var(--accent)" }}
      >
        🔄 Restrukturieren
      </button>
    );
  }

  if (phase === "loading") {
    return (
      <span style={{ fontSize: 12, color: "var(--muted)" }}>⏳ Claude restrukturiert…</span>
    );
  }

  return (
    <div style={{ marginTop: 12, border: "1px solid var(--accent)", borderRadius: 8, overflow: "hidden" }}>
      <div style={{
        display: "flex", justifyContent: "space-between", alignItems: "center",
        padding: "8px 12px", background: "var(--surface)", borderBottom: "1px solid var(--border)",
      }}>
        <span style={{ fontSize: 11, color: "var(--accent)", textTransform: "uppercase", letterSpacing: 0.8 }}>
          Vorschau – restrukturierter Inhalt
        </span>
        <div style={{ display: "flex", gap: 8 }}>
          <button
            onClick={() => { setPhase("idle"); setPreview(""); }}
            style={{ fontSize: 11, padding: "2px 10px" }}
          >
            Verwerfen
          </button>
          <button
            className="primary"
            onClick={handleApply}
            disabled={saving}
            style={{ fontSize: 11, padding: "2px 10px" }}
          >
            {saving ? "Speichert…" : "✓ Übernehmen & Review starten"}
          </button>
        </div>
      </div>
      <textarea
        value={preview}
        onChange={e => setPreview(e.target.value)}
        rows={20}
        style={{
          width: "100%", fontFamily: "monospace", fontSize: 12, display: "block",
          background: "var(--bg)", color: "var(--fg)", border: "none",
          padding: 12, resize: "vertical", boxSizing: "border-box",
        }}
      />
      {error && <p style={{ color: "var(--red)", fontSize: 13, padding: "6px 12px" }}>{error}</p>}
    </div>
  );
}
