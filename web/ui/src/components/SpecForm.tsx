import { useState } from "react";
import { api, AiUsageEntry } from "../api";

function buildSpecTemplate(title: string, section1: string): string {
  const today = new Date().toISOString().slice(0, 10);
  return `# ${title}

## 1. Kontext & Motivation

${section1.trim()}

## 2. Zielsetzung

**Primärziel:**


**Erfolgskriterien (messbar):**
- [ ]

**Nicht-Ziele (explizit):**
-

## 3. User Stories

| ID    | Als ... | möchte ich ... | um ... |
|-------|---------|----------------|--------|
| US-01 |         |                |        |

## 4. Funktionale Anforderungen

- **FR-01:**

## 5. Nicht-funktionale Anforderungen

| Kategorie     | Anforderung |
|---------------|-------------|
| Performance   |             |
| Security      |             |
| Accessibility |             |
| Observability |             |
| Datenschutz   |             |

## 6. Akzeptanzkriterien (Gherkin)

\`\`\`gherkin
Feature: ${title}

  Scenario:
    Given
    When
    Then
\`\`\`

## 7. Edge Cases & Fehlerfälle

-

## 8. Contracts (was wird garantiert)

| Contract-ID | Typ | Was wird garantiert? |
|-------------|-----|----------------------|

## 9. Tests (wie wird verifiziert)

| Test-ID  | Level | Was prüft der Test? |
|----------|-------|---------------------|

## 10. Offene Fragen

- [ ]

## 11. Änderungshistorie

| Datum      | Version | Autor | Änderung             |
|------------|---------|-------|----------------------|
| ${today}   | 0.1.0   |       | Initiale Erstellung  |
`;
}

interface Props {
  onCreated: (id: string) => void;
  onCancel: () => void;
}

type Mode = "simple" | "ai";
type AiPhase = "idle" | "generating" | "preview";

function UsagePill({ entry }: { entry: AiUsageEntry }) {
  const isCli = entry.provider === "claude-cli";
  return (
    <span style={{ fontSize: 10, color: "var(--muted)", fontFamily: "monospace" }}>
      {isCli
        ? <span>claude-cli</span>
        : <>{entry.input_tokens}↑ {entry.output_tokens}↓
            {entry.cache_read_tokens > 0 && (
              <span style={{ color: "var(--green)" }}> {entry.cache_read_tokens} cached</span>
            )}
            {" "}${(entry.cost_usd ?? 0).toFixed(5)}
          </>
      }
    </span>
  );
}

export default function SpecForm({ onCreated, onCancel }: Props) {
  const [mode, setMode]         = useState<Mode>("simple");
  const [title, setTitle]       = useState("");
  const [owner, setOwner]       = useState("");
  const [priority, setPriority] = useState("medium");
  const [description, setDescription] = useState("");
  const [aiPhase, setAiPhase]   = useState<AiPhase>("idle");
  const [aiBody, setAiBody]     = useState("");
  const [aiUsage, setAiUsage]   = useState<AiUsageEntry | null>(null);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState("");

  async function handleGenerate() {
    if (!title.trim()) return;
    setAiPhase("generating");
    setError("");
    setAiBody("");
    setAiUsage(null);
    try {
      const res = await api.aiGenerateSpec({ title, description });
      setAiBody(buildSpecTemplate(title, res.result));
      setAiUsage(res.usage);
      setAiPhase("preview");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Fehler beim Generieren.");
      setAiPhase("idle");
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    setLoading(true);
    setError("");
    try {
      const res = await api.createSpec({ title, owner, priority });
      if (mode === "ai" && aiBody.trim()) {
        await api.updateSpec(res.id, aiBody);
      }
      onCreated(res.id);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Fehler beim Anlegen.");
    } finally {
      setLoading(false);
    }
  }

  const canSubmit = title.trim() && (mode === "simple" || aiPhase === "preview");

  return (
    <form onSubmit={handleSubmit} className="card" style={{ display: "flex", flexDirection: "column", gap: 12, marginBottom: 12 }}>
      {/* Mode toggle */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h3 style={{ fontSize: 14, fontWeight: 700 }}>Neue Spec</h3>
        <div style={{ display: "flex", gap: 2, background: "var(--bg)", borderRadius: 5, padding: 2 }}>
          <button
            type="button"
            onClick={() => { setMode("simple"); setAiPhase("idle"); setAiBody(""); setError(""); }}
            style={{
              fontSize: 11, padding: "3px 8px", border: "none",
              background: mode === "simple" ? "var(--surface)" : "transparent",
              color: mode === "simple" ? "var(--text)" : "var(--muted)",
              borderRadius: 4, cursor: "pointer",
            }}
          >
            Einfach
          </button>
          <button
            type="button"
            onClick={() => { setMode("ai"); setError(""); }}
            style={{
              fontSize: 11, padding: "3px 8px", border: "none",
              background: mode === "ai" ? "var(--accent)" : "transparent",
              color: mode === "ai" ? "#1e1e2e" : "var(--muted)",
              borderRadius: 4, cursor: "pointer",
            }}
          >
            ✦ KI
          </button>
        </div>
      </div>

      {/* Title – always shown */}
      <div>
        <label>Titel *</label>
        <input
          value={title}
          onChange={e => setTitle(e.target.value)}
          placeholder="z.B. User Registrierung"
          autoFocus
          required
        />
      </div>

      {/* AI: description input */}
      {mode === "ai" && (
        <div>
          <label>Beschreibung <span style={{ color: "var(--muted)", fontWeight: 400 }}>(optional)</span></label>
          <textarea
            value={description}
            onChange={e => setDescription(e.target.value)}
            placeholder="Kontext für die KI – was soll die Spec leisten? Wer sind die Nutzer?"
            style={{
              width: "100%", minHeight: 60, fontSize: 12, padding: 8,
              boxSizing: "border-box", background: "var(--bg)", color: "var(--text)",
              border: "1px solid var(--border)", borderRadius: 4, resize: "vertical",
            }}
          />
        </div>
      )}

      {/* Owner + Priority */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <div>
          <label>Owner</label>
          <input value={owner} onChange={e => setOwner(e.target.value)} placeholder="Name oder Team" />
        </div>
        <div>
          <label>Priorität</label>
          <select value={priority} onChange={e => setPriority(e.target.value)}>
            <option value="low">low</option>
            <option value="medium">medium</option>
            <option value="high">high</option>
            <option value="critical">critical</option>
          </select>
        </div>
      </div>

      {/* AI: generate button + phase feedback */}
      {mode === "ai" && aiPhase !== "preview" && (
        <button
          type="button"
          onClick={handleGenerate}
          disabled={!title.trim() || aiPhase === "generating"}
          style={{
            fontSize: 12, padding: "6px 12px",
            background: "var(--accent)", color: "#1e1e2e",
            border: "none", borderRadius: 4, cursor: "pointer",
            opacity: (!title.trim() || aiPhase === "generating") ? 0.5 : 1,
          }}
        >
          {aiPhase === "generating" ? "✦ Claude generiert…" : "✦ Body generieren"}
        </button>
      )}

      {/* AI: preview textarea */}
      {mode === "ai" && aiPhase === "preview" && (
        <div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
            <span style={{ fontSize: 11, color: "var(--accent)", textTransform: "uppercase", letterSpacing: 0.8 }}>
              Generierter Body
            </span>
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              {aiUsage && <UsagePill entry={aiUsage} />}
              <button
                type="button"
                onClick={() => { setAiPhase("idle"); setAiBody(""); setAiUsage(null); }}
                style={{ fontSize: 10, padding: "1px 6px", color: "var(--muted)" }}
              >
                neu generieren
              </button>
            </div>
          </div>
          <textarea
            value={aiBody}
            onChange={e => setAiBody(e.target.value)}
            rows={14}
            style={{
              width: "100%", fontFamily: "monospace", fontSize: 11, display: "block",
              background: "var(--bg)", color: "var(--text)",
              border: "1px solid var(--accent)", borderRadius: 4,
              padding: 8, resize: "vertical", boxSizing: "border-box",
            }}
          />
        </div>
      )}

      {error && <p style={{ color: "var(--red)", fontSize: 13 }}>{error}</p>}

      <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
        <button type="button" onClick={onCancel}>Abbrechen</button>
        <button
          type="submit"
          className="primary"
          disabled={loading || !canSubmit}
        >
          {loading ? "Anlegen…" : "Spec anlegen"}
        </button>
      </div>
    </form>
  );
}
